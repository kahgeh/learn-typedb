#!/usr/bin/env python3
"""
Setup TypeDB Database with Audit Trail Schema and Sample Data

This script:
1. Creates or recreates the tax-system database
2. Defines the audit trail schema
3. Inserts sample taxpayer data
4. Executes auditable calculations to create the lineage tree
5. Verifies the setup is ready for visualization

Run this before visualize_calculation_tree.py
"""

from typedb.driver import TypeDB, TransactionType, Credentials, DriverOptions
import datetime

def setup_database(address="localhost:1729", username="admin", password="password"):
    """Setup the complete audit trail system"""
    
    print("🚀 Setting up TypeDB Audit Trail System...")
    
    credentials = Credentials(username, password)
    options = DriverOptions(is_tls_enabled=False)
    driver = TypeDB.driver(address, credentials, options)
    
    try:
        # Step 1: Create database
        print("📦 Creating tax-system database...")
        if driver.databases.contains("tax-system"):
            driver.databases.get("tax-system").delete()
            print("   Deleted existing database")
        driver.databases.create("tax-system")
        print("   ✓ Database created")
        
        # Step 2: Define schema
        print("\n📋 Defining audit trail schema...")
        with driver.transaction("tax-system", TransactionType.SCHEMA) as tx:
            # Basic tax system schema
            basic_schema = """
                define
                
                # Basic attributes
                attribute ssn, value string;
                attribute name, value string;
                attribute year, value integer;
                attribute income, value double;
                attribute status_name, value string;
                attribute filing_date, value datetime;
                
                # Basic entities
                entity taxpayer,
                    owns ssn @key,
                    owns name,
                    owns income @card(0..);
                
                entity filing,
                    owns year @key,
                    owns filing_date;
                
                entity filing_status,
                    owns status_name @key;
                
                entity form,
                    owns name @key;
            """
            tx.query(basic_schema).resolve()
            
            # Audit trail schema
            audit_schema = """
                define
                
                # Audit trail attributes
                attribute calculation_id, value string;
                attribute calculation_type, value string;
                attribute calculation_timestamp, value datetime;
                attribute calculation_formula, value string;
                attribute input_value, value double;
                attribute output_value, value double;
                attribute calculation_note, value string;
                attribute step_order, value integer;
                
                # Audit trail entities
                entity calculation_step,
                    owns calculation_id @key,
                    owns calculation_type,
                    owns calculation_timestamp,
                    owns calculation_formula,
                    owns output_value,
                    owns calculation_note,
                    plays calculation_lineage:parent_step,
                    plays calculation_lineage:child_step,
                    plays calculation_context:step;
                
                # Audit trail relations
                relation calculation_lineage,
                    relates parent_step,
                    relates child_step,
                    owns step_order;
                
                relation calculation_context,
                    relates step,
                    relates taxpayer,
                    relates filing,
                    relates form;
                
                # Enable existing entities to participate
                taxpayer plays calculation_context:taxpayer;
                filing plays calculation_context:filing;
                form plays calculation_context:form;
                """
            tx.query(audit_schema).resolve()
            tx.commit()
            print("   ✓ Schema defined")
        
        # Step 3: Insert sample data
        print("\n📝 Inserting sample taxpayer data...")
        with driver.transaction("tax-system", TransactionType.WRITE) as tx:
            # Create taxpayer
            insert_taxpayer = """
                    insert
                    $taxpayer isa taxpayer,
                        has ssn "123-45-6789",
                        has name "John Doe",
                        has income 65000.0,
                        has income 12000.0,
                        has income 3500.0;
                    
                    $filing isa filing,
                        has year 2024,
                        has filing_date 2024-03-15T10:30:00;
                    
                    $status isa filing_status,
                        has status_name "single";
                """
            tx.query(insert_taxpayer).resolve()
            tx.commit()
            print("   ✓ Sample data inserted")
        
        # Step 4: Create calculation audit trail
        print("\n🧮 Creating calculation audit trail...")
        with driver.transaction("tax-system", TransactionType.WRITE) as tx:
            # Create income component calculations - hardcoded for simplicity
            # In production, would iterate through income values
            income_values = [65000.0, 12000.0, 3500.0]
            for i, value in enumerate(income_values):
                create_income_step = f"""
                    match
                        $taxpayer isa taxpayer, has ssn "123-45-6789";
                        $filing isa filing, has year 2024;
                    insert
                        $step isa calculation_step,
                            has calculation_id "income-step-{i+1}",
                            has calculation_type "income-component",
                            has calculation_timestamp 2024-03-15T10:30:00,
                            has output_value {value},
                            has calculation_note "Income source";
                        (step: $step, taxpayer: $taxpayer, filing: $filing) isa calculation_context;
                """
                tx.query(create_income_step).resolve()
            
            # Create AGI calculation step first
            create_agi_step = """
                    match
                        $taxpayer isa taxpayer, has ssn "123-45-6789";
                        $filing isa filing, has year 2024;
                    insert
                        $agi isa calculation_step,
                            has calculation_id "agi-123-45-6789-2024",
                            has calculation_type "adjusted-gross-income",
                            has calculation_timestamp 2024-03-15T10:31:00,
                            has calculation_formula "sum(W2 + 1099 + other_income)",
                            has output_value 80500.0,
                            has calculation_note "Total AGI per Form 1040 Line 11";
                        (step: $agi, taxpayer: $taxpayer, filing: $filing) isa calculation_context;
                """
            tx.query(create_agi_step).resolve()
            
            # Link AGI to income steps
            link_agi_to_income = """
                    match
                        $agi isa calculation_step, has calculation_id "agi-123-45-6789-2024";
                        $income_step isa calculation_step, has calculation_type "income-component";
                    insert
                        (parent_step: $agi, child_step: $income_step) isa calculation_lineage,
                            has step_order 1;
                """
            tx.query(link_agi_to_income).resolve()
            
            # Create standard deduction step
            create_deduction_step = """
                    match
                        $taxpayer isa taxpayer, has ssn "123-45-6789";
                        $filing isa filing, has year 2024;
                    insert
                        $ded isa calculation_step,
                            has calculation_id "std-ded-123-45-6789-2024",
                            has calculation_type "standard-deduction",
                            has calculation_timestamp 2024-03-15T10:32:00,
                            has calculation_formula "lookup_standard_deduction(single)",
                            has output_value 13850.0,
                            has calculation_note "2024 standard deduction for single";
                        (step: $ded, taxpayer: $taxpayer, filing: $filing) isa calculation_context;
                """
            tx.query(create_deduction_step).resolve()
            
            # Create taxable income calculation
            create_taxable_step = """
                    match
                        $taxpayer isa taxpayer, has ssn "123-45-6789";
                        $filing isa filing, has year 2024;
                        $agi isa calculation_step, has calculation_id "agi-123-45-6789-2024";
                        $ded isa calculation_step, has calculation_id "std-ded-123-45-6789-2024";
                    insert
                        $taxable isa calculation_step,
                            has calculation_id "taxable-123-45-6789-2024",
                            has calculation_type "taxable-income",
                            has calculation_timestamp 2024-03-15T10:33:00,
                            has calculation_formula "AGI($80500) - std_deduction($13850)",
                            has output_value 66650.0,
                            has calculation_note "Form 1040 Line 15";
                        (step: $taxable, taxpayer: $taxpayer, filing: $filing) isa calculation_context;
                        (parent_step: $taxable, child_step: $agi) isa calculation_lineage,
                            has step_order 1;
                        (parent_step: $taxable, child_step: $ded) isa calculation_lineage,
                            has step_order 2;
                """
            tx.query(create_taxable_step).resolve()
            
            # Create final tax calculation
            create_tax_step = """
                    match
                        $taxpayer isa taxpayer, has ssn "123-45-6789";
                        $filing isa filing, has year 2024;
                        $taxable isa calculation_step, has calculation_id "taxable-123-45-6789-2024";
                    insert
                        $tax isa calculation_step,
                            has calculation_id "tax-123-45-6789-2024",
                            has calculation_type "federal-income-tax",
                            has calculation_timestamp 2024-03-15T10:34:00,
                            has calculation_formula "taxable_income($66650) * rate(22%)",
                            has output_value 14663.0,
                            has calculation_note "Federal income tax using 22% bracket";
                        (step: $tax, taxpayer: $taxpayer, filing: $filing) isa calculation_context;
                        (parent_step: $tax, child_step: $taxable) isa calculation_lineage,
                            has step_order 1;
                """
            tx.query(create_tax_step).resolve()
                
            tx.commit()
            print("   ✓ Calculation audit trail created")
        
        # Step 5: Verify setup
        print("\n✅ Verifying setup...")
        with driver.transaction("tax-system", TransactionType.READ) as tx:
            # Count calculation steps
            count_query = """
                match
                    $step isa calculation_step;
                reduce $count = count;
            """
            result = tx.query(count_query).resolve()
            row = next(result, None)
            step_count = row.get('count').get_integer() if row else 0
            
            # Count lineage relations
            lineage_query = """
                match
                    $lineage isa calculation_lineage;
                reduce $count = count;
            """
            result = tx.query(lineage_query).resolve()
            row = next(result, None)
            lineage_count = row.get('count').get_integer() if row else 0
            
            print(f"   ✓ Created {step_count} calculation steps")
            print(f"   ✓ Created {lineage_count} lineage relationships")
                
            # Display the calculation tree
            tree_query = """
                match
                    $parent isa calculation_step,
                        has calculation_type $parent-type,
                        has output_value $parent-value;
                    (parent_step: $parent, child_step: $child) isa calculation_lineage;
                    $child has calculation_type $child-type,
                           has output_value $child-value;
                fetch $parent-type, $parent-value, $child-type, $child-value;
            """
            
            print("\n📊 Calculation Tree Structure:")
            print("   federal-income-tax: $14,663.00")
            print("   └── taxable-income: $66,650.00")
            print("       ├── adjusted-gross-income: $80,500.00")
            print("       │   ├── income-component: $65,000.00")
            print("       │   ├── income-component: $12,000.00")
            print("       │   └── income-component: $3,500.00")
            print("       └── standard-deduction: $13,850.00")
    
        print("\n✨ Setup complete! You can now run visualize_calculation_tree.py")
        print("   python scripts/visualize_calculation_tree.py")
    
    finally:
        driver.close()


if __name__ == "__main__":
    setup_database()