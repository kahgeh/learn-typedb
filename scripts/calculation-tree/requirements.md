╔═══════════════════════════════════════════════════════════════════════════╗
║                     TAX CALCULATION DEPENDENCY TREE                       ║
║                  (Field Name → Calculation Function)                      ║
╚═══════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────┐
│ Form 1040 Field Dependency Hierarchy                                    │
└─────────────────────────────────────────────────────────────────────────┘

Federal Income Tax [Line 16]
└── calculate_federal_tax()
    │
    ├── Taxable Income [Line 15]
    │   └── calculate_taxable_income()
    │       │
    │       ├── Adjusted Gross Income [Line 11]
    │       │   └── calculate_agi()
    │       │       │
    │       │       └── Total Income [Line 9]
    │       │           └── calculate_total_income()
    │       │               │
    │       │               ├── W-2 Wages
    │       │               │   └── (income_source.amount)
    │       │               │
    │       │               └── 1099 Income
    │       │                   └── (income_source.amount)
    │       │
    │       └── Standard Deduction [Line 12]
    │           └── get_standard_deduction()
    │               │
    │               ├── Tax Year (2024)
    │               │   └── (tax_year.year)
    │               │
    │               └── Filing Status (single/married)
    │                   └── (filing_status.filing_status_type)
    │
    └── Tax Rate Lookup
        └── get_tax_rate()
            │
            ├── INPUT: Taxable Income ($75,400)
            ├── INPUT: Tax Year (2024)
            ├── INPUT: Filing Status (single)
            │
            └── LOOKUP: tax_bracket_rule
                │
                ├── Check: $0 - $11,600 → 10%
                │   └── $75,400 > $11,600
                │
                ├── Check: $11,600 - $47,150 → 12%
                │   └── $75,400 > $47,150
                │
                ├── Check: $47,150 - $100,525 → 22%
                │   └── $75,400 in range
                │
                └── Check: $100,525+ → 24%
                    └── $75,400 < $100,525

┌─────────────────────────────────────────────────────────────────────────┐
│ Function Composition Flow                                               │
└─────────────────────────────────────────────────────────────────────────┘

calculate_complete_return()
    │
    ├─► calculate_total_income($taxpayer)
    │     └─► SUM(income_source.amount) for all income types
    │
    ├─► calculate_agi($taxpayer)
    │     └─► CALLS: calculate_total_income($taxpayer)
    │
    ├─► get_standard_deduction($year, $status)
    │     └─► LOOKUP: standard_deduction_rule → deduction_amount
    │
    ├─► calculate_taxable_income($taxpayer, $year, $status)
    │     ├─► CALLS: calculate_agi($taxpayer)
    │     └─► CALLS: get_standard_deduction($year, $status)
    │     └─► RETURNS: AGI - Standard Deduction
    │
    └─► calculate_federal_tax($taxpayer, $year, $status)
          ├─► CALLS: calculate_taxable_income($taxpayer, $year, $status)
          ├─► CALLS: get_tax_rate($taxable, $year, $status)
          │     └─► MATCH: tax_bracket_rule WHERE:
          │           • bracket.min <= $taxable <= bracket.max
          │           • applicable_year = $year
          │           • applicable_status = $status
          │           • RETURNS: bracket.rate (first match)
          └─► RETURNS: Taxable Income × Tax Rate

┌─────────────────────────────────────────────────────────────────────────┐
│ Tax Bracket Lookup Logic (get_tax_rate function)                         │
└─────────────────────────────────────────────────────────────────────────┘

get_tax_rate($income: 75400, $year: 2024, $status: single)
    │
    └── QUERY: tax_bracket_rule
        │
        ├── MATCH CONDITIONS:
        │   • (applicable_year: $year, applicable_status: $status, bracket: $b)
        │   • $b has bracket_min $min, bracket_max $max, rate $rate
        │   • $income >= $min AND $income <= $max
        │
        └── EVALUATION for $75,400:
            ├── Bracket 1: $0-$11,600 (10%)      → NO (exceeds max)
            ├── Bracket 2: $11,600-$47,150 (12%) → NO (exceeds max)
            ├── Bracket 3: $47,150-$100,525 (22%) → YES ✓
            └── Bracket 4: $100,525+ (24%)        → NO (below min)
            
            RETURNS: 0.22 (22% rate)

┌─────────────────────────────────────────────────────────────────────────┐
│ Calculation Example (John Doe - Actual Values)                          │
└─────────────────────────────────────────────────────────────────────────┘

Federal Income Tax ← calculate_federal_tax()
    │
    ├── Taxable Income: $75,400 ← calculate_taxable_income()
    │   │
    │   ├── AGI: $90,000 ← calculate_agi()
    │   │   └── Total Income: $90,000 ← calculate_total_income()
    │   │       ├── W-2: $75,000
    │   │       └── 1099: $15,000
    │   │
    │   └── Standard Deduction: $14,600 ← get_standard_deduction()
    │
    └── Tax Rate: 22% ← get_tax_rate($75,400, 2024, single)
        │
        └── Bracket Selection Process:
            ├── Query: tax_bracket_rule for year=2024, status=single
            ├── Find: bracket where $75,400 ∈ [min, max]
            └── Result: $47,150-$100,525 bracket → 22% rate
    
    FINAL: $75,400 × 0.22 = $16,588

