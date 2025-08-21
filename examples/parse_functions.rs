use anyhow::Result;
use std::fs;
use typedb_examples::{extract_function_metadata, FunctionMetadata};

fn main() -> Result<()> {
    println!("TypeQL Function Metadata Extractor Example");
    println!("{}", "=".repeat(60));
    println!();
    
    // Example TypeDB functions
    let functions = vec![
        r#"fun calculate_federal_tax($taxpayer: taxpayer, $year: tax_year, $status: filing_status) -> double:
            match
                let $taxable = calculate_taxable_income($taxpayer, $year, $status);
                let $min, $max, $rate, $base = get_tax_bracket($taxable, $year, $status);
                let $tax = $base + (($taxable - $min) * $rate);
            return first $tax;"#,
        
        r#"fun calculate_total_income($taxpayer: taxpayer) -> double:
            match
                $income (earner: $taxpayer, type: $type) isa income_source, has amount $amt;
            return sum($amt);"#,
        
        r#"fun get_tax_bracket($income: double, $year: tax_year, $status: filing_status) -> bracket_min, bracket_max, rate, base_tax:
            match
                (applicable_year: $year,
                 applicable_status: $status,
                 bracket: $bracket) isa tax_bracket_rule;
                $bracket has bracket_min $min, has bracket_max $max, has rate $rate, has base_tax $base;
                $income >= $min;
                $income <= $max;
            return first $min, $max, $rate, $base;"#,
        
        r#"fun mutual_friends($p1: person, $p2: person) -> { person }:
            match
                $f1 isa friendship, links (friend: $p1, friend: $pm);
                $f2 isa friendship, links (friend: $p2, friend: $pm);
            return { $pm };"#,
    ];
    
    let mut all_metadata = Vec::new();
    
    for func_text in functions {
        match extract_function_metadata(func_text) {
            Ok(metadata) => {
                print_function_metadata(&metadata);
                all_metadata.push(metadata);
            }
            Err(e) => {
                eprintln!("❌ Error parsing function: {}", e);
            }
        }
    }
    
    // Save metadata to JSON
    if !all_metadata.is_empty() {
        save_metadata_to_json(&all_metadata)?;
    }
    
    Ok(())
}

fn print_function_metadata(metadata: &FunctionMetadata) {
    println!("{}", "=".repeat(60));
    println!("Function Name: {}", metadata.name);
    println!();
    
    println!("Parameters:");
    if metadata.parameters.is_empty() {
        println!("  (none)");
    } else {
        for param in &metadata.parameters {
            println!("  ${}: {}", param.name, param.type_name);
        }
    }
    println!();
    
    println!("Output: {}", metadata.output);
    println!();
    
    println!("Code Block:");
    for line in metadata.code_block.lines() {
        println!("  {}", line);
    }
    println!();
}

fn save_metadata_to_json(metadata: &[FunctionMetadata]) -> Result<()> {
    let json_output = serde_json::to_string_pretty(metadata)?;
    fs::write("function_metadata.json", json_output)?;
    println!("{}", "=".repeat(60));
    println!("✅ All metadata successfully extracted and saved to function_metadata.json");
    
    // Print summary
    println!();
    println!("📊 Summary:");
    println!("   Total functions parsed: {}", metadata.len());
    for meta in metadata {
        println!("   - {} ({} params, returns {})", 
            meta.name, 
            meta.parameters.len(),
            meta.output
        );
    }
    
    Ok(())
}