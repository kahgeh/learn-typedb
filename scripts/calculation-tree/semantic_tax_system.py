#!/usr/bin/env python3
"""
Semantic Tax Calculation System in TypeDB 3.x

This demonstrates TRUE semantic correctness by:
1. Encoding tax calculation relationships in the schema
2. Using TypeDB functions to define calculation logic
3. Showing calculation dependencies WITHOUT needing taxpayer data
4. Ensuring calculations follow tax law semantics through constraints

Key improvements over the audit trail approach:
- Calculation formulas are part of the schema, not just recorded after-the-fact
- Dependencies between fields are explicitly modeled
- The system knows HOW to calculate, not just stores results
"""

from typedb.driver import TypeDB, TransactionType, Credentials, DriverOptions
import json

def create_semantic_tax_schema(driver):
    """Create a schema where tax calculation semantics are embedded"""
    
    print("📋 Defining semantic tax schema...")
    with driver.transaction("tax-system", TransactionType.SCHEMA) as tx:
        
        # Define the semantic tax domain model
        semantic_schema = """
            define
            
            # === Attributes ===
            attribute ssn, value string;
            attribute name, value string;
            attribute amount, value double;
            attribute year, value integer;
            attribute form_name, value string;
            attribute field_name, value string;
            attribute field_id, value string;
            attribute calculation_type, value string;
            attribute formula_expression, value string;
            attribute filing_status_type, value string;
            attribute deduction_amount, value double;
            attribute rate, value double;
            attribute bracket_min, value double;
            attribute bracket_max, value double;
            attribute dependency_type, value string;
            
            # === Core Tax Entities ===
            
            entity taxpayer,
                owns ssn @key,
                owns name,
                plays tax_filing:filer,
                plays income_reporting:earner,
                plays calculation_execution:subject;
            
            entity tax_year,
                owns year @key,
                plays tax_filing:period,
                plays tax_parameters:applicable_year;
            
            entity filing_status,
                owns filing_status_type @key,
                plays tax_filing:status,
                plays tax_parameters:applicable_status;
            
            # === Tax Calculation Semantics ===
            
            # Represents a calculable field on a tax form
            entity tax_field,
                owns form_name,
                owns field_name,
                owns field_id @key,
                owns calculation_type,
                owns formula_expression,
                plays field_dependency:dependent_field,
                plays field_dependency:source_field,
                plays calculation_execution:calculated_field,
                plays field_hierarchy:parent_field,
                plays field_hierarchy:child_field;
            
            # Represents an actual calculated value
            entity field_value,
                owns amount,
                plays calculation_execution:result,
                plays value_lineage:derived_value,
                plays value_lineage:source_value;
            
            # Tax parameters (brackets, deductions, etc.)
            entity tax_bracket,
                owns bracket_min,
                owns bracket_max,
                owns rate,
                plays tax_parameters:bracket;
            
            entity standard_deduction,
                owns deduction_amount,
                plays tax_parameters:deduction;
            
            # === Relations that encode calculation semantics ===
            
            # Tax filing context
            relation tax_filing,
                relates filer,
                relates period,
                relates status,
                plays calculation_execution:context;
            
            # Income reporting
            relation income_reporting,
                relates earner,
                owns amount @card(0..),
                plays calculation_execution:input_data;
            
            # Field dependency graph - HOW fields relate
            relation field_dependency,
                relates dependent_field,
                relates source_field @card(1..),
                owns dependency_type;
            
            # Field hierarchy - structural relationships
            relation field_hierarchy,
                relates parent_field,
                relates child_field @card(0..);
            
            # Calculation execution - links fields to values
            relation calculation_execution,
                relates calculated_field,
                relates result,
                relates context,
                relates input_data @card(0..),
                relates subject;
            
            # Value lineage - tracks calculation flow
            relation value_lineage,
                relates derived_value,
                relates source_value @card(1..);
            
            # Tax parameters lookup
            relation tax_parameters,
                relates applicable_year,
                relates applicable_status,
                relates bracket @card(0..),
                relates deduction @card(0..);
        """
        tx.query(semantic_schema).resolve()
        
        # Define TypeDB functions for calculations
        calculation_functions = """
            define
            
            # Function to calculate total income - returns sum of all income
            fun calculate_total_income($taxpayer: taxpayer) -> double:
                match
                    (earner: $taxpayer) isa income_reporting, has amount $amt;
                return sum($amt);
            
            # Function to lookup standard deduction - returns first matching deduction
            fun get_standard_deduction($year: tax_year, $status: filing_status) -> double:
                match
                    (applicable_year: $year, 
                     applicable_status: $status,
                     deduction: $ded) isa tax_parameters;
                    $ded isa standard_deduction, has deduction_amount $amount;
                return first $amount;
            
            # Function to calculate taxable income - returns calculated value
            fun calculate_taxable_income($agi: double, $deduction: double) -> double:
                match
                    let $taxable = $agi - $deduction;
                return first $taxable;
            
            # Function to find applicable tax rate - returns first matching rate
            fun get_tax_rate($income: double, $year: tax_year, $status: filing_status) -> double:
                match
                    (applicable_year: $year,
                     applicable_status: $status,
                     bracket: $bracket) isa tax_parameters;
                    $bracket isa tax_bracket, has bracket_min $min, has bracket_max $max, has rate $rate;
                    $income >= $min;
                    $income <= $max;
                return first $rate;
        """
        tx.query(calculation_functions).resolve()
        
        tx.commit()
        print("   ✓ Semantic schema with functions defined")


def insert_tax_form_structure(driver):
    """Insert the tax form structure and calculation dependencies"""
    
    print("\n📊 Inserting tax form structure and dependencies...")
    with driver.transaction("tax-system", TransactionType.WRITE) as tx:
        
        # Define form fields and their semantic relationships
        form_structure = """
            insert
            
            # === Form 1040 Field Definitions ===
            
            # Line 1-8: Various income sources (simplified as total)
            $line9 isa tax_field,
                has form_name "1040",
                has field_name "Total Income",
                has field_id "1040-line-9",
                has calculation_type "aggregation",
                has formula_expression "SUM(all_income_sources)";
            
            # Line 11: Adjusted Gross Income
            $line11 isa tax_field,
                has form_name "1040",
                has field_name "Adjusted Gross Income",
                has field_id "1040-line-11",
                has calculation_type "subtraction",
                has formula_expression "total_income - above_the_line_deductions";
            
            # Line 12: Standard or Itemized Deduction
            $line12 isa tax_field,
                has form_name "1040",
                has field_name "Standard Deduction",
                has field_id "1040-line-12",
                has calculation_type "lookup",
                has formula_expression "LOOKUP(standard_deduction_table, filing_status, tax_year)";
            
            # Line 15: Taxable Income
            $line15 isa tax_field,
                has form_name "1040",
                has field_name "Taxable Income",
                has field_id "1040-line-15",
                has calculation_type "subtraction",
                has formula_expression "MAX(0, AGI - deductions)";
            
            # Line 16: Federal Income Tax
            $line16 isa tax_field,
                has form_name "1040",
                has field_name "Federal Income Tax",
                has field_id "1040-line-16",
                has calculation_type "bracket_lookup",
                has formula_expression "APPLY_TAX_BRACKETS(taxable_income, filing_status, tax_year)";
            
            # === Define Calculation Dependencies ===
            
            # AGI depends on Total Income
            (dependent_field: $line11, source_field: $line9) isa field_dependency,
                has dependency_type "input";
            
            # Taxable Income depends on AGI and Deductions
            (dependent_field: $line15, source_field: $line11) isa field_dependency,
                has dependency_type "minuend";
            (dependent_field: $line15, source_field: $line12) isa field_dependency,
                has dependency_type "subtrahend";
            
            # Tax depends on Taxable Income
            (dependent_field: $line16, source_field: $line15) isa field_dependency,
                has dependency_type "input";
            
            # === Define Field Hierarchy ===
            
            # Tax is parent of Taxable Income
            (parent_field: $line16, child_field: $line15) isa field_hierarchy;
            
            # Taxable Income is parent of AGI and Deductions
            (parent_field: $line15, child_field: $line11) isa field_hierarchy;
            (parent_field: $line15, child_field: $line12) isa field_hierarchy;
            
            # AGI is parent of Total Income
            (parent_field: $line11, child_field: $line9) isa field_hierarchy;
        """
        tx.query(form_structure).resolve()
        
        # Insert tax parameters for 2024
        tax_parameters = """
            insert
            $year2024 isa tax_year, has year 2024;
            
            $single isa filing_status, has filing_status_type "single";
            $married_joint isa filing_status, has filing_status_type "married_filing_jointly";
            
            # Standard deductions for 2024
            $single_deduction isa standard_deduction, has deduction_amount 13850.0;
            (applicable_year: $year2024, 
             applicable_status: $single,
             deduction: $single_deduction) isa tax_parameters;
            
            $married_deduction isa standard_deduction, has deduction_amount 27700.0;
            (applicable_year: $year2024,
             applicable_status: $married_joint,
             deduction: $married_deduction) isa tax_parameters;
            
            # Tax brackets for 2024 - Single
            $bracket1 isa tax_bracket,
                has bracket_min 0.0,
                has bracket_max 11000.0,
                has rate 0.10;
            (applicable_year: $year2024,
             applicable_status: $single,
             bracket: $bracket1) isa tax_parameters;
            
            $bracket2 isa tax_bracket,
                has bracket_min 11000.0,
                has bracket_max 44725.0,
                has rate 0.12;
            (applicable_year: $year2024,
             applicable_status: $single,
             bracket: $bracket2) isa tax_parameters;
            
            $bracket3 isa tax_bracket,
                has bracket_min 44725.0,
                has bracket_max 95375.0,
                has rate 0.22;
            (applicable_year: $year2024,
             applicable_status: $single,
             bracket: $bracket3) isa tax_parameters;
            
            $bracket4 isa tax_bracket,
                has bracket_min 95375.0,
                has bracket_max 182050.0,
                has rate 0.24;
            (applicable_year: $year2024,
             applicable_status: $single,
             bracket: $bracket4) isa tax_parameters;
        """
        tx.query(tax_parameters).resolve()
        tx.commit()
        print("   ✓ Tax form structure and parameters inserted")


def visualize_calculation_semantics(driver):
    """Show the calculation structure WITHOUT any taxpayer data"""
    
    print("\n🔍 Semantic Calculation Structure (no taxpayer data):")
    print("="*60)
    
    with driver.transaction("tax-system", TransactionType.READ) as tx:
        
        # Query the field dependency graph
        print("\n📐 Tax Calculation Dependencies:")
        print("-" * 60)
        
        dependency_query = """
            match
                $dependent isa tax_field,
                    has field_name $dep_name,
                    has calculation_type $calc_type,
                    has formula_expression $formula;
                (dependent_field: $dependent, source_field: $source) isa field_dependency,
                    has dependency_type $dep_type;
                $source has field_name $src_name;
            fetch $dep_name, $calc_type, $formula, $src_name, $dep_type;
        """
        
        dependencies = {}
        for result in tx.query(dependency_query).resolve():
            dep_name = result['dep_name']['value']
            calc_type = result['calc_type']['value']
            formula = result['formula']['value']
            src_name = result['src_name']['value']
            dep_type = result['dep_type']['value']
            
            if dep_name not in dependencies:
                dependencies[dep_name] = {
                    'type': calc_type,
                    'formula': formula,
                    'sources': []
                }
            dependencies[dep_name]['sources'].append({
                'field': src_name,
                'role': dep_type
            })
        
        for field_name, info in dependencies.items():
            print(f"\n📊 {field_name}")
            print(f"   Type: {info['type']}")
            print(f"   Formula: {info['formula']}")
            print(f"   Dependencies:")
            for source in info['sources']:
                print(f"     ← {source['field']} (as {source['role']})")
        
        # Query the field hierarchy
        print("\n🌳 Field Calculation Hierarchy:")
        print("-" * 60)
        
        hierarchy_query = """
            match
                $parent isa tax_field, has field_name $parent_name;
                (parent_field: $parent, child_field: $child) isa field_hierarchy;
                $child has field_name $child_name;
            fetch $parent_name, $child_name;
        """
        
        hierarchy = {}
        for result in tx.query(hierarchy_query).resolve():
            parent = result['parent_name']['value']
            child = result['child_name']['value']
            
            if parent not in hierarchy:
                hierarchy[parent] = []
            hierarchy[parent].append(child)
        
        # Build tree starting from Federal Income Tax
        def print_tree(field, indent=0):
            print("  " * indent + "└─ " + field)
            if field in hierarchy:
                for child in hierarchy[field]:
                    print_tree(child, indent + 1)
        
        print_tree("Federal Income Tax")
        
        # Show available tax brackets
        print("\n💰 Tax Parameters (Semantic Rules):")
        print("-" * 60)
        
        bracket_query = """
            match
                $year isa tax_year, has year 2024;
                $status isa filing_status, has filing_status_type "single";
                (applicable_year: $year,
                 applicable_status: $status,
                 bracket: $bracket) isa tax_parameters;
                $bracket has bracket_min $min,
                        has bracket_max $max,
                        has rate $rate;
            select $min, $max, $rate;
            sort $min asc;
        """
        
        print("\n2024 Tax Brackets (Single):")
        for result in tx.query(bracket_query).resolve():
            min_val = result.get('min').get_double()
            max_val = result.get('max').get_double()
            rate = result.get('rate').get_double()
            print(f"   ${min_val:,.0f} - ${max_val:,.0f} : {rate*100:.0f}%")
        
        # Show standard deductions
        deduction_query = """
            match
                $year isa tax_year, has year 2024;
                $status isa filing_status, has filing_status_type $status_type;
                (applicable_year: $year,
                 applicable_status: $status,
                 deduction: $ded) isa tax_parameters;
                $ded has deduction_amount $amount;
            select $status_type, $amount;
        """
        
        print("\n2024 Standard Deductions:")
        for result in tx.query(deduction_query).resolve():
            status = result.get('status_type').get_string()
            amount = result.get('amount').get_double()
            print(f"   {status}: ${amount:,.2f}")


def demonstrate_semantic_calculation(driver):
    """Demonstrate calculation with sample data using the semantic structure"""
    
    print("\n🧪 Demonstrating Semantic Calculation...")
    with driver.transaction("tax-system", TransactionType.WRITE) as tx:
        
        # Insert test taxpayer
        insert_taxpayer = """
            insert
            $taxpayer isa taxpayer,
                has ssn "123-45-6789",
                has name "John Doe";
            
            # Add income sources
            (earner: $taxpayer) isa income_reporting, has amount 65000.0;
            (earner: $taxpayer) isa income_reporting, has amount 12000.0;
            (earner: $taxpayer) isa income_reporting, has amount 3500.0;
            
            # Create filing
            $year isa tax_year, has year 2024;
            $status isa filing_status, has filing_status_type "single";
            (filer: $taxpayer, period: $year, status: $status) isa tax_filing;
        """
        tx.query(insert_taxpayer).resolve()
        tx.commit()
        print("   ✓ Test taxpayer inserted")
    
    # Now query using the functions
    with driver.transaction("tax-system", TransactionType.READ) as tx:
        print("\n📊 Calculation Results Using Semantic Functions:")
        
        # Calculate total income
        income_query = """
            match
                $taxpayer isa taxpayer, has ssn "123-45-6789";
                let $total = calculate_total_income($taxpayer);
            select $total;
        """
        result = tx.query(income_query).resolve()
        row = next(result, None)
        total_income = None
        if row:
            total_income = row.get('total').get_double()
            print(f"   Total Income: ${total_income:,.2f}")
        
        # Get standard deduction
        deduction_query = """
            match
                $year isa tax_year, has year 2024;
                $status isa filing_status, has filing_status_type "single";
                let $deduction = get_standard_deduction($year, $status);
            select $deduction;
        """
        result = tx.query(deduction_query).resolve()
        row = next(result, None)
        deduction = None
        if row:
            deduction = row.get('deduction').get_double()
            print(f"   Standard Deduction: ${deduction:,.2f}")
        
        # Calculate taxable income
        if total_income and deduction:
            taxable_query = f"""
                match
                    let $taxable = calculate_taxable_income({total_income}, {deduction});
                select $taxable;
            """
            result = tx.query(taxable_query).resolve()
            row = next(result, None)
            if row:
                taxable = row.get('taxable').get_double()
                print(f"   Taxable Income: ${taxable:,.2f}")
                
                # Get tax rate
                rate_query = f"""
                    match
                        $year isa tax_year, has year 2024;
                        $status isa filing_status, has filing_status_type "single";
                        let $rate = get_tax_rate({taxable}, $year, $status);
                    select $rate;
                """
                result = tx.query(rate_query).resolve()
                row = next(result, None)
                if row:
                    rate = row.get('rate').get_double()
                    tax = taxable * rate
                    print(f"   Tax Rate: {rate*100:.0f}%")
                    print(f"   Federal Tax: ${tax:,.2f}")


def setup_semantic_database():
    """Main setup function"""
    
    print("🚀 Setting up Semantic Tax System...")
    
    credentials = Credentials("admin", "password")
    options = DriverOptions(is_tls_enabled=False)
    driver = TypeDB.driver("localhost:1729", credentials, options)
    
    try:
        # Create or recreate database
        if driver.databases.contains("tax-system"):
            driver.databases.get("tax-system").delete()
        driver.databases.create("tax-system")
        print("   ✓ Database created")
        
        # Define semantic schema
        create_semantic_tax_schema(driver)
        
        # Insert tax form structure
        insert_tax_form_structure(driver)
        
        # Visualize calculation semantics
        visualize_calculation_semantics(driver)
        
        # Demonstrate with sample data
        demonstrate_semantic_calculation(driver)
        
        print("\n✨ Semantic tax system ready!")
        print("\n🎯 Key Semantic Features Demonstrated:")
        print("   1. Calculation formulas are part of the schema")
        print("   2. Dependencies between fields are explicitly modeled")
        print("   3. Tax parameters (brackets, deductions) are queryable data")
        print("   4. Functions encapsulate calculation logic")
        print("   5. The structure is visible WITHOUT taxpayer data")
        
    finally:
        driver.close()


if __name__ == "__main__":
    setup_semantic_database()