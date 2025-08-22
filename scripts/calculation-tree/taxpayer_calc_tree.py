#!/usr/bin/env python3
"""
Generic taxpayer-specific tree builder that extends the purely generic approach.
All taxpayer-specific behavior is driven by metadata, maintaining the generic nature.
"""

from typedb.driver import TypeDB, TransactionType, Credentials, DriverOptions
import argparse
from config import DATABASE_CONFIG, VISUALIZATION_CONFIG, SAMPLE_DATA_CONFIG
from tax_form_calc_tree import PurelyGenericTreeBuilder

class GenericTaxpayerTreeBuilder(PurelyGenericTreeBuilder):
    """Extends generic tree builder with taxpayer context - still metadata-driven"""
    
    def __init__(self, tx, year, ssn):
        super().__init__(tx, year)
        self.ssn = ssn
        self.taxpayer_values = {}
        self.taxpayer_context = {}
        self.load_taxpayer_context()
    
    def load_taxpayer_context(self):
        """Load taxpayer-specific context and values"""
        
        # Get taxpayer and filing status
        context_query = """
            match
                $taxpayer isa taxpayer, has ssn "%s";
                $year_entity isa tax_year, has year %d;
                $filing isa tax_filing,
                    links (filer: $taxpayer, period: $year_entity, status: $status);
                $status has filing_status_type $status_type,
                        has filing_status_display $display;
            select $taxpayer, $year_entity, $status, $status_type, $display;
        """ % (self.ssn, self.year)
        
        result = next(self.tx.query(context_query).resolve(), None)
        if result:
            self.taxpayer_context = {
                'taxpayer': result.get('taxpayer'),
                'year_entity': result.get('year_entity'),
                'status': result.get('status'),
                'status_type': result.get('status_type').get_string(),
                'status_display': result.get('display').get_string()
            }
            
            # Load all field values using TypeQL functions
            self.load_field_values()
    
    def load_field_values(self):
        """Load all field values for the taxpayer using TypeQL functions"""
        
        if not self.taxpayer_context:
            return
        
        # Query all field values using the calculation functions
        values_query = """
            match
                $taxpayer isa taxpayer, has ssn "%s";
                $year_entity isa tax_year, has year %d;
                $filing isa tax_filing,
                    links (filer: $taxpayer, period: $year_entity, status: $status);
                let $total = calculate_total_income($taxpayer);
                let $agi = calculate_agi($taxpayer);
                let $deduction = get_standard_deduction($year_entity, $status);
                let $taxable = calculate_taxable_income($taxpayer, $year_entity, $status);
                let $tax = calculate_federal_tax($taxpayer, $year_entity, $status);
            select $total, $agi, $deduction, $taxable, $tax;
        """ % (self.ssn, self.year)
        
        result = next(self.tx.query(values_query).resolve(), None)
        if result:
            # Map values to field IDs
            self.taxpayer_values = {
                '1040-line-9': result.get('total').get_double(),
                '1040-line-11': result.get('agi').get_double(),
                '1040-line-12': result.get('deduction').get_double() if hasattr(result.get('deduction'), 'get_double') else result.get('deduction'),
                '1040-line-15': result.get('taxable').get_double(),
                '1040-line-16': result.get('tax').get_double()
            }
    
    def build_tree(self, field_id, indent="", is_last=True, visited=None):
        """Build tree with taxpayer values - extends generic approach"""
        
        if visited is None:
            visited = set()
        
        if field_id in visited:
            return f"{indent}└── (circular reference)\n"
        
        visited.add(field_id)
        
        field = self.fields.get(field_id)
        if not field:
            return ""
        
        tree = ""
        
        # Get taxpayer value for this field
        value_str = ""
        if field_id in self.taxpayer_values:
            value = self.taxpayer_values[field_id]
            value_str = f" = ${value:,.0f}" if isinstance(value, (int, float)) else f" = {value}"
        
        # Build node with value
        if indent == "":
            tree += f"{field['name']} [{field_id.replace('1040-', '')}]{value_str}\n"
            tree += f"└── {field['function']}()\n"
            next_indent = "    "
        else:
            connector = "└──" if is_last else "├──"
            tree += f"{indent}{connector} {field['name']} [{field_id.replace('1040-', '')}]{value_str}\n"
            
            func_indent = indent + ("    " if is_last else "│   ")
            tree += f"{func_indent}└── {field['function']}()\n"
            next_indent = func_indent + "    "
        
        # Get function spec
        func_spec = self.function_specs.get(field['function'], {})
        func_type = func_spec.get('type')
        
        # Handle function based on type with taxpayer context
        if func_type == 'aggregation':
            taxpayer_items = self.get_taxpayer_aggregated_items(func_spec)
            if taxpayer_items:
                tree += self.display_taxpayer_items(taxpayer_items, next_indent, func_spec)
                return tree  # Aggregations are leaf nodes
        
        elif func_type == 'lookup':
            taxpayer_results = self.get_taxpayer_lookup_results(func_spec)
            if taxpayer_results:
                tree += self.display_taxpayer_lookup_results(taxpayer_results, next_indent, func_spec)
                # Continue processing dependencies for lookups
        
        # Check for additional content
        additional_content = self.get_taxpayer_additional_content(field['function'], next_indent)
        has_additional = additional_content is not None
        
        # Process field dependencies
        deps = field.get('dependencies', [])
        if deps:
            tree += f"{next_indent}│\n"
            for i, dep_id in enumerate(deps):
                is_last_dep = (i == len(deps) - 1) and not has_additional
                tree += self.build_tree(dep_id, next_indent, is_last_dep, visited)
        
        # Process additional function behaviors
        if additional_content:
            tree += additional_content
        
        return tree
    
    def get_taxpayer_aggregated_items(self, func_spec):
        """Get actual taxpayer items for aggregation functions"""
        query_pattern = func_spec.get('query_pattern')
        
        if query_pattern == 'income_type':
            # Get actual taxpayer income sources with values
            query = """
                match
                    $taxpayer isa taxpayer, has ssn "%s";
                    $income isa income_source,
                        links (earner: $taxpayer, type: $type),
                        has amount $amt;
                    $type has field_name $name;
                select $name, $amt;
            """ % self.ssn
            
            items = []
            for result in self.tx.query(query).resolve():
                items.append({
                    'name': result.get('name').get_string(),
                    'amount': result.get('amt').get_double()
                })
            return items
        
        return []
    
    def get_taxpayer_lookup_results(self, func_spec):
        """Get taxpayer-specific lookup results"""
        query_pattern = func_spec.get('query_pattern')
        
        if query_pattern == 'standard_deduction_rule' and self.taxpayer_context:
            # Get the specific deduction that applies to this taxpayer
            status_type = self.taxpayer_context['status_type']
            query = """
                match
                    $year isa tax_year, has year %d;
                    $status isa filing_status, has filing_status_type "%s";
                    $rule isa standard_deduction_rule,
                        links (applicable_year: $year, applicable_status: $status, deduction: $ded);
                    $status has filing_status_display $display;
                    $ded has deduction_amount $amount;
                select $display, $amount;
            """ % (self.year, status_type)
            
            result = next(self.tx.query(query).resolve(), None)
            if result:
                return [{
                    'status': result.get('display').get_string(),
                    'amount': result.get('amount').get_double(),
                    'applied': True
                }]
        
        return []
    
    def display_taxpayer_items(self, items, indent, func_spec):
        """Display taxpayer's actual items with values"""
        tree = f"{indent}│\n"
        
        for i, item in enumerate(items):
            is_last = (i == len(items) - 1)
            connector = "└──" if is_last else "├──"
            
            # Use taxpayer display pattern if available
            display_pattern = func_spec.get('taxpayer_display_pattern', '{name} = ${amount:,.0f}')
            display = display_pattern.format(**item)
            tree += f"{indent}{connector} {display}\n"
            
            if not is_last:
                tree += f"{indent}│\n" if i < len(items) - 2 else ""
        
        return tree
    
    def display_taxpayer_lookup_results(self, results, indent, func_spec):
        """Display taxpayer-specific lookup results"""
        tree = ""
        
        for result in results:
            # Show only the applicable result for the taxpayer
            display_pattern = func_spec.get('taxpayer_display_pattern', 
                                          func_spec.get('display_pattern', '{status}: ${amount}'))
            # Format the display properly
            if 'amount' in result and isinstance(result['amount'], (int, float)):
                display = f"{result['status']} Filer → ${result['amount']:,.0f}"
            else:
                display = display_pattern.format(**result)
            tree += f"{indent}└── {display}\n"
        
        return tree
    
    def get_taxpayer_additional_content(self, function_name, indent):
        """Get taxpayer-specific additional content based on metadata"""
        
        func_spec = self.function_specs.get(function_name, {})
        query_pattern = func_spec.get('query_pattern')
        
        if query_pattern == 'tax_bracket_rule' and self.taxpayer_context:
            return self.display_taxpayer_tax_bracket(indent)
        
        return None
    
    def display_taxpayer_tax_bracket(self, indent):
        """Display the specific tax bracket that applies to the taxpayer"""
        
        if '1040-line-15' not in self.taxpayer_values:
            return None
        
        taxable = self.taxpayer_values['1040-line-15']
        status_type = self.taxpayer_context['status_type']
        
        tree = f"{indent}│\n"
        tree += f"{indent}└── Tax Rate Lookup\n"
        
        # Query for all brackets and find the applicable one
        query = """
            match
                $year isa tax_year, has year %d;
                $status isa filing_status, has filing_status_type "%s";
                $rule isa tax_bracket_rule,
                    links (applicable_year: $year, applicable_status: $status, bracket: $bracket);
                $bracket has bracket_min $min, has bracket_max $max,
                        has bracket_rate $rate, has bracket_base_tax $base;
            select $min, $max, $rate, $base;
            sort $min asc;
        """ % (self.year, status_type)
        
        # Find the applicable bracket
        applicable_bracket = None
        for result in self.tx.query(query).resolve():
            min_val = result.get('min').get_double()
            max_val = result.get('max').get_double()
            if min_val <= taxable <= max_val:
                applicable_bracket = result
                break
        
        if applicable_bracket:
            min_val = applicable_bracket.get('min').get_double()
            max_val = applicable_bracket.get('max').get_double()
            rate = applicable_bracket.get('rate').get_double()
            base_tax = applicable_bracket.get('base').get_double()
            
            tree += f"{indent}    └── get_tax_bracket() → ${base_tax:,.0f}, {rate*100:.0f}%\n"
            tree += f"{indent}        │\n"
            
            # Format status display
            status_display = self.taxpayer_context['status_display']
            tree += f"{indent}        └── {status_display} Filer Tax Brackets\n"
            
            # Show the applicable bracket
            if max_val >= 999999999:
                range_str = f"${min_val:,.0f}+"
            else:
                range_str = f"${min_val:,.0f} - ${max_val:,.0f}"
            
            tree += f"{indent}            └── {range_str} → ${base_tax:,.0f}, {rate*100:.0f}% ← APPLIED\n"
        
        return tree


def display_header(title):
    """Display formatted header"""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)


def main():
    parser = argparse.ArgumentParser(description='Generic taxpayer-specific dependency tree')
    parser.add_argument('--year', type=int, default=SAMPLE_DATA_CONFIG['default_tax_year'],
                       help='Tax year (default: 2024)')
    parser.add_argument('--ssn', type=str, required=True,
                       help='Taxpayer SSN')
    parser.add_argument('--field', type=str, default=VISUALIZATION_CONFIG['default_root_field'],
                       help='Field ID to start from')
    
    args = parser.parse_args()
    
    credentials = Credentials(DATABASE_CONFIG['username'], DATABASE_CONFIG['password'])
    options = DriverOptions(is_tls_enabled=DATABASE_CONFIG['tls_enabled'])
    driver = TypeDB.driver(DATABASE_CONFIG['host'], credentials, options)
    
    try:
        with driver.transaction(DATABASE_CONFIG['name'], TransactionType.READ) as tx:
            builder = GenericTaxpayerTreeBuilder(tx, args.year, args.ssn)
            
            display_header("Taxpayer Calculation Tree")
            print(f"\nTaxpayer SSN: {args.ssn}")
            print(f"Return Type: 1040")
            print(f"Tax Year: {args.year}")
            print(f"Starting from: {args.field}")
            print("\n")
            
            tree = builder.build_tree(args.field)
            print(tree)
            
    
    finally:
        driver.close()


if __name__ == "__main__":
    main()
