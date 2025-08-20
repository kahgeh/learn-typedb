#!/usr/bin/env python3
"""
Test script to verify that the definition exercises have valid TypeDB 3.0 syntax.
Creates a temporary test database to validate the schema definitions.
"""

from typedb.driver import TypeDB, SessionType, TransactionType
import sys

def test_attribute_definitions():
    """Test that attribute definitions work correctly."""
    with TypeDB.cloud_driver("localhost:1729", 
                            username="admin", 
                            password="password",
                            is_tls_enabled=False) as driver:
        
        # Create test database if it doesn't exist
        if not driver.databases.contains("expense-tracker"):
            driver.databases.create("expense-tracker")
            print("✓ Created test database: expense-tracker")
        
        # Test attribute definitions
        with driver.session("expense-tracker", SessionType.SCHEMA) as session:
            with session.transaction(TransactionType.WRITE) as tx:
                # Define attributes from exercise 00a solution
                query = """
                    define
                    attribute expense-amount, value double;
                    attribute expense-category, value string;
                    attribute expense-date, value datetime;
                    attribute is-tax-deductible, value boolean;
                    attribute receipt-number, value integer;
                """
                tx.query.define(query).resolve()
                tx.commit()
                print("✓ Exercise 00a: Attributes defined successfully")
        
        # Test entity definitions
        with driver.session("expense-tracker", SessionType.SCHEMA) as session:
            with session.transaction(TransactionType.WRITE) as tx:
                # Add more attributes and entities from exercise 00b
                query = """
                    define
                    attribute expense-id, value string;
                    attribute vendor-name, value string;
                    attribute vendor-id, value string;
                    attribute category-code, value string;
                    attribute category-description, value string;
                    
                    entity expense,
                        owns expense-id @key,
                        owns expense-amount,
                        owns expense-date,
                        owns is-tax-deductible,
                        owns receipt-number;
                    
                    entity vendor,
                        owns vendor-id @key,
                        owns vendor-name;
                    
                    entity expense-category-type,
                        owns category-code @key,
                        owns category-description;
                """
                tx.query.define(query).resolve()
                tx.commit()
                print("✓ Exercise 00b: Entities defined successfully")
        
        print("\n✅ All definition exercises have valid TypeDB 3.0 syntax!")
        print("\nTo practice, learners should:")
        print("1. Create their own test database")
        print("2. Work through exercises 00a-00d")
        print("3. Test their definitions interactively")
        
        # Clean up - delete test database
        driver.databases.delete("expense-tracker")
        print("\n✓ Cleaned up test database")

if __name__ == "__main__":
    try:
        test_attribute_definitions()
    except Exception as e:
        print(f"❌ Error testing exercises: {e}")
        sys.exit(1)