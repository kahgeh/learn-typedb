# TypeDB for Tax Compliance Systems: A Learning Guide

## Why TypeDB for Tax Systems?

### The Challenge
Building tax systems with traditional databases requires:
- Complex joins across dozens of tables
- Manual consistency checking between forms
- Hard-coded validation logic in application layer
- Difficulty representing temporal rule changes
- No semantic understanding of tax concepts

### TypeDB's Solution
TypeDB provides a knowledge graph approach that naturally models:
1. **Semantic Relationships**: "taxpayer files return containing forms with fields"
2. **Rule Inference**: Automatic calculation propagation and validation
3. **Type Safety**: Strong typing prevents invalid data structures
4. **Temporal Modeling**: Rules and forms versioned by tax year
5. **Dependency Tracking**: Automatic relationship management

## Core Concepts Applied to Tax Domain

### 1. Entity Modeling
```typeql
# Traditional DB: Multiple tables with foreign keys
# TypeDB: Natural entity definitions

tax-year sub entity,
    owns year @key,
    owns jurisdiction,
    plays form-definition:applicable-year;

form-type sub entity,
    owns form-code @key,
    owns form-name,
    plays form-dependency:dependent-form;
```

**Benefit**: Each tax concept is a first-class entity with semantic meaning.

### 2. Relationships as First-Class Citizens
```typeql
field-dependency sub relation,
    relates source-field,
    relates target-field,
    owns dependency-type,
    owns condition-expression;
```

**Benefit**: Dependencies aren't just foreign keys - they carry metadata about HOW fields relate.

### 3. Rule-Based Inference
```typeql
rule gross-income-calculation:
    when {
        $filing isa filing;
        $wages (parent-filing: $filing, value-field: $wage-field) isa field-value,
            has value-number $wage-amount;
        $wage-field isa field-definition, has field-id "W2_WAGES";
        # ... other income sources
        ?gross-income = $wage-amount + $interest-amount;
    } then {
        (parent-filing: $filing, value-field: $gross-field) isa field-value,
            has value-number ?gross-income;
    };
```

**Benefit**: Calculations happen IN the database, ensuring consistency.

## Practical Use Cases

### 1. Form Generation
TypeDB can generate form UI dynamically:
```python
def generate_form_ui(form_code, tax_year):
    """Generate UI from TypeDB schema."""
    query = """
        match
        $form isa form-type, has form-code $code;
        (container: $def, contained-field: $field) isa field-containment,
            has field-order $order,
            has section-name $section;
        $field has field-type $type, has is-required $req;
        fetch $field, $type, $req, $order, $section;
    """
    # Results directly map to UI components
```

### 2. Validation Chains
Validations cascade through relationships:
```typeql
rule dependent-form-validation:
    when {
        # If Schedule C is filed...
        $filing contains Schedule C data;
        # But Form 1040 is missing...
        not { $filing contains Form 1040 data; };
    } then {
        # Create validation error
        validation-error(filing: $filing, 
                        message: "Schedule C requires Form 1040");
    };
```

### 3. Multi-Jurisdiction Support
```typeql
# Federal rules
$fed-rule isa calculation-rule,
    has jurisdiction "US-FEDERAL",
    has expression "agi - standard_deduction";

# State rules reference federal
$state-rule isa calculation-rule,
    has jurisdiction "CA-STATE",
    has expression "federal_agi * 0.8";
```

### 4. Temporal Rule Changes
```typeql
# 2023 Standard Deduction
$rule-2023 isa deduction-rule,
    has tax-year 2023,
    has amount 13850;

# 2024 Standard Deduction  
$rule-2024 isa deduction-rule,
    has tax-year 2024,
    has amount 14600;
```

## Key Advantages for Your Use Case

### 1. LLM Integration
- **Semantic Schema**: LLMs can understand TypeDB's natural language-like queries
- **Rule Generation**: LLMs can generate TypeQL rules from tax documentation
- **Validation Messages**: Error messages are semantic, not cryptic codes

### 2. Authority Specification Parsing
- **Direct Mapping**: Tax authority specs map naturally to TypeDB entities
- **Relationship Preservation**: Form dependencies explicitly modeled
- **Version Control**: Each tax year's rules coexist without conflicts

### 3. Data Integrity
- **Type Safety**: Can't put string in number field
- **Relationship Constraints**: Can't file Schedule C without Form 1040
- **Calculation Consistency**: Rules ensure derived values stay synchronized

### 4. Query Power
```typeql
# Find all fields affecting refund amount
match
$refund isa field-definition, has field-id "REFUND_DUE";
$path (source-field: $source, target-field: $refund) isa field-dependency;
fetch $source;

# Returns entire dependency tree!
```

## Implementation Patterns

### Pattern 1: Field Validation
```typeql
# Define validation as relation
validation-rule sub relation,
    relates validated-field,
    owns rule-expression,
    owns error-message;

# Query validations for a form
match
$field isa field-definition;
$rule (validated-field: $field) isa validation-rule,
    has rule-expression $expr;
fetch $field, $expr;
```

### Pattern 2: Calculation Chains
```typeql
# Define calculation relationships
calculation sub relation,
    relates input-field @card(1..),
    relates output-field,
    owns calculation-expression;

# Trace calculation dependencies
match
$output has field-id "TAX_LIABILITY";
$calc (output-field: $output, input-field: $input) isa calculation;
fetch $input recursive;
```

### Pattern 3: Form Hierarchies
```typeql
# Forms contain sections contain fields
field-containment sub relation,
    relates container,
    relates contained-field,
    owns field-order,
    owns section-name;
```

## Performance Considerations

1. **Inference Caching**: TypeDB caches inferred results
2. **Index on Keys**: Use @key for frequently queried attributes
3. **Batch Operations**: Load data in transactions
4. **Query Optimization**: Use specific patterns first, then generalize

## Next Steps for Learning

1. **Run the Setup**: Execute `python scripts/setup_database.py`
2. **Explore Queries**: Try the query examples
3. **Modify Rules**: Add new calculation rules
4. **Build UI Generator**: Create form UI from TypeDB schema
5. **Test Validations**: Insert invalid data and see rules catch it

## Advanced Topics to Explore

1. **Reasoning Chains**: How TypeDB chains multiple rules
2. **Negation**: Validating absence of data
3. **Aggregations**: Sum, count, average in TypeQL
4. **Streaming**: Real-time updates as data changes
5. **Explanations**: Why a rule fired or validation failed

## Comparison with Traditional Approach

| Aspect | Traditional DB | TypeDB |
|--------|----------------|---------|
| Schema | Tables + Constraints | Semantic Types + Rules |
| Relationships | Foreign Keys | First-class Relations |
| Validation | Application Code | Database Rules |
| Calculations | Stored Procedures | Inference Rules |
| Versioning | Complex Schemas | Natural Temporal Modeling |
| Query Language | SQL Joins | Pattern Matching |

## Resources

- [TypeDB Documentation](https://typedb.com/docs)
- [TypeQL Language Guide](https://typedb.com/docs/typeql/2.x/overview)
- [Rule Inference](https://typedb.com/blog/inference-in-typedb)
- Our Schema: `schemas/tax-schema.tql`
- Sample Data: `data/sample-tax-data.tql`