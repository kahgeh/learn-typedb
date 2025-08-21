#!/usr/bin/env python3
"""
Query TypeDB to dynamically build and display dual field dependency trees:
1. Generic Year View - Shows all possible paths and options
2. Taxpayer-Specific View - Shows actual calculation path with values
"""

from typedb.driver import TypeDB, TransactionType, Credentials, DriverOptions
from collections import defaultdict
import argparse
from config import DATABASE_CONFIG, VISUALIZATION_CONFIG, SAMPLE_DATA_CONFIG

def get_field_dependencies(tx):
    """Get all field dependencies from the database"""
    
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
    
    deps_query = """
        match
            $dependency isa field_dependency,
                links (dependent_field: $dep, source_field: $src);
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


def get_all_income_types(tx):
    """Get all possible income types"""
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


def get_taxpayer_income(tx, ssn):
    """Get actual income sources for a specific taxpayer"""
    query = """
        match
            $taxpayer isa taxpayer, has ssn "%s";
            $income isa income_source,
                links (earner: $taxpayer, type: $type),
                has amount $amt;
            $type has field_name $name;
        select $name, $amt;
    """ % ssn
    
    income_sources = []
    for result in tx.query(query).resolve():
        income_sources.append({
            'name': result.get('name').get_string(),
            'amount': result.get('amt').get_double()
        })
    return income_sources


def get_all_standard_deductions(tx, year):
    """Get all standard deduction options for a year with display names"""
    query = """
        match
            $year isa tax_year, has year %d;
            $rule isa standard_deduction_rule,
                links (applicable_year: $year, applicable_status: $status, deduction: $ded);
            $status has filing_status_type $status_type, has filing_status_display $display;
            $ded has deduction_amount $amount;
        select $status_type, $display, $amount;
    """ % year
    
    deductions = {}
    for result in tx.query(query).resolve():
        status = result.get('status_type').get_string()
        display = result.get('display').get_string()
        amount = result.get('amount').get_double()
        deductions[status] = {'display': display, 'amount': amount}
    return deductions


def get_itemized_deductions(tx, year):
    """Get all itemized deduction types for a year"""
    query = """
        match
            $year isa tax_year, has year %d;
            $opt isa itemized_deduction_option,
                links (applicable_year: $year, type: $type);
            $type has deduction_type $id, has deduction_display $display;
        select $id, $display, $type;
    """ % year
    
    deductions = []
    for result in tx.query(query).resolve():
        ded_type = result.get('type')
        display = result.get('display').get_string()
        
        # Check if has limit
        limit_query = """
            match
                $type has deduction_display "%s";
                $type has deduction_limit $limit;
            select $limit;
        """ % display
        
        limit_result = next(tx.query(limit_query).resolve(), None)
        limit = limit_result.get('limit').get_double() if limit_result else None
        
        if limit and limit < 999999999:  # Only show limit if it's a real limit
            display = f"{display} (max ${limit:,.0f})"
        
        deductions.append(display)
    
    return deductions


def get_all_tax_brackets(tx, year):
    """Get all tax brackets for all filing statuses with base tax"""
    query = """
        match
            $year isa tax_year, has year %d;
            $rule isa tax_bracket_rule,
                links (applicable_year: $year, applicable_status: $status, bracket: $bracket);
            $status has filing_status_type $status_type;
            $bracket has bracket_min $min, has bracket_max $max, has bracket_rate $rate, has bracket_base_tax $base;
        select $status_type, $min, $max, $rate, $base;
        sort $status_type asc, $min asc;
    """ % year
    
    brackets = defaultdict(list)
    for result in tx.query(query).resolve():
        status = result.get('status_type').get_string()
        min_val = result.get('min').get_double()
        max_val = result.get('max').get_double()
        rate = result.get('rate').get_double()
        base_tax = result.get('base').get_double()
        brackets[status].append((min_val, max_val, rate, base_tax))
    return dict(brackets)


def get_taxpayer_calculations(tx, ssn, year):
    """Get actual calculation values for a taxpayer"""
    query = """
        match
            $taxpayer isa taxpayer, has ssn "%s";
            $year_entity isa tax_year, has year %d;
            $filing isa tax_filing,
                links (filer: $taxpayer, period: $year_entity, status: $status);
            $status has filing_status_type $status_type;
            let $total = calculate_total_income($taxpayer);
            let $agi = calculate_agi($taxpayer);
            let $deduction = get_standard_deduction($year_entity, $status);
            let $taxable = calculate_taxable_income($taxpayer, $year_entity, $status);
            let $tax = calculate_federal_tax($taxpayer, $year_entity, $status);
        select $status_type, $total, $agi, $deduction, $taxable, $tax;
    """ % (ssn, year)
    
    result = next(tx.query(query).resolve(), None)
    if result:
        return {
            'status': result.get('status_type').get_string(),
            'total_income': result.get('total').get_double(),
            'agi': result.get('agi').get_double(),
            'deduction': result.get('deduction').get_double() if hasattr(result.get('deduction'), 'get_double') else result.get('deduction'),
            'taxable': result.get('taxable').get_double(),
            'tax': result.get('tax').get_double()
        }
    return None


def get_filing_status_display(tx, status_type):
    """Get filing status display name from database"""
    query = """
        match
            $status isa filing_status,
                has filing_status_type "%s",
                has filing_status_display $display;
        select $display;
    """ % status_type
    
    result = next(tx.query(query).resolve(), None)
    if result:
        display = result.get('display').get_string()
        return display.upper() + " FILERS" if status_type == "single" else display.upper()
    return status_type.upper()


def build_generic_year_tree(fields, root_id, tx, year, indent="", is_last=True, visited=None):
    """Build tree showing all possible paths for a given year"""
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
        tree += f"Federal Income Tax [{root_id.replace('1040-', '')}]\n"
        tree += f"└── {field['function']}()\n"
        next_indent = "    "
    else:
        connector = "└──" if is_last else "├──"
        # For deductions field, show as "Deductions" not "Standard Deduction"
        field_name = "Deductions" if root_id == "1040-line-12" else field['name']
        tree += f"{indent}{connector} {field_name} [{root_id.replace('1040-', '')}]\n"
        
        if is_last:
            # For deductions, show calculate_deductions instead of get_standard_deduction
            func_name = "calculate_deductions" if root_id == "1040-line-12" else field['function']
            tree += f"{indent}    └── {func_name}()\n"
            next_indent = indent + "        "
        else:
            func_name = "calculate_deductions" if root_id == "1040-line-12" else field['function']
            tree += f"{indent}│   └── {func_name}()\n"
            next_indent = indent + "│       "
    
    # Handle special cases
    if field['function'] == 'calculate_total_income':
        # Show all possible income types
        income_types = get_all_income_types(tx)
        if income_types:
            tree += f"{next_indent}│\n"
            # Add more income types for generic view
            all_types = [
                {'name': 'W-2 Wages'},
                {'name': '1099 Income'},
                {'name': 'Capital Gains'},
                {'name': 'Business Income'}
            ]
            for i, income_type in enumerate(all_types):
                is_last_type = (i == len(all_types) - 1)
                connector = "└──" if is_last_type else "├──"
                tree += f"{next_indent}{connector} [POSSIBLE] {income_type['name']}\n"
                if not is_last_type:
                    tree += f"{next_indent}│\n" if i < len(all_types) - 2 else ""
            return tree
    
    elif root_id == "1040-line-12":  # Deductions field
        # Show both standard and itemized options from database
        standard_deductions = get_all_standard_deductions(tx, year)
        itemized_deductions = get_itemized_deductions(tx, year)
        
        tree += f"{next_indent}│\n"
        # Option A: Standard Deduction
        tree += f"{next_indent}├── [OPTION A] Standard Deduction\n"
        
        # Sort deductions in the desired order
        status_order = ['single', 'married_filing_jointly', 'head_of_household']
        sorted_deductions = [(s, standard_deductions[s]) for s in status_order if s in standard_deductions]
        
        for i, (status, info) in enumerate(sorted_deductions):
            is_last_status = (i == len(sorted_deductions) - 1)
            connector = "└──" if is_last_status else "├──"
            tree += f"{next_indent}│   {connector} {info['display']}: ${info['amount']:,.0f}\n"
        
        tree += f"{next_indent}│\n"
        # Option B: Itemized Deductions from database
        tree += f"{next_indent}└── [OPTION B] Itemized Deductions\n"
        for i, deduction_display in enumerate(itemized_deductions):
            is_last = (i == len(itemized_deductions) - 1)
            connector = "└──" if is_last else "├──"
            tree += f"{next_indent}    {connector} {deduction_display}\n"
        return tree
    
    # Process dependencies
    deps = field.get('dependencies', [])
    has_tax_lookup = field['function'] == 'calculate_federal_tax'
    
    for i, dep_id in enumerate(deps):
        is_last_child = (i == len(deps) - 1) and not has_tax_lookup
        
        if i < len(deps):
            tree += f"{next_indent[:-4]}    │\n"
        
        child_indent = next_indent[:-4] + "    "
        tree += build_generic_year_tree(fields, dep_id, tx, year, child_indent, is_last_child, visited)
    
    # Add tax rate lookup for calculate_federal_tax
    if has_tax_lookup:
        tree += f"{next_indent[:-4]}    │\n"
        tree += f"{next_indent[:-4]}    └── Tax Rate Lookup\n"
        tree += f"{next_indent[:-4]}        └── get_tax_rate()\n"
        tree += f"{next_indent[:-4]}            │\n"
        
        # Get all tax brackets from database
        all_brackets = get_all_tax_brackets(tx, year)
        
        # Define the order we want to show filing statuses
        status_order = ['single', 'married_filing_jointly', 'head_of_household']
        available_statuses = [s for s in status_order if s in all_brackets]
        
        # Show all available statuses from the database
        for j, status in enumerate(available_statuses):
            brackets = all_brackets[status]
            is_last_status = (j == len(available_statuses) - 1)
            status_connector = "└──" if is_last_status else "├──"
            
            tree += f"{next_indent[:-4]}            {status_connector} [FOR {get_filing_status_display(tx, status)}]\n"
            
            status_indent = "    " if is_last_status else "│   "
            
            for i, (min_val, max_val, rate, base_tax) in enumerate(brackets):
                is_last_bracket = (i == len(brackets) - 1)
                bracket_connector = "└──" if is_last_bracket else "├──"
                
                if max_val >= 999999999:
                    range_str = f"${min_val:,.0f}+"
                else:
                    range_str = f"${min_val:,.0f} - ${max_val:,.0f}"
                
                tree += f"{next_indent[:-4]}            {status_indent}{bracket_connector} {range_str} → ${base_tax:,.0f}, {rate*100:.0f}%\n"
            
            if not is_last_status:
                tree += f"{next_indent[:-4]}            │\n"
    
    return tree


def build_taxpayer_specific_tree(fields, root_id, tx, ssn, year, calculations=None, indent="", is_last=True, visited=None):
    """Build tree showing actual calculation path for specific taxpayer"""
    if visited is None:
        visited = set()
    
    if root_id in visited:
        return indent + "└── (circular reference)\n"
    
    visited.add(root_id)
    
    field = fields.get(root_id)
    if not field:
        return ""
    
    tree = ""
    
    # Get value for this field
    value_str = ""
    if calculations:
        if root_id == "1040-line-16":
            value_str = f" = ${calculations['tax']:,.0f}"
        elif root_id == "1040-line-15":
            value_str = f" = ${calculations['taxable']:,.0f}"
        elif root_id == "1040-line-11":
            value_str = f" = ${calculations['agi']:,.0f}"
        elif root_id == "1040-line-9":
            value_str = f" = ${calculations['total_income']:,.0f}"
        elif root_id == "1040-line-12":
            value_str = f" = ${calculations['deduction']:,.0f}"
    
    # Root node
    if indent == "":
        tree += f"Federal Income Tax [{root_id.replace('1040-', '')}]{value_str}\n"
        tree += f"└── {field['function']}()\n"
        next_indent = "    "
    else:
        connector = "└──" if is_last else "├──"
        tree += f"{indent}{connector} {field['name']} [{root_id.replace('1040-', '')}]{value_str}\n"
        
        if is_last:
            tree += f"{indent}    └── {field['function']}()\n"
            next_indent = indent + "        "
        else:
            tree += f"{indent}│   └── {field['function']}()\n"
            next_indent = indent + "│       "
    
    # Handle special cases
    if field['function'] == 'calculate_total_income':
        # Show actual income sources
        income_sources = get_taxpayer_income(tx, ssn)
        if income_sources:
            tree += f"{next_indent}│\n"
            for i, source in enumerate(income_sources):
                is_last_source = (i == len(income_sources) - 1)
                connector = "└──" if is_last_source else "├──"
                tree += f"{next_indent}{connector} {source['name']} = ${source['amount']:,.0f}\n"
                if not is_last_source:
                    tree += f"{next_indent}│\n" if i < len(income_sources) - 2 else ""
            return tree
    
    elif field['function'] == 'get_standard_deduction' and calculations:
        # Get the display name from database
        display_query = """
            match
                $status isa filing_status,
                    has filing_status_type "%s",
                    has filing_status_display $display;
            select $display;
        """ % calculations['status']
        
        display_result = next(tx.query(display_query).resolve(), None)
        display = display_result.get('display').get_string() if display_result else calculations['status'].title()
        
        tree += f"{next_indent}└── {display} Filer → ${calculations['deduction']:,.0f}\n"
        return tree
    
    # Process dependencies
    deps = field.get('dependencies', [])
    has_tax_lookup = field['function'] == 'calculate_federal_tax'
    
    for i, dep_id in enumerate(deps):
        is_last_child = (i == len(deps) - 1) and not has_tax_lookup
        
        if i < len(deps):
            tree += f"{next_indent[:-4]}    │\n"
        
        child_indent = next_indent[:-4] + "    "
        tree += build_taxpayer_specific_tree(fields, dep_id, tx, ssn, year, calculations, child_indent, is_last_child, visited)
    
    # Add tax rate lookup for calculate_federal_tax
    if has_tax_lookup and calculations:
        taxable = calculations['taxable']
        status = calculations['status']
        
        # Get the applicable bracket
        brackets = get_all_tax_brackets(tx, year).get(status, [])
        applicable_bracket = None
        for min_val, max_val, rate, base_tax in brackets:
            if min_val <= taxable <= max_val:
                applicable_bracket = (min_val, max_val, rate, base_tax)
                break
        
        if applicable_bracket:
            min_val, max_val, rate, base_tax = applicable_bracket
            tree += f"{next_indent[:-4]}    │\n"
            
            tree += f"{next_indent[:-4]}    └── Tax Rate Lookup\n"
            tree += f"{next_indent[:-4]}        └── get_tax_bracket() → ${base_tax:,.0f}, {rate*100:.0f}%\n"
            tree += f"{next_indent[:-4]}            │\n"
            tree += f"{next_indent[:-4]}            └── {status.title().replace('_', ' ')} Filer Tax Brackets\n"
            
            if max_val >= 999999999:
                range_str = f"${min_val:,.0f}+"
            else:
                range_str = f"${min_val:,.0f} - ${max_val:,.0f}"
            
            tree += f"{next_indent[:-4]}                └── {range_str} → ${base_tax:,.0f}, {rate*100:.0f}% ← APPLIED\n"
    
    return tree


def display_header(title, mode=None):
    """Display formatted header"""
    print("\n╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                     TAX CALCULATION DEPENDENCY TREE                       ║")
    print("║                  (Field Name → Calculation Function)                      ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    
    if mode:
        print("\n┌─────────────────────────────────────────────────────────────────────────┐")
        print(f"│ Form 1040 Field Dependency Hierarchy ( {mode} )                      │")
        print("└─────────────────────────────────────────────────────────────────────────┘")
    print()


def main():
    parser = argparse.ArgumentParser(description='Display tax calculation dependency tree')
    parser.add_argument('--year', type=int, default=SAMPLE_DATA_CONFIG['default_tax_year'],
                       help='Tax year (default: 2024)')
    parser.add_argument('--ssn', type=str,
                       help='Taxpayer SSN (if provided, shows taxpayer-specific view)')
    parser.add_argument('--compare', action='store_true',
                       help='Show comparison view (requires SSN)')
    parser.add_argument('--show-calculations', action='store_true',
                       help='Show calculation details')
    
    args = parser.parse_args()
    
    credentials = Credentials(DATABASE_CONFIG['username'], DATABASE_CONFIG['password'])
    options = DriverOptions(is_tls_enabled=DATABASE_CONFIG['tls_enabled'])
    driver = TypeDB.driver(DATABASE_CONFIG['host'], credentials, options)
    
    try:
        with driver.transaction(DATABASE_CONFIG['name'], TransactionType.READ) as tx:
            # Get field dependencies
            fields = get_field_dependencies(tx)
            root_field_id = VISUALIZATION_CONFIG['default_root_field']
            
            if args.compare:
                # Show both views
                if not args.ssn:
                    print("Error: SSN required for comparison view")
                    return
                
                # Generic view
                display_header("TAX CALCULATION DEPENDENCY TREE", "Year View")
                tree = build_generic_year_tree(fields, root_field_id, tx, args.year)
                print(tree)
                
                # Taxpayer-specific view
                calculations = get_taxpayer_calculations(tx, args.ssn, args.year)
                if calculations:
                    display_header("TAX CALCULATION DEPENDENCY TREE", "Taxpayer View")
                    tree = build_taxpayer_specific_tree(fields, root_field_id, tx, args.ssn, args.year, calculations)
                    print(tree)
                else:
                    print(f"No tax filing found for SSN {args.ssn} in year {args.year}")
            
            elif args.ssn:
                # Taxpayer-specific view
                calculations = get_taxpayer_calculations(tx, args.ssn, args.year)
                if calculations:
                    display_header("TAX CALCULATION DEPENDENCY TREE", "Taxpayer View")
                    tree = build_taxpayer_specific_tree(fields, root_field_id, tx, args.ssn, args.year, calculations)
                    print(tree)
                else:
                    print(f"No tax filing found for SSN {args.ssn} in year {args.year}")
            
            else:
                # Generic year view
                display_header("TAX CALCULATION DEPENDENCY TREE", "Year View")
                tree = build_generic_year_tree(fields, root_field_id, tx, args.year)
                print(tree)
    
    finally:
        driver.close()


if __name__ == "__main__":
    main()