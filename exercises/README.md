# TypeDB Tax System Learning Exercises

A structured learning path for mastering TypeDB through tax system queries, progressing from simple entity queries to complex real-world tax calculations.

## Learning Path Overview

The exercises are organized in three levels with increasing complexity:

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
| 01 | List All Taxpayers | 🟢 Beginner | Entity matching, basic select |
| 02 | Find Required Fields | 🟢 Beginner | Attribute filtering, boolean values |
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

1. **Complete exercises in order** - Each builds on previous concepts
2. **Read the context carefully** - Understanding the domain helps write better queries
3. **Start simple** - Get a basic query working, then refine
4. **Use the console interactively** - Test parts of your query incrementally
5. **Reference the documentation** - Located in `docs/typedb-docs-3.x/core-concepts/`

## Domain Context

The tax system model includes:
- **Entities**: taxpayer, form-type, form-definition, field-definition, validation-rule
- **Relations**: filing, field-containment, field-dependency, calculation, field-validation
- **Attributes**: ssn, field-id, calculation-expression, severity, etc.

This mirrors real tax software where:
- Forms contain fields in sections
- Fields depend on other fields
- Calculations cascade through the system
- Validations ensure data integrity

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