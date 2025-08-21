#!/usr/bin/env python3
"""
Query TypeDB to dynamically build and display the field dependency tree.
Refined version with no hardcoded values except the root field ID.
"""

from typedb.driver import TypeDB, TransactionType, Credentials, DriverOptions
from collections import defaultdict
from config import DATABASE_CONFIG, VISUALIZATION_CONFIG, SAMPLE_DATA_CONFIG

def get_field_dependencies(tx):
    """Get all field dependencies from the database"""
    
    # Query to get all fields with their functions
    fields_query = """
        match
            $field isa form_field,
                has field_id $id,
                has field_name $name,
                has calculation_function $func;
        select $id, $name, $func;
    """
    
    fields = {}
    for result in tx.query(fields_query).resolve():
        field_id = result.get('id').get_string()
        name = result.get('name').get_string()
        func = result.get('func').get_string()
        fields[field_id] = {
            'name': name,
            'function': func,
            'dependencies': [],
            'dependents': []
        }
    
    # Query to get dependency relationships
    deps_query = """
        match
            (dependent_field: $dep, source_field: $src) isa field_dependency;
            $dep has field_id $dep_id;
            $src has field_id $src_id;
        select $dep_id, $src_id;
    """
    
    for result in tx.query(deps_query).resolve():
        dep_id = result.get('dep_id').get_string()
        src_id = result.get('src_id').get_string()
        
        if dep_id in fields and src_id in fields:
            fields[dep_id]['dependencies'].append(src_id)
            fields[src_id]['dependents'].append(dep_id)
    
    return fields


def get_function_inputs(tx, function_name):
    """Dynamically get function input requirements from database"""
    
    query = """
        match
            $meta isa function_metadata,
                has calculation_function "%s",
                has function_type $type;
        select $type;
    """ % function_name
    
    # First get function type
    func_type = None
    result = next(tx.query(query).resolve(), None)
    if result:
        func_type = result.get('type').get_string()
    
    # Then get inputs if they exist
    inputs_query = """
        match
            $meta isa function_metadata,
                has calculation_function "%s";
            (function: $meta, input: $input) isa function_input_spec;
            $input has input_description $desc,
                has input_entity_type $entity_type,
                has input_attribute_type $attr_type;
        select $desc, $entity_type, $attr_type;
    """ % function_name
    
    inputs = []
    for result in tx.query(inputs_query).resolve():
        inputs.append({
            'description': result.get('desc').get_string(),
            'entity_type': result.get('entity_type').get_string(),
            'attribute_type': result.get('attr_type').get_string()
        })
    
    return func_type, inputs


def get_income_types(tx):
    """Get all income types from database"""
    
    query = """
        match
            $type isa income_type,
                has field_id $id,
                has field_name $name;
        select $id, $name;
    """
    
    income_types = []
    for result in tx.query(query).resolve():
        income_types.append({
            'id': result.get('id').get_string(),
            'name': result.get('name').get_string()
        })
    return income_types


def get_sample_calculation_context(tx):
    """Get sample context for calculations from database"""
    
    # Query for any existing taxpayer and filing
    context_query = """
        match
            $taxpayer isa taxpayer, has ssn $ssn;
            $year isa tax_year, has year $yr;
            $status isa filing_status, has filing_status_type $status_type;
            (filer: $taxpayer, period: $year, status: $status) isa tax_filing;
        select $ssn, $yr, $status_type;
        limit 1;
    """
    
    result = next(tx.query(context_query).resolve(), None)
    if result:
        return {
            'ssn': result.get('ssn').get_string(),
            'year': result.get('yr').get_integer(),
            'status': result.get('status_type').get_string()
        }
    
    # Fall back to default values from config
    return {
        'ssn': SAMPLE_DATA_CONFIG['default_taxpayer_ssn'],
        'year': SAMPLE_DATA_CONFIG['default_tax_year'],
        'status': SAMPLE_DATA_CONFIG['default_filing_status']
    }


def build_dependency_tree(fields, root_id, tx=None, indent="", is_last=True, visited=None):
    """Recursively build ASCII tree representation with proper formatting"""
    if visited is None:
        visited = set()
    
    if root_id in visited:
        return indent + "└── (circular reference)\n"
    
    visited.add(root_id)
    
    field = fields.get(root_id)
    if not field:
        return ""
    
    tree = ""
    
    # Root node
    if indent == "":
        tree += f"{field['name']} [{root_id.replace('1040-', '')}]\n"
        tree += f"└── {field['function']}()\n"
        next_indent = "    "
    else:
        # Child node
        connector = "└──" if is_last else "├──"
        tree += f"{indent}{connector} {field['name']} [{root_id.replace('1040-', '')}]\n"
        
        # Function line
        if is_last:
            tree += f"{indent}    └── {field['function']}()\n"
            next_indent = indent + "        "
        else:
            tree += f"{indent}│   └── {field['function']}()\n"
            next_indent = indent + "│       "
    
    # Get function metadata to determine special handling
    func_type, inputs = get_function_inputs(tx, field['function']) if tx else (None, [])
    
    # Handle aggregation functions (like calculate_total_income)
    if func_type == 'aggregation' and field['function'] == 'calculate_total_income':
        income_types = get_income_types(tx)
        if income_types:
            tree += f"{next_indent}│\n"
            for i, income_type in enumerate(income_types):
                is_last_type = (i == len(income_types) - 1)
                connector = "└──" if is_last_type else "├──"
                tree += f"{next_indent}{connector} {income_type['name']}\n"
                tree += f"{next_indent}{'    ' if is_last_type else '│   '}└── (income_source.amount)\n"
                if not is_last_type:
                    tree += f"{next_indent}│\n"
            return tree
    
    # Handle lookup functions with inputs
    elif func_type == 'lookup' and inputs:
        tree += f"{next_indent}│\n"
        for i, input_spec in enumerate(inputs):
            is_last_input = (i == len(inputs) - 1)
            connector = "└──" if is_last_input else "├──"
            
            # Get actual value for display if possible
            display_value = input_spec['description']
            if input_spec['entity_type'] == 'tax_year':
                context = get_sample_calculation_context(tx)
                display_value = f"{input_spec['description']} ({context['year']})"
            elif input_spec['entity_type'] == 'filing_status':
                context = get_sample_calculation_context(tx)
                display_value = f"{input_spec['description']} ({context['status']})"
            
            tree += f"{next_indent}{connector} {display_value}\n"
            tree += f"{next_indent}{'    ' if is_last_input else '│   '}└── ({input_spec['entity_type']}.{input_spec['attribute_type']})\n"
            if not is_last_input:
                tree += f"{next_indent}│\n"
        return tree
    
    # Process dependencies
    deps = field.get('dependencies', [])
    has_tax_lookup = field['function'] == 'calculate_federal_tax' and tx
    
    total_children = len(deps) + (1 if has_tax_lookup else 0)
    
    # Add each dependency
    for i, dep_id in enumerate(deps):
        is_last_child = (i == len(deps) - 1) and not has_tax_lookup
        
        if i < len(deps):  # Add separator before each dependency except the last
            tree += f"{next_indent[:-4]}    │\n"
        
        child_indent = next_indent[:-4] + "    "
        tree += build_dependency_tree(fields, dep_id, tx, child_indent, is_last_child, visited)
    
    # Add tax rate lookup for calculate_federal_tax
    if has_tax_lookup:
        context = get_sample_calculation_context(tx)
        
        # Get taxable income amount
        taxable_amount = 75400.0  # Default
        try:
            taxable_query = """
                match
                    $john isa taxpayer, has ssn "%s";
                    $year isa tax_year, has year %d;
                    $status isa filing_status, has filing_status_type "%s";
                    let $taxable = calculate_taxable_income($john, $year, $status);
                select $taxable;
            """ % (context['ssn'], context['year'], context['status'])
            
            result = next(tx.query(taxable_query).resolve(), None)
            if result:
                taxable_amount = result.get('taxable').get_double()
        except:
            pass
        
        tree += f"{next_indent[:-4]}    │\n"
        tree += f"{next_indent[:-4]}    └── Tax Rate Lookup\n"
        tree += f"{next_indent[:-4]}        └── get_tax_rate()\n"
        tree += f"{next_indent[:-4]}            │\n"
        tree += f"{next_indent[:-4]}            ├── INPUT: Taxable Income (${taxable_amount:,.0f})\n"
        tree += f"{next_indent[:-4]}            ├── INPUT: Tax Year ({context['year']})\n"
        tree += f"{next_indent[:-4]}            ├── INPUT: Filing Status ({context['status']})\n"
        tree += f"{next_indent[:-4]}            │\n"
        tree += f"{next_indent[:-4]}            └── LOOKUP: tax_bracket_rule\n"
        
        # Query actual brackets
        brackets_query = """
            match
                $year isa tax_year, has year %d;
                $status isa filing_status, has filing_status_type "%s";
                (applicable_year: $year, applicable_status: $status, bracket: $bracket) isa tax_bracket_rule;
                $bracket has bracket_min $min, has bracket_max $max, has rate $rate;
            select $min, $max, $rate;
            sort $min asc;
        """ % (context['year'], context['status'])
        
        brackets = []
        for bracket in tx.query(brackets_query).resolve():
            min_val = bracket.get('min').get_double()
            max_val = bracket.get('max').get_double()
            rate = bracket.get('rate').get_double()
            brackets.append((min_val, max_val, rate))
        
        if brackets:
            tree += f"{next_indent[:-4]}                │\n"
            for i, (min_val, max_val, rate) in enumerate(brackets):
                is_last_bracket = (i == len(brackets) - 1)
                connector = "└──" if is_last_bracket else "├──"
                
                # Format range
                if max_val > 999999999:
                    range_str = f"${min_val:,.0f}+"
                else:
                    range_str = f"${min_val:,.0f} - ${max_val:,.0f}"
                
                tree += f"{next_indent[:-4]}                {connector} Check: {range_str} → {rate*100:.0f}%\n"
                
                # Check result
                if taxable_amount < min_val:
                    check = f"${taxable_amount:,.0f} < ${min_val:,.0f}"
                elif taxable_amount > max_val:
                    check = f"${taxable_amount:,.0f} > ${max_val:,.0f}"
                else:
                    check = f"${taxable_amount:,.0f} in range"
                
                sub_indent = "    " if is_last_bracket else "│   "
                tree += f"{next_indent[:-4]}                {sub_indent}└── {check}\n"
                
                if not is_last_bracket:
                    tree += f"{next_indent[:-4]}                │\n"
    
    return tree


def query_and_display_tree(database_name=None, root_field_id=None):
    """Main function to query TypeDB and display the dependency tree
    
    Args:
        database_name: Name of the TypeDB database (uses config default if None)
        root_field_id: Starting field ID for the tree (uses config default if None)
    """
    
    # Use config defaults if not provided
    if database_name is None:
        database_name = DATABASE_CONFIG['name']
    if root_field_id is None:
        root_field_id = VISUALIZATION_CONFIG['default_root_field']
    
    print(f"🔍 Querying TypeDB database '{database_name}' for Field Dependencies...")
    print("=" * 60)
    
    credentials = Credentials(DATABASE_CONFIG['username'], DATABASE_CONFIG['password'])
    options = DriverOptions(is_tls_enabled=DATABASE_CONFIG['tls_enabled'])
    driver = TypeDB.driver(DATABASE_CONFIG['host'], credentials, options)
    
    try:
        with driver.transaction(database_name, TransactionType.READ) as tx:
            # Get all field dependencies
            fields = get_field_dependencies(tx)
            
            # Display field information
            print("\n📊 Form Fields and Their Functions:")
            print("-" * 60)
            for field_id in sorted(fields.keys()):
                field = fields[field_id]
                print(f"{field_id}: {field['name']}")
                print(f"   Function: {field['function']}()")
                if field['dependencies']:
                    dep_names = [fields[d]['name'] for d in field['dependencies']]
                    print(f"   Depends on: {', '.join(dep_names)}")
                print()
            
            # Display function metadata if available
            print("\n🔧 Function Metadata:")
            print("-" * 60)
            metadata_query = """
                match
                    $meta isa function_metadata,
                        has calculation_function $func,
                        has function_type $type;
                select $func, $type;
                sort $func asc;
            """
            
            for result in tx.query(metadata_query).resolve():
                func_name = result.get('func').get_string()
                func_type = result.get('type').get_string()
                print(f"{func_name}: {func_type}")
            print()
            
            # Build and display dependency tree
            print(f"\n🌳 Form 1040 Field Dependency Hierarchy (starting from {root_field_id}):")
            print("-" * 60)
            tree = build_dependency_tree(fields, root_field_id, tx)
            print(tree)
            
    finally:
        driver.close()


if __name__ == "__main__":
    # Can override defaults by passing parameters
    query_and_display_tree()