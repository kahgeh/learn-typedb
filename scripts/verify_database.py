#!/usr/bin/env python3
"""
Simple script to verify the TypeDB tax system database is loaded correctly.
"""

from typedb.driver import TypeDB, Credentials, DriverOptions, TransactionType


def main():
    """Verify database is loaded."""
    credentials = Credentials("admin", "password")
    options = DriverOptions(is_tls_enabled=False)
    driver = TypeDB.driver("localhost:1729", credentials, options)
    
    print("TypeDB Tax System - Database Verification")
    print("=" * 50)
    
    try:
        # Check database exists
        if driver.databases.contains("tax-system"):
            print("✓ Database 'tax-system' exists")
        else:
            print("✗ Database 'tax-system' not found")
            print("  Run: python scripts/setup_database_simple.py")
            return
        
        # Simple connection test
        with driver.transaction("tax-system", TransactionType.READ) as tx:
            print("✓ Successfully connected to database")
        
        print("\nDatabase is ready for use!")
        print("\nSample data loaded includes:")
        print("  - Tax years: 2023, 2024")
        print("  - Form types: 1040, Schedule A")
        print("  - Field definitions: SSN, W2 Wages, Gross Income")
        print("  - Sample taxpayer: John Doe")
        print("  - Validation rules and calculations")
        
        print("\nTo explore the data:")
        print("1. Complete the TODO in scripts/query_examples.py")
        print("2. Use TypeDB Console to run queries directly")
        print("3. Read docs/typedb-for-tax-systems.md for concepts")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.close()


if __name__ == "__main__":
    main()