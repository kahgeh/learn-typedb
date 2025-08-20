#!/usr/bin/env python3
"""
Simplified setup script for TypeDB tax system database.
Uses TypeDB Python driver directly instead of console commands.
"""

from typedb.driver import TypeDB, Credentials, DriverOptions, TransactionType
from pathlib import Path
import sys


def main():
    """Main setup function."""
    base_path = Path(__file__).parent.parent
    schema_file = base_path / "schemas" / "tax-schema-v3.tql"
    data_file = base_path / "data" / "sample-tax-data-v3.tql"
    
    print("Setting up TypeDB Tax System Database")
    print("=" * 40)
    
    # Connect to TypeDB
    print("\nConnecting to TypeDB...")
    try:
        # Create credentials and options
        credentials = Credentials("admin", "password")
        options = DriverOptions(is_tls_enabled=False)
        
        driver = TypeDB.driver("localhost:1729", credentials, options)
        print("Connected successfully!")
    except Exception as e:
        print(f"Failed to connect to TypeDB: {e}")
        print("\nPlease ensure TypeDB server is running:")
        print("  typedb server")
        sys.exit(1)
    
    try:
        # Get database manager
        databases = driver.databases
        
        # Delete existing database if it exists
        if databases.contains("tax-system"):
            print("\nDeleting existing tax-system database...")
            databases.get("tax-system").delete()
            print("Existing database deleted.")
        
        # Create new database
        print("\nCreating tax-system database...")
        databases.create("tax-system")
        print("Database created successfully!")
        
        # Load schema
        print("\nLoading schema...")
        with open(schema_file, 'r') as f:
            schema_content = f.read()
        
        with driver.transaction("tax-system", TransactionType.SCHEMA) as tx:
            result = tx.query(schema_content)
            result.resolve()  # Execute the query
            tx.commit()
        print("Schema loaded successfully!")
        
        # Load sample data
        print("\nLoading sample data...")
        with open(data_file, 'r') as f:
            data_content = f.read()
        
        with driver.transaction("tax-system", TransactionType.WRITE) as tx:
            result = tx.query(data_content)
            result.resolve()  # Execute the query
            tx.commit()
        print("Sample data loaded successfully!")
        
        print("\n" + "=" * 40)
        print("Setup complete! Database 'tax-system' is ready.")
        print("\nYou can now:")
        print("1. Run queries using: python scripts/query_examples_v3.py")
        print("2. Explore the schema and data using TypeDB Console")
        print("3. Implement the field dependency query (see TODO in query_examples.py)")
        
    except Exception as e:
        print(f"\nError during setup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        driver.close()


if __name__ == "__main__":
    main()