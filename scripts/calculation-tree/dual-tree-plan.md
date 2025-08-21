# Plan: Two Types of Dependency Trees

## Overview

We need two distinct views of the tax calculation dependency tree:
1. **Generic Year View**: Shows all possible paths and options for a given tax year
2. **Taxpayer-Specific View**: Shows only the actual path taken for a specific taxpayer

## 1. Generic Year Dependency Tree

### Purpose
Show the complete structure of tax calculations for a given year, displaying ALL possible branches and options.

### Key Features
- Shows ALL tax brackets for each filing status
- Shows ALL deduction options (standard vs itemized)
- Shows ALL income types possible
- Shows conditional branches (e.g., "if married" vs "if single")
- Highlights the decision points in the calculation

### Example Output Structure
```
Federal Income Tax [line-16]
└── calculate_federal_tax()
    │
    ├── Taxable Income [line-15]
    │   └── calculate_taxable_income()
    │       │
    │       ├── Adjusted Gross Income [line-11]
    │       │   └── calculate_agi()
    │       │       │
    │       │       └── Total Income [line-9]
    │       │           └── calculate_total_income()
    │       │               │
    │       │               ├── [POSSIBLE] W-2 Wages
    │       │               ├── [POSSIBLE] 1099 Income
    │       │               ├── [POSSIBLE] Capital Gains
    │       │               └── [POSSIBLE] Business Income
    │       │
    │       └── Deductions [line-12]
    │           └── calculate_deductions()
    │               │
    │               ├── [OPTION A] Standard Deduction
    │               │   ├── Single: $14,600
    │               │   ├── Married Filing Jointly: $29,200
    │               │   └── Head of Household: $21,900
    │               │
    │               └── [OPTION B] Itemized Deductions
    │                   ├── State/Local Taxes (max $10,000)
    │                   ├── Mortgage Interest
    │                   └── Charitable Contributions
    │
    └── Tax Rate Lookup
        └── get_tax_rate()
            │
            ├── [FOR SINGLE FILERS]
            │   ├── $0 - $11,600 → 10%
            │   ├── $11,600 - $47,150 → 12%
            │   ├── $47,150 - $100,525 → 22%
            │   └── $100,525+ → 24%
            │
            ├── [FOR MARRIED FILING JOINTLY]
            │   ├── $0 - $23,200 → 10%
            │   ├── $23,200 - $94,300 → 12%
            │   ├── $94,300 - $201,050 → 22%
            │   └── $201,050+ → 24%
            │
            └── [FOR HEAD OF HOUSEHOLD]
                ├── $0 - $16,550 → 10%
                ├── $16,550 - $63,100 → 12%
                ├── $63,100 - $100,500 → 22%
                └── $100,500+ → 24%
```

## 2. Taxpayer-Specific Dependency Tree

### Purpose
Show the actual calculation path taken for a specific taxpayer, with real values and only relevant branches.

### Key Features
- Shows ONLY the income types the taxpayer actually has
- Shows ONLY the deduction type they used (standard OR itemized)
- Shows ONLY their filing status's tax brackets
- Highlights which bracket was actually used
- Shows actual calculated values at each step

### Example Output Structure (for John Doe, Single, $90k income)
```
Federal Income Tax [line-16] = $16,588
└── calculate_federal_tax()
    │
    ├── Taxable Income [line-15] = $75,400
    │   └── calculate_taxable_income()
    │       │
    │       ├── Adjusted Gross Income [line-11] = $90,000
    │       │   └── calculate_agi()
    │       │       │
    │       │       └── Total Income [line-9] = $90,000
    │       │           └── calculate_total_income()
    │       │               │
    │       │               ├── W-2 Wages = $75,000
    │       │               └── 1099 Income = $15,000
    │       │
    │       └── Standard Deduction [line-12] = $14,600
    │           └── get_standard_deduction()
    │               └── Single Filer → $14,600
    │
    └── Tax Rate Lookup
        └── get_tax_rate()
            │
            └── Single Filer Tax Brackets
                ├── $0 - $11,600 → 10% = $1,160
                ├── $11,600 - $47,150 → 12% = $4,266
                ├── $47,150 - $100,525 → 22% = $6,237 ← APPLIED
                │   └── ($75,400 - $47,150) × 22%
                └── $100,525+ → 24% 
```

## Implementation Plan

### Phase 1: Schema Extensions (if needed)
```tql
define

# Add conditional logic metadata (optional - only if we want to store branch conditions)
attribute condition_type, value string; # "filing_status", "income_threshold", etc.
attribute condition_description, value string;

# Extend function_metadata (if tracking conditional logic)
entity function_metadata,
    owns calculation_function @key,
    owns function_type,
    owns has_conditional_logic,
    plays conditional_branch:function;

# Conditional branches (optional)
entity conditional_branch_spec,
    owns condition_type,
    owns condition_description,
    plays conditional_branch:condition;

relation conditional_branch,
    relates function,
    relates condition;
```

Note: The existing schema in `semantic_tax_system.py` may already be sufficient. The different views are achieved through query logic, not schema changes.

### Phase 2: Query Functions

#### A. Generic Year Tree Builder
```python
def build_generic_year_tree(tx, year, root_field_id):
    """
    Build tree showing all possible paths for a given year.
    Query parameters: year only (no taxpayer specified)
    """
    
    # Get all filing statuses for the year
    filing_statuses = get_all_filing_statuses(tx, year)
    
    # Get all income types available in the system
    income_types = get_all_income_types(tx)
    
    # Get all deduction options for the year (standard amounts for all statuses)
    deduction_options = get_all_deduction_options(tx, year)
    
    # Get all tax brackets for all filing statuses
    tax_brackets = get_all_tax_brackets(tx, year)
    
    # Build tree with all branches marked as [POSSIBLE] or [OPTION]
    # The query logic determines what to show, not a stored attribute
    return build_tree_with_all_branches(...)
```

#### B. Taxpayer-Specific Tree Builder
```python
def build_taxpayer_tree(tx, taxpayer_ssn, year, root_field_id):
    """
    Build tree showing actual calculation path for specific taxpayer.
    Query parameters: taxpayer_ssn AND year
    """
    
    # Query taxpayer's actual data for the year
    taxpayer_data = get_taxpayer_data(tx, taxpayer_ssn, year)
    
    # Query only the income sources this taxpayer actually has
    actual_income = get_taxpayer_income_sources(tx, taxpayer_ssn)
    
    # Query the actual deduction type used (standard or itemized)
    actual_deduction = get_taxpayer_deduction(tx, taxpayer_ssn, year)
    
    # Query only the tax bracket that applies to this taxpayer's income
    applicable_bracket = get_applicable_bracket(tx, taxpayer_data)
    
    # Build tree with actual values - the query parameters determine the view
    return build_tree_with_actual_values(...)
```

### Phase 3: Enhanced Visualization

#### A. Add Visual Indicators
```python
class TreeNodeType(Enum):
    ACTUAL = "→"        # Actual value/path taken
    POSSIBLE = "◇"      # Possible but not used
    OPTION = "○"        # Alternative option
    SELECTED = "●"      # Selected option
    NOT_APPLICABLE = "×" # Not applicable for this taxpayer
```

#### B. Value Display
```python
def format_node_with_value(node_name, value=None, node_type=TreeNodeType.ACTUAL):
    if value is not None:
        return f"{node_type.value} {node_name} = ${value:,.2f}"
    else:
        return f"{node_type.value} {node_name}"
```

### Phase 4: CLI Interface

```python
def main():
    parser = argparse.ArgumentParser()
    # Remove 'mode' - the presence of SSN determines the view type
    parser.add_argument('--year', type=int, 
                       default=2024,
                       help='Tax year')
    parser.add_argument('--ssn', type=str,
                       help='Taxpayer SSN (if provided, shows taxpayer-specific view)')
    parser.add_argument('--show-calculations', action='store_true',
                       help='Show calculation details')
    parser.add_argument('--compare', action='store_true',
                       help='Show comparison view (requires SSN)')
    
    args = parser.parse_args()
    
    # The view type is determined by which parameters are provided
    if args.compare:
        if not args.ssn:
            print("Error: SSN required for comparison view")
            return
        tree = build_comparison_view(tx, args.ssn, args.year, root_field_id)
    elif args.ssn:
        # SSN provided = taxpayer-specific view
        tree = build_taxpayer_tree(tx, args.ssn, args.year, root_field_id)
    else:
        # No SSN = generic year view
        tree = build_generic_year_tree(tx, args.year, root_field_id)
```

### Phase 5: Comparison View

Create a side-by-side comparison showing:
1. What rules/brackets were available (generic)
2. What was actually used (taxpayer-specific)

```python
def build_comparison_view(tx, taxpayer_ssn, year):
    """Show generic options alongside actual taxpayer path"""
    
    generic_tree = build_generic_year_tree(tx, year)
    taxpayer_tree = build_taxpayer_tree(tx, taxpayer_ssn, year)
    
    # Merge trees, highlighting differences
    return merge_and_highlight_trees(generic_tree, taxpayer_tree)
```

## Benefits of This Approach

### For Generic Year View:
- **Educational**: Shows all tax rules and options for the year
- **Planning**: Helps understand different scenarios
- **Validation**: Ensures all rules are properly loaded
- **Documentation**: Self-documenting tax structure

### For Taxpayer-Specific View:
- **Clarity**: Shows exact calculation path
- **Debugging**: Easy to trace specific calculations
- **Audit Trail**: Clear record of how tax was calculated
- **Optimization**: Can identify better options

## Next Steps

1. **Extend Schema**: Add conditional logic metadata
2. **Create Helper Functions**: Build queries for each view type
3. **Implement Tree Builders**: Separate functions for each view
4. **Add CLI Interface**: Command-line arguments for mode selection
5. **Test with Examples**: Verify both views work correctly
6. **Add Comparison Mode**: Side-by-side view of generic vs specific

## Example Usage

```bash
# Generic year view - shows all possibilities (no SSN provided)
uv run python query_dependency_tree.py --year 2024

# Taxpayer-specific view - shows actual calculation (SSN provided)
uv run python query_dependency_tree.py --year 2024 --ssn "123-45-6789"

# Comparison view (requires SSN)
uv run python query_dependency_tree.py --compare --year 2024 --ssn "123-45-6789"

# With calculation details
uv run python query_dependency_tree.py --year 2024 --ssn "123-45-6789" --show-calculations
```

The key insight: **The view type is implicit based on the query parameters provided**, not stored in the database.

This design provides flexibility to view the tax calculation structure from different perspectives, making it useful for both understanding the tax system and debugging specific calculations.
