# TypeQL Query Examples for Tax System

This folder contains TypeQL query scripts that can be run directly using TypeDB console.

## Running Queries

Each `.tqls` file is a complete TypeDB console script that can be executed directly:

```bash
typedb console --address=localhost:1729 --username=admin --tls-disabled --password password --script=queries/01-count-entities.tqls
```

## Query Files

| Query File | Description |
|------------|-------------|
| 01-count-entities.tqls | List all tax years in the system |
| 02-list-form-types.tqls | Show all available tax form types (returns) |
| 03-form-fields.tqls | Get fields for Form 1040 (2024 version) |
| 04-field-dependencies.tqls | Find which fields depend on W2_WAGES |
| 05-validation-rules.tqls | List all validation rules |
| 06-calculations.tqls | Show calculation relationships between fields |
| 07-taxpayer-info.tqls | Get taxpayer information and classifications |
| 08-form-dependencies.tqls | Show dependencies between different forms |
| 09-forms-by-year.tqls | Find forms applicable to tax year 2024 |
| 10-calculation-chain.tqls | Trace the calculation chain for gross income |

## Query Script Format

Each query file follows this format:
```typeql
transaction read tax-system
    match [your pattern];
    select [variables];
    
    close
```

## Learning Exercises

### Exercise 1: Modify Field Dependencies
Create a new query to find fields that depend on GROSS_INCOME (reverse of query 04).

### Exercise 2: Required Fields Query
Create a query to find all required fields:
```typeql
transaction read tax-system
    match 
        $field isa field-definition, has is-required true;
    select $field;
    
    close
```

### Exercise 3: Tax Year Comparison
Write a query to compare forms available in 2023 vs 2024.

## TypeDB 3.0 Notes

- Queries use `select` instead of older `get` or `fetch` syntax
- Scripts must include `transaction` and `close` commands
- The `--script` flag runs the entire file as a console script