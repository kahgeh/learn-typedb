#!/usr/bin/env python3
"""
Example TypeQL queries for the tax system database.
Compatible with TypeDB 3.0 and Python driver 3.4+
"""

from typedb.driver import TypeDB, Credentials, DriverOptions, TransactionType
import json


class TaxSystemQuerier:
    def __init__(self):
        self.credentials = Credentials("admin", "password")
        self.options = DriverOptions(is_tls_enabled=False)
        self.driver = TypeDB.driver("localhost:1729", self.credentials, self.options)
        self.database = "tax-system"
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.driver.close()
    
    def run_fetch_query(self, query):
        """Helper to run a fetch query and return parsed results."""
        with self.driver.transaction(self.database, TransactionType.READ) as tx:
            result = tx.query(query)
            answers = result.resolve()
            
            parsed_results = []
            for answer in answers:
                parsed_results.append(json.loads(answer.to_json()))
            return parsed_results
    
    def get_tax_years(self):
        """Retrieve all tax years in the system."""
        query = "match $x isa tax-year; fetch $x;"
        results = self.run_fetch_query(query)
        
        years = []
        for r in results:
            x_data = r.get("x", {})
            if "year" in x_data and "jurisdiction" in x_data:
                years.append({
                    "year": x_data["year"][0]["value"],
                    "jurisdiction": x_data["jurisdiction"][0]["value"]
                })
        return years
    
    def get_form_types(self):
        """Retrieve all form types."""
        query = "match $x isa form-type; fetch $x;"
        results = self.run_fetch_query(query)
        
        forms = []
        for r in results:
            x_data = r.get("x", {})
            if all(k in x_data for k in ["form-code", "form-name", "category"]):
                forms.append({
                    "code": x_data["form-code"][0]["value"],
                    "name": x_data["form-name"][0]["value"],
                    "category": x_data["category"][0]["value"]
                })
        return forms
    
    def get_form_fields(self, form_version="1040-2024-v1"):
        """Get all fields for a specific form version."""
        query = f"""match 
            $form isa form-definition, has version "{form_version}";
            $rel (container: $form, contained-field: $field) isa field-containment;
            fetch $rel, $field;"""
        
        results = self.run_fetch_query(query)
        
        fields = []
        for r in results:
            field_data = r.get("field", {})
            rel_data = r.get("rel", {})
            
            if field_data and rel_data:
                field_info = {
                    "field_id": field_data.get("field-id", [{}])[0].get("value", ""),
                    "field_name": field_data.get("field-name", [{}])[0].get("value", ""),
                    "field_type": field_data.get("field-type", [{}])[0].get("value", ""),
                    "order": rel_data.get("field-order", [{}])[0].get("value", 0),
                    "section": rel_data.get("section-name", [{}])[0].get("value", "")
                }
                if field_info["field_id"]:
                    fields.append(field_info)
        
        # Sort by order
        fields.sort(key=lambda x: x["order"])
        return fields
    
    def get_field_dependencies(self, field_id):
        """Get all fields that depend on or influence a given field.
        
        TODO(human): Implement this query to find field dependencies
        This should find both:
        1. Fields that this field depends on (where this field is the target)
        2. Fields that depend on this field (where this field is the source)
        
        Hint: Use the field-dependency relation which has source-field and target-field roles.
        Return a dictionary with "depends_on" and "influences" lists.
        """
        pass
    
    def get_validation_rules(self):
        """Get all validation rules in the system."""
        query = "match $rule isa validation-rule; fetch $rule;"
        results = self.run_fetch_query(query)
        
        rules = []
        for r in results:
            rule_data = r.get("rule", {})
            if rule_data:
                # Extract the field that this rule validates
                # This would need a more complex query to get the related field
                rules.append({
                    "expression": rule_data.get("rule-expression", [{}])[0].get("value", ""),
                    "error_message": rule_data.get("error-message", [{}])[0].get("value", ""),
                    "severity": rule_data.get("severity", [{}])[0].get("value", "")
                })
        return rules
    
    def get_calculations(self):
        """Get all calculation relationships."""
        query = "match $calc isa calculation; fetch $calc;"
        results = self.run_fetch_query(query)
        
        calculations = []
        for r in results:
            calc_data = r.get("calc", {})
            if calc_data:
                calculations.append({
                    "expression": calc_data.get("calculation-expression", [{}])[0].get("value", ""),
                    "calc_type": calc_data.get("calculation-type", [{}])[0].get("value", "")
                })
        return calculations
    
    def count_entities(self):
        """Count entities of each type."""
        entity_types = ["tax-year", "form-type", "form-definition", 
                       "field-definition", "taxpayer", "filing"]
        counts = {}
        
        for entity_type in entity_types:
            query = f"match $x isa {entity_type}; fetch $x;"
            results = self.run_fetch_query(query)
            counts[entity_type] = len(results)
        
        return counts


def main():
    """Demonstrate various queries."""
    with TaxSystemQuerier() as querier:
        print("TypeDB Tax System Query Examples")
        print("=" * 50)
        
        # Count entities
        print("\n0. Entity Counts:")
        print("-" * 30)
        counts = querier.count_entities()
        for entity_type, count in counts.items():
            print(f"  - {entity_type}: {count}")
        
        # 1. Get tax years
        print("\n1. Tax Years in the System:")
        print("-" * 30)
        try:
            years = querier.get_tax_years()
            for year in years:
                print(f"  - {year['year']} ({year['jurisdiction']})")
        except Exception as e:
            print(f"  Error: {e}")
        
        # 2. Get form types
        print("\n2. Available Form Types:")
        print("-" * 30)
        try:
            forms = querier.get_form_types()
            for form in forms:
                print(f"  - {form['code']}: {form['name']} [{form['category']}]")
        except Exception as e:
            print(f"  Error: {e}")
        
        # 3. Get form fields
        print("\n3. Fields in Form 1040 (2024):")
        print("-" * 30)
        try:
            fields = querier.get_form_fields("1040-2024-v1")
            current_section = None
            for field in fields:
                if field["section"] != current_section:
                    current_section = field["section"]
                    print(f"\n  [{current_section}]")
                print(f"    {field['order']:2d}. {field['field_name']} ({field['field_id']})")
                print(f"        Type: {field['field_type']}")
        except Exception as e:
            print(f"  Error: {e}")
        
        # 4. Get validation rules
        print("\n4. Validation Rules:")
        print("-" * 30)
        try:
            rules = querier.get_validation_rules()
            for rule in rules:
                print(f"  - Expression: {rule['expression']}")
                print(f"    Error: {rule['error_message']}")
                print(f"    Severity: {rule['severity']}")
        except Exception as e:
            print(f"  Error: {e}")
        
        # 5. Get calculations
        print("\n5. Field Calculations:")
        print("-" * 30)
        try:
            calcs = querier.get_calculations()
            for calc in calcs:
                print(f"  - Expression: {calc['expression']}")
                print(f"    Type: {calc['calc_type']}")
        except Exception as e:
            print(f"  Error: {e}")
        
        # 6. TODO: Field dependencies
        print("\n6. Field Dependencies:")
        print("-" * 30)
        print("  TODO: Implement get_field_dependencies() method")
        print("  This will show bidirectional field relationships")


if __name__ == "__main__":
    main()