# Tax Calculation Audit Trail System

A complete solution for auditable tax calculations in TypeDB with visualization capabilities.

## 🎯 Overview

This system demonstrates how to create fully auditable tax calculations where:
- Every calculation step is recorded as data
- Dependencies between calculations form a queryable graph
- The calculation tree can be visualized and exported
- Auditors can trace any value back to its source

## 📁 Files

- `setup_audit_trail.py` - Sets up database, schema, and sample data
- `visualize_calculation_tree.py` - Queries and visualizes the calculation tree
- `../exercises/00d6-audit-calculation-walkthrough.tqls` - Schema definition walkthrough
- `../exercises/00d7-query-audit-walkthrough.tqls` - Query patterns walkthrough

## 🚀 Quick Start

### Step 1: Start TypeDB Server
```bash
typedb server
```

### Step 2: Run Setup Script
```bash
python scripts/setup_audit_trail.py
```

This will:
1. Create the `tax-system` database
2. Define the audit trail schema
3. Insert sample taxpayer data (John Doe, SSN: 123-45-6789)
4. Create a complete calculation tree with 7 steps
5. Verify the setup

Expected output:
```
🚀 Setting up TypeDB Audit Trail System...
📦 Creating tax-system database...
   ✓ Database created
📋 Defining audit trail schema...
   ✓ Schema defined
📝 Inserting sample taxpayer data...
   ✓ Sample data inserted
🧮 Creating calculation audit trail...
   ✓ Calculation audit trail created
✅ Verifying setup...
   ✓ Created 7 calculation steps
   ✓ Created 5 lineage relationships

📊 Calculation Tree Structure:
   federal-income-tax: $14,663.00
   └── taxable-income: $66,650.00
       ├── adjusted-gross-income: $80,500.00
       │   ├── income-component: $65,000.00
       │   ├── income-component: $12,000.00
       │   └── income-component: $3,500.00
       └── standard-deduction: $13,850.00

✨ Setup complete! You can now run visualize_calculation_tree.py
```

### Step 3: Visualize the Calculation Tree
```bash
python scripts/visualize_calculation_tree.py
```

This will:
1. Query the calculation tree from TypeDB
2. Display it in the console
3. Export to `tax_calculation.dot` (Graphviz format)
4. Export to `tax_calculation.json` (for D3.js visualization)

### Step 4: Generate Visual Diagram (Optional)
If you have Graphviz installed:
```bash
dot -Tpng tax_calculation.dot -o tax_calculation.png
```

## 📊 Understanding the Calculation Tree

The sample data creates this calculation hierarchy:

```
Federal Income Tax ($14,663)
  ← calculated from
    Taxable Income ($66,650)
      ← calculated from
        AGI ($80,500)
          ← sum of
            W-2 Income ($65,000)
            1099 Income ($12,000)
            Other Income ($3,500)
        Standard Deduction ($13,850)
          ← lookup based on filing status
```

## 🔍 Key Concepts

### Calculation Steps
Each calculation is stored as a `calculation-step` entity with:
- Unique ID for traceability
- Type (e.g., "federal-income-tax", "adjusted-gross-income")
- Timestamp when calculated
- Formula used
- Output value
- Human-readable notes

### Lineage Relations
The `calculation-lineage` relation creates parent-child links:
- Parent step (the calculation that depends on others)
- Child step (the input calculation)
- Step order (for ordering multiple dependencies)

### Context Relations
The `calculation-context` relation links calculations to:
- The taxpayer
- The tax filing year
- Related forms (if applicable)

## 🛠️ Customization

### Adding More Taxpayers
Edit `setup_audit_trail.py` to add more taxpayers:
```python
insert_taxpayer = """
    insert
    $taxpayer isa taxpayer,
        has ssn "987-65-4321",
        has name "Jane Smith",
        has income 85000.0,
        has income 5000.0;
"""
```

### Modifying Calculations
The calculation logic in the setup script can be modified to:
- Add more calculation types
- Include deductions and credits
- Handle different filing statuses
- Add state tax calculations

### Export Formats
The visualization script supports:
- Console tree (ASCII art)
- Graphviz DOT (for diagrams)
- JSON (for web visualization)

You can extend it to support:
- CSV for spreadsheets
- HTML reports
- Interactive web dashboards

## 📝 Query Examples

### Get All Calculations for a Taxpayer
```typeql
match
    $taxpayer isa taxpayer, has ssn "123-45-6789";
    $filing isa filing, has year 2024;
    (step: $step, taxpayer: $taxpayer, filing: $filing) isa calculation-context;
    $step has calculation-type $type,
          has output-value $value;
select $type, $value;
```

### Find Impact of Changing Income
```typeql
match
    $income-step isa calculation-step, 
        has calculation-type "income-component",
        has output-value 65000.0;
    (parent-step: $dependent, child-step: $income-step) isa calculation-lineage;
    $dependent has calculation-type $type;
select $type;
```

### Verify Calculation Consistency
```typeql
match
    $agi isa calculation-step, 
        has calculation-type "adjusted-gross-income",
        has output-value $recorded-agi;
    (parent-step: $agi, child-step: $income) isa calculation-lineage;
    $income has output-value $value;
reduce $calculated-agi = sum($value);
# Compare $recorded-agi with $calculated-agi
```

## 🎓 Learning Exercises

1. **Extend the Schema**: Add calculation steps for tax credits
2. **Add Validation**: Create queries that verify calculation correctness
3. **Impact Analysis**: Write queries showing what changes if income increases
4. **Time Travel**: Add temporal queries to compare calculations across years
5. **Optimization**: Find the most expensive calculations in the tree

## 🐛 Troubleshooting

### Connection Issues
Ensure TypeDB is running and accessible:
```bash
typedb server status
```

### Missing Dependencies
Install required Python packages:
```bash
pip install typedb-driver
pip install graphviz  # Optional, for visualization
```

### Query Errors
Check TypeDB 3.0 syntax in queries:
- Use `has` for attributes (not `owns` in queries)
- Use proper relation syntax: `(role: player)`
- Use `select` not `fetch` for read queries

## 📚 Further Reading

- [TypeDB 3.0 Documentation](../docs/typedb-docs-3.x/)
- [Exercise 00d6](../exercises/00d6-audit-calculation-walkthrough.tqls) - Schema walkthrough
- [Exercise 00d7](../exercises/00d7-query-audit-walkthrough.tqls) - Query patterns
- [TypeQL Functions](../docs/typedb-docs-3.x/reference/modules/ROOT/pages/typeql/functions/)