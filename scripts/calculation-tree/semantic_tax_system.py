#!/usr/bin/env python3
"""
True Semantic Tax Calculation System in TypeDB 3.x

This demonstrates REAL semantic correctness by:
1. Using TypeDB functions as the ONLY source of calculation logic (no formula strings!)
2. Functions call other functions, creating a true dependency graph
3. Field metadata references functions by name, creating traceable calculations
4. The schema IS the business logic, not just a description of it

Key improvements:
- No redundant formula_expression or calculation_formula attributes
- Functions are composable and reusable
- Calculation logic is validated by TypeDB's type system
- Dependencies are explicit through function calls
"""

from typedb.driver import TypeDB, TransactionType, Credentials, DriverOptions
import json

def create_true_semantic_schema(driver):
    """Create a schema where functions ARE the calculations"""
    
    print("📋 Defining true semantic tax schema...")
    with driver.transaction("tax-system", TransactionType.SCHEMA) as tx:
        
        # Define the core schema WITHOUT formula strings
        core_schema = """
            define
            
            # === Attributes ===
            attribute ssn, value string;
            attribute name, value string;
            attribute amount, value double;
            attribute year, value integer;
            attribute form_name, value string;
            attribute field_name, value string;
            attribute field_id, value string;
            attribute filing_status_type, value string;
            attribute filing_status_display, value string;
            attribute deduction_amount, value double;
            attribute deduction_type, value string;
            attribute deduction_display, value string;
            attribute deduction_limit, value double;
            attribute bracket_rate, value double;
            attribute bracket_min, value double;
            attribute bracket_max, value double;
            attribute bracket_base_tax, value double;  # Tax owed on income up to bracket_min
            # NEW: Instead of formula_expression, we store function names
            attribute calculation_function, value string;
            attribute depends_on_function, value string;
            # Function metadata attributes
            attribute function_type, value string;  # "aggregation", "lookup", "calculation", "external"
            attribute input_description, value string;
            attribute input_entity_type, value string;
            attribute input_attribute_type, value string;
            
            # === Core Entities ===
            
            entity taxpayer,
                owns ssn @key,
                owns name,
                plays tax_filing:filer,
                plays income_source:earner;
            
            entity tax_year,
                owns year @key,
                plays tax_filing:period,
                plays tax_bracket_rule:applicable_year,
                plays standard_deduction_rule:applicable_year,
                plays itemized_deduction_option:applicable_year;
            
            entity filing_status,
                owns filing_status_type @key,
                owns filing_status_display,
                plays tax_filing:status,
                plays tax_bracket_rule:applicable_status,
                plays standard_deduction_rule:applicable_status;
            
            # Form fields now reference their calculation function
            entity form_field,
                owns form_name,
                owns field_name,
                owns field_id @key,
                owns calculation_function,  # Name of the TypeDB function that calculates this
                plays field_dependency:dependent_field,
                plays field_dependency:source_field;
            
            entity income_type,
                owns field_id @key,
                owns field_name,
                plays income_source:type;
            
            entity tax_bracket,
                owns bracket_min,
                owns bracket_max,
                owns bracket_rate,
                owns bracket_base_tax,
                plays tax_bracket_rule:bracket;
            
            entity standard_deduction,
                owns deduction_amount,
                plays standard_deduction_rule:deduction;
            
            entity itemized_deduction_type,
                owns deduction_type @key,
                owns deduction_display,
                owns deduction_limit,
                plays itemized_deduction_option:type;
            
            # === Relations ===
            
            relation tax_filing,
                relates filer,
                relates period,
                relates status;
            
            relation income_source,
                relates earner,
                relates type,
                owns amount;
            
            # Field dependencies are derived from function calls
            relation field_dependency,
                relates dependent_field,
                relates source_field,
                owns depends_on_function;  # Which function creates this dependency
            
            relation tax_bracket_rule,
                relates applicable_year,
                relates applicable_status,
                relates bracket;
            
            relation standard_deduction_rule,
                relates applicable_year,
                relates applicable_status,
                relates deduction;
            
            relation itemized_deduction_option,
                relates applicable_year,
                relates type;
            
            # Function metadata entity
            entity function_metadata,
                owns calculation_function @key,
                owns function_type,
                plays function_input_spec:function;
            
            # Input specification
            entity input_spec,
                owns input_description,
                owns input_entity_type,
                owns input_attribute_type,
                plays function_input_spec:input;
            
            # Relation linking functions to their inputs
            relation function_input_spec,
                relates function,
                relates input;
        """
        tx.query(core_schema).resolve()
        
        # Define COMPOSABLE functions that call each other
        calculation_functions = """
            define
            
            # Base function: Calculate total income for a taxpayer
            fun calculate_total_income($taxpayer: taxpayer) -> double:
                match
                    $income isa income_source,
                        links (earner: $taxpayer, type: $type),
                        has amount $amt;
                return sum($amt);
            
            # Lookup function: Get standard deduction
            fun get_standard_deduction($year: tax_year, $status: filing_status) -> deduction_amount:
                match
                    $rule isa standard_deduction_rule,
                        links (applicable_year: $year, 
                               applicable_status: $status,
                               deduction: $deduction);
                    $deduction has deduction_amount $ded_amount;
                return first $ded_amount;
            
            # COMPOSED function: Calculate AGI (calls calculate_total_income)
            fun calculate_agi($taxpayer: taxpayer) -> double:
                match
                    let $total_income = calculate_total_income($taxpayer);
                    # For simplicity, no adjustments in this example
                    let $agi = $total_income;
                return first $agi;
            
            # COMPOSED function: Calculate taxable income (calls other functions)
            fun calculate_taxable_income($taxpayer: taxpayer, $year: tax_year, $status: filing_status) -> double:
                match
                    let $agi = calculate_agi($taxpayer);
                    let $ded_attr = get_standard_deduction($year, $status);
                    let $taxable = $agi - $ded_attr;
                    # TypeDB 3.0 doesn't have if/else yet, so we ensure positive in the query
                    $taxable > 0;
                return first $taxable;
            
            # Get applicable tax bracket with all needed info
            fun get_tax_bracket($income: double, $year: tax_year, $status: filing_status) -> bracket_min, bracket_max, bracket_rate, bracket_base_tax:
                match
                    $rule isa tax_bracket_rule,
                        links (applicable_year: $year,
                               applicable_status: $status,
                               bracket: $bracket);
                    $bracket has bracket_min $min, has bracket_max $max, has bracket_rate $rate, has bracket_base_tax $base;
                    $income >= $min;
                    $income <= $max;
                return first $min, $max, $rate, $base;
            
            # COMPOSED function: Calculate federal tax using progressive tax calculation
            fun calculate_federal_tax($taxpayer: taxpayer, $year: tax_year, $status: filing_status) -> double:
                match
                    let $taxable = calculate_taxable_income($taxpayer, $year, $status);
                    let $min, $max, $rate, $base = get_tax_bracket($taxable, $year, $status);
                    let $tax = $base + (($taxable - $min) * $rate);
                return first $tax;
            
            # Meta function: Get all calculations for a tax return
            fun calculate_complete_return($taxpayer: taxpayer, $year: tax_year, $status: filing_status) -> double, double, deduction_amount, double, double:
                match
                    let $total_income = calculate_total_income($taxpayer);
                    let $agi = calculate_agi($taxpayer);
                    let $deduction = get_standard_deduction($year, $status);
                    let $taxable = calculate_taxable_income($taxpayer, $year, $status);
                    let $tax = calculate_federal_tax($taxpayer, $year, $status);
                return first $total_income, $agi, $deduction, $taxable, $tax;
        """
        tx.query(calculation_functions).resolve()
        tx.commit()
        print("   ✓ True semantic schema with composable functions defined")


def insert_form_metadata(driver):
    """Insert form field metadata that references calculation functions"""
    
    print("\n📊 Inserting form metadata with function references...")
    with driver.transaction("tax-system", TransactionType.WRITE) as tx:
        
        # Form fields now reference their calculation functions by name
        form_metadata = """
            insert
            # Form 1040 fields with their calculation functions
            $line9 isa form_field,
                has form_name "1040",
                has field_name "Total Income",
                has field_id "1040-line-9",
                has calculation_function "calculate_total_income";
            
            $line11 isa form_field,
                has form_name "1040",
                has field_name "Adjusted Gross Income",
                has field_id "1040-line-11",
                has calculation_function "calculate_agi";
            
            $line12 isa form_field,
                has form_name "1040",
                has field_name "Standard Deduction",
                has field_id "1040-line-12",
                has calculation_function "get_standard_deduction";
            
            $line15 isa form_field,
                has form_name "1040",
                has field_name "Taxable Income",
                has field_id "1040-line-15",
                has calculation_function "calculate_taxable_income";
            
            $line16 isa form_field,
                has form_name "1040",
                has field_name "Federal Income Tax",
                has field_id "1040-line-16",
                has calculation_function "calculate_federal_tax";
            
            # Dependencies are explicit through function composition
            $dep1 isa field_dependency,
                links (dependent_field: $line11, source_field: $line9),
                has depends_on_function "calculate_agi";
            $dep2 isa field_dependency,
                links (dependent_field: $line15, source_field: $line11),
                has depends_on_function "calculate_taxable_income";
            $dep3 isa field_dependency,
                links (dependent_field: $line15, source_field: $line12),
                has depends_on_function "calculate_taxable_income";
            $dep4 isa field_dependency,
                links (dependent_field: $line16, source_field: $line15),
                has depends_on_function "calculate_federal_tax";
        """
        tx.query(form_metadata).resolve()
        
        # Insert tax configuration
        tax_config = """
            insert
            $year2024 isa tax_year, has year 2024;
            
            $single isa filing_status, has filing_status_type "single", has filing_status_display "Single";
            $married isa filing_status, has filing_status_type "married_filing_jointly", has filing_status_display "Married Filing Jointly";
            
            # Standard deductions
            $single_ded isa standard_deduction, has deduction_amount 14600.0;
            $single_ded_rule isa standard_deduction_rule,
                links (applicable_year: $year2024, applicable_status: $single, deduction: $single_ded);
            
            $married_ded isa standard_deduction, has deduction_amount 29200.0;
            $married_ded_rule isa standard_deduction_rule,
                links (applicable_year: $year2024, applicable_status: $married, deduction: $married_ded);
            
            # Tax brackets for single filers with correct base_tax values
            # First bracket: $0-$11,600 at 10%, base tax = $0
            $bracket1 isa tax_bracket, has bracket_min 0.0, has bracket_max 11600.0, has bracket_rate 0.10, has bracket_base_tax 0.0;
            $single_bracket1_rule isa tax_bracket_rule,
                links (applicable_year: $year2024, applicable_status: $single, bracket: $bracket1);
            
            # Second bracket: $11,600-$47,150 at 12%, base tax = $1,160 (from first bracket)
            $bracket2 isa tax_bracket, has bracket_min 11600.0, has bracket_max 47150.0, has bracket_rate 0.12, has bracket_base_tax 1160.0;
            $single_bracket2_rule isa tax_bracket_rule,
                links (applicable_year: $year2024, applicable_status: $single, bracket: $bracket2);
            
            # Third bracket: $47,150-$100,525 at 22%, base tax = $5,426 ($1,160 + $4,266)
            $bracket3 isa tax_bracket, has bracket_min 47150.0, has bracket_max 100525.0, has bracket_rate 0.22, has bracket_base_tax 5426.0;
            $single_bracket3_rule isa tax_bracket_rule,
                links (applicable_year: $year2024, applicable_status: $single, bracket: $bracket3);
            
            # Fourth bracket: $100,525+ at 24%, base tax = $17,168.50 ($5,426 + $11,742.50)
            $bracket4 isa tax_bracket, has bracket_min 100525.0, has bracket_max 999999999.0, has bracket_rate 0.24, has bracket_base_tax 17168.5;
            $single_bracket4_rule isa tax_bracket_rule,
                links (applicable_year: $year2024, applicable_status: $single, bracket: $bracket4);
            
            # Tax brackets for married filing jointly
            $m_bracket1 isa tax_bracket, has bracket_min 0.0, has bracket_max 23200.0, has bracket_rate 0.10, has bracket_base_tax 0.0;
            $married_bracket1_rule isa tax_bracket_rule,
                links (applicable_year: $year2024, applicable_status: $married, bracket: $m_bracket1);
            
            $m_bracket2 isa tax_bracket, has bracket_min 23200.0, has bracket_max 94300.0, has bracket_rate 0.12, has bracket_base_tax 2320.0;
            $married_bracket2_rule isa tax_bracket_rule,
                links (applicable_year: $year2024, applicable_status: $married, bracket: $m_bracket2);
            
            $m_bracket3 isa tax_bracket, has bracket_min 94300.0, has bracket_max 201050.0, has bracket_rate 0.22, has bracket_base_tax 10852.0;
            $married_bracket3_rule isa tax_bracket_rule,
                links (applicable_year: $year2024, applicable_status: $married, bracket: $m_bracket3);
            
            $m_bracket4 isa tax_bracket, has bracket_min 201050.0, has bracket_max 999999999.0, has bracket_rate 0.24, has bracket_base_tax 34337.0;
            $married_bracket4_rule isa tax_bracket_rule,
                links (applicable_year: $year2024, applicable_status: $married, bracket: $m_bracket4);
            
            # Head of household filing status
            $hoh isa filing_status, has filing_status_type "head_of_household", has filing_status_display "Head of Household";
            
            # Standard deduction for head of household
            $hoh_ded isa standard_deduction, has deduction_amount 21900.0;
            $hoh_ded_rule isa standard_deduction_rule,
                links (applicable_year: $year2024, applicable_status: $hoh, deduction: $hoh_ded);
            
            # Tax brackets for head of household
            $h_bracket1 isa tax_bracket, has bracket_min 0.0, has bracket_max 16550.0, has bracket_rate 0.10, has bracket_base_tax 0.0;
            $hoh_bracket1_rule isa tax_bracket_rule,
                links (applicable_year: $year2024, applicable_status: $hoh, bracket: $h_bracket1);
            
            $h_bracket2 isa tax_bracket, has bracket_min 16550.0, has bracket_max 63100.0, has bracket_rate 0.12, has bracket_base_tax 1655.0;
            $hoh_bracket2_rule isa tax_bracket_rule,
                links (applicable_year: $year2024, applicable_status: $hoh, bracket: $h_bracket2);
            
            $h_bracket3 isa tax_bracket, has bracket_min 63100.0, has bracket_max 100500.0, has bracket_rate 0.22, has bracket_base_tax 7241.0;
            $hoh_bracket3_rule isa tax_bracket_rule,
                links (applicable_year: $year2024, applicable_status: $hoh, bracket: $h_bracket3);
            
            $h_bracket4 isa tax_bracket, has bracket_min 100500.0, has bracket_max 999999999.0, has bracket_rate 0.24, has bracket_base_tax 15469.0;
            $hoh_bracket4_rule isa tax_bracket_rule,
                links (applicable_year: $year2024, applicable_status: $hoh, bracket: $h_bracket4);
            
            # Income types
            $w2 isa income_type, has field_id "income-w2", has field_name "W-2 Wages";
            $i1099 isa income_type, has field_id "income-1099", has field_name "1099 Income";
            
            # Itemized deduction types
            $salt isa itemized_deduction_type, 
                has deduction_type "state_local_taxes",
                has deduction_display "State/Local Taxes",
                has deduction_limit 10000.0;
            $salt_opt isa itemized_deduction_option,
                links (applicable_year: $year2024, type: $salt);
            
            $mortgage isa itemized_deduction_type,
                has deduction_type "mortgage_interest",
                has deduction_display "Mortgage Interest",
                has deduction_limit 999999999.0;  # No real limit
            $mortgage_opt isa itemized_deduction_option,
                links (applicable_year: $year2024, type: $mortgage);
            
            $charity isa itemized_deduction_type,
                has deduction_type "charitable_contributions",
                has deduction_display "Charitable Contributions",
                has deduction_limit 999999999.0;  # No real limit
            $charity_opt isa itemized_deduction_option,
                links (applicable_year: $year2024, type: $charity);
        """
        tx.query(tax_config).resolve()
        tx.commit()
        print("   ✓ Form metadata and tax configuration inserted")


def insert_function_metadata(driver):
    """Insert metadata about function behaviors and inputs"""
    
    print("\n📝 Inserting function metadata...")
    with driver.transaction("tax-system", TransactionType.WRITE) as tx:
        
        metadata = """
            insert
            # Function type metadata for calculate_total_income
            $calc_income_meta isa function_metadata,
                has calculation_function "calculate_total_income",
                has function_type "aggregation";
            
            $income_input isa input_spec,
                has input_description "Income sources for taxpayer",
                has input_entity_type "income_source",
                has input_attribute_type "amount";
            
            $spec1 isa function_input_spec,
                links (function: $calc_income_meta, input: $income_input);
            
            # Standard deduction metadata
            $std_ded_meta isa function_metadata,
                has calculation_function "get_standard_deduction",
                has function_type "lookup";
            
            $year_input isa input_spec,
                has input_description "Tax Year",
                has input_entity_type "tax_year",
                has input_attribute_type "year";
            
            $status_input isa input_spec,
                has input_description "Filing Status",
                has input_entity_type "filing_status",
                has input_attribute_type "filing_status_type";
            
            $spec2 isa function_input_spec,
                links (function: $std_ded_meta, input: $year_input);
            $spec3 isa function_input_spec,
                links (function: $std_ded_meta, input: $status_input);
            
            # Federal tax metadata
            $fed_tax_meta isa function_metadata,
                has calculation_function "calculate_federal_tax",
                has function_type "calculation";
            
            $bracket_input isa input_spec,
                has input_description "Tax bracket lookup",
                has input_entity_type "tax_bracket_rule",
                has input_attribute_type "bracket_rate";
            
            $spec4 isa function_input_spec,
                links (function: $fed_tax_meta, input: $bracket_input);
            
            # AGI metadata
            $agi_meta isa function_metadata,
                has calculation_function "calculate_agi",
                has function_type "calculation";
            
            # Taxable income metadata
            $taxable_meta isa function_metadata,
                has calculation_function "calculate_taxable_income",
                has function_type "calculation";
            
            # Tax bracket lookup metadata
            $tax_bracket_meta isa function_metadata,
                has calculation_function "get_tax_bracket",
                has function_type "lookup";
        """
        tx.query(metadata).resolve()
        tx.commit()
        print("   ✓ Function metadata inserted")


def demonstrate_true_semantic_calculations(driver):
    """Show how calculations work through function composition"""
    
    print("\n🧪 Demonstrating true semantic calculations...")
    
    # Insert test data
    with driver.transaction("tax-system", TransactionType.WRITE) as tx:
        test_data = """
            match
                $w2_type isa income_type, has field_id "income-w2";
                $i1099_type isa income_type, has field_id "income-1099";
                $year2024 isa tax_year, has year 2024;
                $single isa filing_status, has filing_status_type "single";
            insert
                $john isa taxpayer,
                    has ssn "123-45-6789",
                    has name "John Doe";
                
                # Income sources
                $income1 isa income_source,
                    links (earner: $john, type: $w2_type),
                    has amount 75000.0;
                $income2 isa income_source,
                    links (earner: $john, type: $i1099_type),
                    has amount 15000.0;
                
                # Filing info
                $filing isa tax_filing,
                    links (filer: $john, period: $year2024, status: $single);
        """
        tx.query(test_data).resolve()
        tx.commit()
        print("   ✓ Test taxpayer data inserted")
    
    # Query using the composed functions
    with driver.transaction("tax-system", TransactionType.READ) as tx:
        print("\n📊 Calculation Results (using composed functions):")
        print("-" * 60)
        
        # Call the master function that composes all calculations
        complete_return_query = """
            match
                $john isa taxpayer, has ssn "123-45-6789";
                $year isa tax_year, has year 2024;
                $status isa filing_status, has filing_status_type "single";
                let $total, $agi, $deduction, $taxable, $tax = calculate_complete_return($john, $year, $status);
            select $total, $agi, $deduction, $taxable, $tax;
        """
        
        result = tx.query(complete_return_query).resolve()
        row = next(result, None)
        if row:
            print(f"Total Income:        ${row.get('total').get_double():,.2f}")
            print(f"Adjusted Gross Income: ${row.get('agi').get_double():,.2f}")
            # deduction is an attribute, need to get its value
            deduction_val = row.get('deduction').get_double() if hasattr(row.get('deduction'), 'get_double') else row.get('deduction')
            print(f"Standard Deduction:   ${deduction_val:,.2f}")
            print(f"Taxable Income:      ${row.get('taxable').get_double():,.2f}")
            print(f"Federal Tax:         ${row.get('tax').get_double():,.2f}")
        
        # Show how to trace calculations through function metadata
        print("\n🔍 Tracing Calculations Through Function References:")
        print("-" * 60)
        
        trace_query = """
            match
                $field isa form_field,
                    has field_name $name,
                    has field_id $id,
                    has calculation_function $func;
            select $name, $id, $func;
            sort $id asc;
        """
        
        for result in tx.query(trace_query).resolve():
            name = result.get('name').get_string()
            field_id = result.get('id').get_string()
            func = result.get('func').get_string()
            print(f"{field_id}: {name}")
            print(f"   → Calculated by: {func}()")
        
        # Show dependencies
        print("\n🌳 Function Dependency Graph:")
        print("-" * 60)
        
        dep_query = """
            match
                (dependent_field: $dep, source_field: $src) isa field_dependency,
                    has depends_on_function $func;
                $dep has field_name $dep_name;
                $src has field_name $src_name;
            select $dep_name, $src_name, $func;
        """
        
        for result in tx.query(dep_query).resolve():
            dep = result.get('dep_name').get_string()
            src = result.get('src_name').get_string()
            func = result.get('func').get_string()
            print(f"{dep} depends on {src}")
            print(f"   → via function: {func}()")
        


def setup_true_semantic_database():
    """Main setup function"""
    
    print("🚀 Setting up TRUE Semantic Tax System...")
    print("   (Functions ARE the calculations, not just descriptions)")
    
    credentials = Credentials("admin", "password")
    options = DriverOptions(is_tls_enabled=False)
    driver = TypeDB.driver("localhost:1729", credentials, options)
    
    try:
        # Create or recreate database
        if driver.databases.contains("tax-system"):
            driver.databases.get("tax-system").delete()
        driver.databases.create("tax-system")
        print("   ✓ Database created")
        
        # Create schema with composable functions
        create_true_semantic_schema(driver)
        
        # Insert form metadata that references functions
        insert_form_metadata(driver)
        
        # Insert function metadata
        insert_function_metadata(driver)
        
        # Demonstrate calculations
        demonstrate_true_semantic_calculations(driver)
        
        print("\n✨ TRUE Semantic Tax System Ready!")
        print("   • Functions compose to create complex calculations")
        print("   • No redundant formula strings - functions ARE the formulas")
        print("   • Dependencies are explicit through function calls")
        print("   • The schema enforces calculation correctness")
        
    finally:
        driver.close()


if __name__ == "__main__":
    setup_true_semantic_database()
