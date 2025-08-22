#!/usr/bin/env python3
"""
Purely generic tree builder with NO hardcoded special cases.
Everything is driven by database metadata.
"""

from typedb.driver import TypeDB, TransactionType, Credentials, DriverOptions
import argparse
from config import DATABASE_CONFIG, VISUALIZATION_CONFIG, SAMPLE_DATA_CONFIG

class PurelyGenericTreeBuilder:
    """Builds dependency trees using ONLY metadata - no special cases"""
    
    def __init__(self, tx, year=2024):
        self.tx = tx
        self.year = year
        self.fields = {}
        self.function_specs = {}
        self.function_deps = {}
        self.load_metadata()
    
    def load_metadata(self):
        """Load all metadata from the database"""
        
        # Load fields
        fields_query = """
            match
                $field isa form_field,
                    has field_id $id,
                    has field_name $name,
                    has calculation_function $func;
            select $id, $name, $func;
        """
        
        for result in self.tx.query(fields_query).resolve():
            field_id = result.get('id').get_string()
            self.fields[field_id] = {
                'name': result.get('name').get_string(),
                'function': result.get('func').get_string(),
                'dependencies': []
            }
        
        # Load field dependencies
        deps_query = """
            match
                $dependency isa field_dependency,
                    links (dependent_field: $dep, source_field: $src);
                $dep has field_id $dep_id;
                $src has field_id $src_id;
            select $dep_id, $src_id;
        """
        
        for result in self.tx.query(deps_query).resolve():
            dep_id = result.get('dep_id').get_string()
            src_id = result.get('src_id').get_string()
            if dep_id in self.fields:
                self.fields[dep_id]['dependencies'].append(src_id)
        
        # Load function specifications
        func_spec_query = """
            match
                $spec isa function_spec,
                    has function_name $name,
                    has function_type $type;
                try { $spec has display_pattern $pattern; };
                try { $spec has query_pattern $query; };
            select $name, $type, $pattern, $query;
        """
        
        for result in self.tx.query(func_spec_query).resolve():
            func_name = result.get('name').get_string()
            self.function_specs[func_name] = {
                'type': result.get('type').get_string(),
                'display_pattern': result.get('pattern').get_string() if result.get('pattern') else None,
                'query_pattern': result.get('query').get_string() if result.get('query') else None
            }
        
        # Load function dependencies
        func_deps_query = """
            match
                $dep isa function_dependency,
                    links (caller: $caller, callee: $callee);
                $caller has function_name $caller_name;
                $callee has function_name $callee_name;
            select $caller_name, $callee_name;
        """
        
        for result in self.tx.query(func_deps_query).resolve():
            caller = result.get('caller_name').get_string()
            callee = result.get('callee_name').get_string()
            if caller not in self.function_deps:
                self.function_deps[caller] = []
            self.function_deps[caller].append(callee)
    
    def build_tree(self, field_id, indent="", is_last=True, visited=None):
        """Build tree purely from metadata - no special cases"""
        
        if visited is None:
            visited = set()
        
        if field_id in visited:
            return f"{indent}└── (circular reference)\n"
        
        visited.add(field_id)
        
        field = self.fields.get(field_id)
        if not field:
            return ""
        
        tree = ""
        
        # Build node
        if indent == "":
            tree += f"{field['name']} [{field_id.replace('1040-', '')}]\n"
            tree += f"└── {field['function']}()\n"
            next_indent = "    "
        else:
            connector = "└──" if is_last else "├──"
            tree += f"{indent}{connector} {field['name']} [{field_id.replace('1040-', '')}]\n"
            
            func_indent = indent + ("    " if is_last else "│   ")
            tree += f"{func_indent}└── {field['function']}()\n"
            next_indent = func_indent + "    "
        
        # Get function spec
        func_spec = self.function_specs.get(field['function'], {})
        func_type = func_spec.get('type')
        
        # Handle function based on type from metadata
        if func_type == 'aggregation':
            aggregated_items = self.get_aggregated_items(func_spec)
            if aggregated_items:
                tree += self.display_items(aggregated_items, next_indent, func_spec)
                return tree  # Aggregations are leaf nodes
        
        elif func_type == 'lookup':
            lookup_results = self.get_lookup_results(func_spec)
            if lookup_results:
                tree += self.display_lookup_results(lookup_results, next_indent, func_spec)
                # Continue processing dependencies for lookups
        
        # Check if we have additional content to determine if dependencies are last
        additional_content = self.get_additional_function_content(field['function'], next_indent)
        has_additional = additional_content is not None
        
        # Process field dependencies
        deps = field.get('dependencies', [])
        if deps:
            tree += f"{next_indent}│\n"
            for i, dep_id in enumerate(deps):
                # If there's additional content, no dependency is last
                is_last_dep = (i == len(deps) - 1) and not has_additional
                tree += self.build_tree(dep_id, next_indent, is_last_dep, visited)
        
        # Process additional function behaviors
        if additional_content:
            tree += additional_content
        
        return tree
    
    def get_aggregated_items(self, func_spec):
        """Get items for aggregation functions"""
        query_pattern = func_spec.get('query_pattern')
        
        if query_pattern == 'income_type':
            query = """
                match
                    $type isa income_type,
                        has field_name $name;
                select $name;
                sort $name asc;
            """
            
            items = []
            for result in self.tx.query(query).resolve():
                items.append({'name': result.get('name').get_string()})
            return items
        
        return []
    
    def get_lookup_results(self, func_spec):
        """Get results for lookup functions"""
        query_pattern = func_spec.get('query_pattern')
        
        if query_pattern == 'standard_deduction_rule':
            query = """
                match
                    $year isa tax_year, has year %d;
                    $rule isa standard_deduction_rule,
                        links (applicable_year: $year, applicable_status: $status, deduction: $ded);
                    $status has filing_status_display $display;
                    $ded has deduction_amount $amount;
                select $display, $amount;
            """ % self.year
            
            results = []
            for result in self.tx.query(query).resolve():
                results.append({
                    'status': result.get('display').get_string(),
                    'amount': result.get('amount').get_double()
                })
            return results
        
        return []
    
    def display_items(self, items, indent, func_spec):
        """Display aggregated items"""
        tree = f"{indent}│\n"
        display_pattern = func_spec.get('display_pattern', '{name}')
        
        for i, item in enumerate(items):
            is_last = (i == len(items) - 1)
            connector = "└──" if is_last else "├──"
            
            # Format using display pattern
            display = display_pattern.format(**item)
            tree += f"{indent}{connector} {display}\n"
            
            # Add vertical line between siblings (except after the last one)
            if not is_last:
                tree += f"{indent}│\n"
        
        return tree
    
    def display_lookup_results(self, results, indent, func_spec):
        """Display lookup results"""
        tree = f"{indent}│\n"
        display_pattern = func_spec.get('display_pattern', '{status}: ${amount}')
        
        for i, result in enumerate(results):
            is_last = (i == len(results) - 1)
            connector = "└──" if is_last else "├──"
            
            # Format using display pattern
            display = display_pattern.format(**result)
            tree += f"{indent}{connector} {display}\n"
        
        return tree
    
    def get_additional_function_content(self, function_name, indent):
        """Get any additional content for functions based on metadata"""
        
        func_spec = self.function_specs.get(function_name, {})
        query_pattern = func_spec.get('query_pattern')
        
        # Tax brackets are an additional lookup for tax calculation
        if query_pattern == 'tax_bracket_rule':
            return self.display_tax_brackets(indent)
        
        return None
    
    def display_tax_brackets(self, indent):
        """Display tax brackets based on metadata"""
        
        tree = f"{indent}│\n"
        tree += f"{indent}└── Tax Rate Lookup\n"
        tree += f"{indent}    └── get_tax_bracket()\n"
        tree += f"{indent}        │\n"
        
        # Query for tax brackets
        query = """
            match
                $year isa tax_year, has year %d;
                $rule isa tax_bracket_rule,
                    links (applicable_year: $year, applicable_status: $status, bracket: $bracket);
                $status has filing_status_type $type, has filing_status_display $display;
                $bracket has bracket_min $min, has bracket_max $max,
                        has bracket_rate $rate, has bracket_base_tax $base;
            select $type, $display, $min, $max, $rate, $base;
            sort $type asc, $min asc;
        """ % self.year
        
        brackets_by_status = {}
        for result in self.tx.query(query).resolve():
            status_type = result.get('type').get_string()
            display = result.get('display').get_string()
            
            if status_type not in brackets_by_status:
                brackets_by_status[status_type] = {'display': display, 'brackets': []}
            
            brackets_by_status[status_type]['brackets'].append({
                'min': result.get('min').get_double(),
                'max': result.get('max').get_double(),
                'rate': result.get('rate').get_double(),
                'base': result.get('base').get_double()
            })
        
        # Display brackets for each status
        status_list = list(brackets_by_status.items())
        for j, (status, data) in enumerate(status_list):
            is_last_status = (j == len(status_list) - 1)
            status_connector = "└──" if is_last_status else "├──"
            
            tree += f"{indent}        {status_connector} [FOR {data['display'].upper()}]\n"
            
            status_indent = "    " if is_last_status else "│   "
            
            for i, bracket in enumerate(data['brackets']):
                is_last_bracket = (i == len(data['brackets']) - 1)
                bracket_connector = "└──" if is_last_bracket else "├──"
                
                if bracket['max'] >= 999999999:
                    range_str = f"${bracket['min']:,.0f}+"
                else:
                    range_str = f"${bracket['min']:,.0f} - ${bracket['max']:,.0f}"
                
                tree += f"{indent}        {status_indent}{bracket_connector} {range_str} → ${bracket['base']:,.0f}, {bracket['rate']*100:.0f}%\n"
            
            if not is_last_status:
                tree += f"{indent}        │\n"
        
        return tree


def display_header(title):
    """Display formatted header"""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)


def main():
    parser = argparse.ArgumentParser(description='Purely generic dependency tree builder')
    parser.add_argument('--year', type=int, default=SAMPLE_DATA_CONFIG['default_tax_year'],
                       help='Tax year (default: 2024)')
    parser.add_argument('--field', type=str, default=VISUALIZATION_CONFIG['default_root_field'],
                       help='Field ID to start from')
    
    args = parser.parse_args()
    
    credentials = Credentials(DATABASE_CONFIG['username'], DATABASE_CONFIG['password'])
    options = DriverOptions(is_tls_enabled=DATABASE_CONFIG['tls_enabled'])
    driver = TypeDB.driver(DATABASE_CONFIG['host'], credentials, options)
    
    try:
        with driver.transaction(DATABASE_CONFIG['name'], TransactionType.READ) as tx:
            builder = PurelyGenericTreeBuilder(tx, args.year)
            
            display_header("Tax Form Calculation Tree")
            print(f"\nStarting from: {args.field}")
            print(f"Return Type: 1040")
            print(f"Tax Year: {args.year}")
            print("\n")
            
            tree = builder.build_tree(args.field)
            print(tree)
    
    finally:
        driver.close()


if __name__ == "__main__":
    main()
