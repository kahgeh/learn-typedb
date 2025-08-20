#!/usr/bin/env python3
"""
Visualize Tax Calculation Audit Trails from TypeDB

This script demonstrates how to:
1. Query calculation lineage from TypeDB
2. Build a hierarchical tree structure
3. Generate visualizations (console tree, Graphviz, JSON)

Requirements:
- typedb-driver
- graphviz (optional, for DOT file generation)
"""

import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from typedb.driver import TypeDB, TransactionType, Credentials, DriverOptions

@dataclass
class CalculationNode:
    """Represents a calculation step in the audit trail"""
    step_id: str
    calc_type: str
    value: float
    formula: Optional[str]
    note: Optional[str]
    children: List['CalculationNode']
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.step_id,
            'type': self.calc_type,
            'value': self.value,
            'formula': self.formula,
            'note': self.note,
            'children': [child.to_dict() for child in self.children]
        }
    
    def to_console_tree(self, prefix: str = "", is_last: bool = True) -> str:
        """Generate ASCII tree representation"""
        connector = "└── " if is_last else "├── "
        result = prefix + connector + f"{self.calc_type}: ${self.value:,.2f}"
        if self.formula:
            result += f" [{self.formula}]"
        result += "\n"
        
        # Add children
        child_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(self.children):
            is_last_child = (i == len(self.children) - 1)
            result += child.to_console_tree(child_prefix, is_last_child)
        
        return result
    
    def to_graphviz(self) -> Tuple[List[str], List[str]]:
        """Generate Graphviz DOT format nodes and edges"""
        nodes = []
        edges = []
        
        # Current node
        label = f"{self.calc_type}\\n${self.value:,.2f}"
        if self.formula:
            label += f"\\n{self.formula}"
        nodes.append(f'    "{self.step_id}" [label="{label}"];')
        
        # Process children
        for child in self.children:
            edges.append(f'    "{self.step_id}" -> "{child.step_id}";')
            child_nodes, child_edges = child.to_graphviz()
            nodes.extend(child_nodes)
            edges.extend(child_edges)
        
        return nodes, edges


class TaxCalculationAuditor:
    """Query and visualize tax calculation audit trails"""
    
    def __init__(self, address: str = "localhost:1729", 
                 username: str = "admin", 
                 password: str = "password"):
        self.address = address
        self.credentials = Credentials(username, password)
        self.options = DriverOptions(is_tls_enabled=False)
    
    def get_calculation_tree(self, taxpayer_ssn: str, year: int) -> Optional[CalculationNode]:
        """
        Retrieve the complete calculation tree for a taxpayer's tax calculation
        """
        driver = TypeDB.driver(self.address, self.credentials, self.options)
        try:
            with driver.transaction("tax-system", TransactionType.READ) as tx:
                # Query for the root calculation step
                root_query = f"""
                    match
                        $taxpayer isa taxpayer, has ssn "{taxpayer_ssn}";
                        $filing isa filing, has year {year};
                        (step: $root, taxpayer: $taxpayer, filing: $filing) isa calculation_context;
                        $root isa calculation_step,
                            has calculation_type "federal-income-tax",
                            has calculation_id $root_id,
                            has output_value $value;
                    select $root_id, $value;
                """
                
                root_result = tx.query(root_query).resolve()
                root_row = next(root_result, None)
                if not root_row:
                    return None
                
                root_id = root_row.get('root_id').get_string()
                root_value = root_row.get('value').get_double()
                
                # Build the tree recursively
                return self._build_tree_recursive(tx, root_id, "federal-income-tax", root_value)
        finally:
            driver.close()
    
    def _build_tree_recursive(self, tx, step_id: str, calc_type: str, value: float) -> CalculationNode:
        """Recursively build the calculation tree"""
        # Query for children of this step
        children_query = f"""
            match
                $parent isa calculation_step, has calculation_id "{step_id}";
                (parent_step: $parent, child_step: $child) isa calculation_lineage;
                $child has calculation_id $child_id,
                      has calculation_type $child_type,
                      has output_value $child_value;
                select $child_id, $child_type, $child_value;
        """
        
        children = []
        for child_row in tx.query(children_query).resolve():
            child_node = self._build_tree_recursive(
                tx,
                child_row.get('child_id').get_string(),
                child_row.get('child_type').get_string(),
                child_row.get('child_value').get_double()
            )
            children.append(child_node)
        
        # Get additional details - query separately to avoid complex optional patterns
        formula = None
        note = None
        
        # Try to get formula
        formula_query = f"""
            match
                $step isa calculation_step, has calculation_id "{step_id}";
                $step has calculation_formula $formula;
            select $formula;
        """
        try:
            formula_result = tx.query(formula_query).resolve()
            formula_row = next(formula_result, None)
            if formula_row:
                formula = formula_row.get('formula').get_string()
        except:
            pass
        
        # Try to get note
        note_query = f"""
            match
                $step isa calculation_step, has calculation_id "{step_id}";
                $step has calculation_note $note;
            select $note;
        """
        try:
            note_result = tx.query(note_query).resolve()
            note_row = next(note_result, None)
            if note_row:
                note = note_row.get('note').get_string()
        except:
            pass
        
        return CalculationNode(
            step_id=step_id,
            calc_type=calc_type,
            value=value,
            formula=formula,
            note=note,
            children=children
        )
    
    def visualize_console(self, tree: CalculationNode):
        """Print tree to console"""
        print("\n" + "="*60)
        print("TAX CALCULATION AUDIT TRAIL")
        print("="*60)
        print(tree.to_console_tree("", True))
    
    def export_graphviz(self, tree: CalculationNode, filename: str = "tax_calculation.dot"):
        """Export tree as Graphviz DOT file"""
        nodes, edges = tree.to_graphviz()
        
        with open(filename, 'w') as f:
            f.write("digraph TaxCalculation {\n")
            f.write("    rankdir=TB;\n")
            f.write("    node [shape=box, style=rounded];\n")
            f.write("\n".join(nodes) + "\n")
            f.write("\n".join(edges) + "\n")
            f.write("}\n")
        
        print(f"Graphviz file saved to {filename}")
        print("Generate image with: dot -Tpng tax_calculation.dot -o tax_calculation.png")
    
    def export_json(self, tree: CalculationNode, filename: str = "tax_calculation.json"):
        """Export tree as JSON for web visualization (D3.js, etc.)"""
        with open(filename, 'w') as f:
            json.dump(tree.to_dict(), f, indent=2)
        print(f"JSON file saved to {filename}")


def main():
    """Example usage"""
    auditor = TaxCalculationAuditor()
    
    # Get calculation tree for a specific taxpayer
    tree = auditor.get_calculation_tree("123-45-6789", 2024)
    
    if tree:
        # Console visualization
        auditor.visualize_console(tree)
        
        # Export for external visualization
        auditor.export_graphviz(tree)
        auditor.export_json(tree)
        
        # Example output:
        # └── income-tax: $15,234.00 [taxable_income * bracket_rate(0.22)]
        #     ├── taxable-income: $69,245.00 [AGI - standard_deduction]
        #     │   ├── adjusted-gross-income: $83,095.00 [sum(all income sources)]
        #     │   │   ├── income-component: $65,000.00
        #     │   │   ├── income-component: $12,000.00
        #     │   │   └── income-component: $6,095.00
        #     │   └── standard-deduction: $13,850.00
        #     └── tax-bracket: 0.22
    else:
        print("No calculation found for specified taxpayer and year")


if __name__ == "__main__":
    main()