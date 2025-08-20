# TypeDB Tax System Learning Exercises

A comprehensive learning path for mastering TypeDB by progressively building a complete tax system, from basic schema definitions to complex real-world tax calculations.

## Learning Path Overview

The exercises are organized in four levels with increasing complexity:

### 🔵 Foundation (Exercises 00a-00g)
**Focus**: Building the tax system schema progressively
- Defining tax system attributes (IDs, dates, amounts)
- Creating core entities (taxpayer, filing, forms)
- Modeling tax relationships (filing-relation, form-applicable)
- Advanced schema with fields and validations
- Inserting tax data (taxpayers, filings, forms)
- Deleting sensitive data and drafts safely
- Updating tax records (status changes, amendments)

### 🟢 Beginner (Exercises 01-03)
**Focus**: Basic TypeQL syntax and entity queries
- Simple entity matching
- Attribute filtering
- Basic select statements

### 🟡 Intermediate (Exercises 04-06)  
**Focus**: Relations and multi-hop queries
- Understanding relation patterns
- Working with role players
- Joining entities through relations
- Relation attributes

### 🔴 Advanced (Exercises 07-09)
**Focus**: Complex tax workflows matching real-world scenarios
- Multi-relation traversal
- Calculation dependency chains
- Complete tax filing workflows
- Data validation and completeness

## Exercise Files

| Exercise | Title | Difficulty | Key Concepts |
|----------|-------|------------|--------------|
| 00a | Define Tax Attributes | 🔵 Foundation | Tax system attributes, value types |
| 00b | Define Core Tax Entities | 🔵 Foundation | Taxpayer, filing, forms with @key |
| 00c | Define Tax Relations | 🔵 Foundation | Filing relations, tax periods |
| 00d | Advanced Tax Schema | 🔵 Foundation | Form fields, validations, calculations |
| 00e | Insert Tax Data | 🔵 Foundation | Creating taxpayers and filings |
| 00f | Delete Tax Data | 🔵 Foundation | Privacy, draft cleanup, cascading |
| 00g | Update Tax Records | 🔵 Foundation | Status updates, amendments |
| 01 | List All Taxpayers | 🟢 Beginner | Entity matching, basic select |
| 02 | Find Required Fields | 🟢 Beginner | Attribute filtering, boolean values |
| 02a | Tax Data Migration | 🟢 Beginner | Migrating legacy tax data |
| 03 | Forms by Category | 🟢 Beginner | Grouping, multiple attributes |
| 04 | Reverse Field Dependencies | 🟡 Intermediate | Relation roles, dependency graphs |
| 05 | Form Fields by Section | 🟡 Intermediate | Relation attributes, ordering |
| 06 | Validation Rules with Fields | 🟡 Intermediate | Multiple relations, validation logic |
| 07 | Tax Year Form Comparison | 🔴 Advanced | Temporal queries, comparisons |
| 08 | Calculation Dependency Chain | 🔴 Advanced | Recursive traversal, calculation trees |
| 09 | Complete Tax Workflow | 🔴 Advanced | Full workflow, real-world complexity |

## How to Run Exercises

Each exercise is a `.tqls` file that can be run directly with TypeDB console:

```bash
# Run an exercise
typedb console --address=localhost:1729 --username=admin --tls-disabled --password password --script=exercises/01-list-all-taxpayers.tqls

# Or navigate to exercises directory and run
cd exercises/
typedb console --address=localhost:1729 --username=admin --tls-disabled --password password --script=01-list-all-taxpayers.tqls
```

## Exercise Structure

Each exercise file contains:
1. **Task description** - What you need to accomplish
2. **Learning goals** - TypeQL concepts you'll practice
3. **Context** - Domain knowledge about the tax system
4. **Expected output** - What a successful query should return
5. **TODO(human)** markers - Where you need to write code
6. **Hints** - Guidance without giving away the solution

## Solutions

Solutions are intentionally not provided. The learning comes from:
1. Reading the TypeDB documentation in `docs/typedb-docs-3.x/`
2. Examining similar patterns in the `queries/` directory
3. Experimenting with different approaches
4. Understanding error messages

## Progression Tips

1. **Start with Foundation exercises (00a-00d)** - Learn to define schemas before querying
2. **Complete exercises in order** - Each builds on previous concepts
3. **Read the context carefully** - Understanding the domain helps write better queries
4. **Start simple** - Get a basic query working, then refine
5. **Use the console interactively** - Test parts of your query incrementally
6. **Reference the documentation** - Located in `docs/typedb-docs-3.x/core-concepts/`
7. **For schema exercises** - Create a test database to practice without affecting the main tax-system database

## Domain Context: Tax System

All exercises use a single, comprehensive tax system domain that you build progressively:

### Foundation Level (00a-00g)
Start with core components:
- **Basic Entities**: taxpayer, tax-year, return-type, filing
- **Core Relations**: filing-relation, filing-period, form-applicable
- **Essential Attributes**: taxpayer-id, filing-status, year, form-code

### Intermediate Level (00d and beyond)
Add complexity:
- **Advanced Entities**: form-definition, field-definition, validation-rule
- **Complex Relations**: field-containment, field-dependency, calculation
- **Specialized Attributes**: calculation-expression, rule-expression, severity

### Complete System
The full schema mirrors real tax software:
- Forms contain fields organized in sections
- Fields have dependencies and calculations
- Validations ensure compliance
- Temporal versioning tracks changes
- Classifications categorize taxpayers

By building the schema progressively, you understand both HOW to model in TypeDB and WHY each design decision matters for real-world tax systems.

## Getting Stuck?

If you're stuck on an exercise:
1. Check the query files in `queries/` for similar patterns
2. Review the schema in `schemas/tax-schema-v3.tql`
3. Use `match $x isa [type]; select $x;` to explore what data exists
4. Break complex queries into smaller parts
5. Test each part independently

## Next Steps

After completing these exercises, you'll be ready to:
- Write complex TypeDB queries for production systems
- Model your own domains using TypeDB's semantic approach
- Optimize queries for performance
- Build applications using TypeDB drivers

Remember: The goal is not just to get the right answer, but to understand the patterns and thinking behind semantic queries.