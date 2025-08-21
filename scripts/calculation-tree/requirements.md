╔═══════════════════════════════════════════════════════════════════════════╗
║                     TAX CALCULATION DEPENDENCY TREE                       ║
║                  (Field Name → Calculation Function)                      ║
╚═══════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────┐
│ Form 1040 Field Dependency Hierarchy ( Year View )                      │
└─────────────────────────────────────────────────────────────────────────┘


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

┌─────────────────────────────────────────────────────────────────────────┐
│ Form 1040 Field Dependency Hierarchy ( Taxpayer View )                  │
└─────────────────────────────────────────────────────────────────────────┘

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
      └── Tax Rate Lookup = (base_tax: $6,426, tax_rate: 22%, min: 47150, max:100525) 
          └── get_tax_bracket() 
              │
              └── Single Filer Tax Brackets
                  └── $47,150 - $100,525 → 22% = $6,237 ← APPLIED



