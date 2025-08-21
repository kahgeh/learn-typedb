use anyhow::Result;
use serde::{Deserialize, Serialize};
use typeql::parse_definition_function;

#[derive(Debug, Serialize, Deserialize)]
pub struct FunctionMetadata {
    pub name: String,
    pub parameters: Vec<Parameter>,
    pub output: String,
    pub code_block: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Parameter {
    pub name: String,
    pub type_name: String,
}

/// Extract metadata from a TypeQL function definition
pub fn extract_function_metadata(function_text: &str) -> Result<FunctionMetadata> {
    // Parse the function using TypeQL parser
    let func_ast = parse_definition_function(function_text)?;
    
    // Get debug string for detailed extraction
    let debug_str = format!("{:#?}", func_ast);
    
    // Extract function name
    let name = extract_function_name(&debug_str);
    
    // Extract parameters
    let parameters = extract_parameters(&debug_str);
    
    // Extract output/return type
    let output = extract_output(&debug_str);
    
    // Extract code block (the match block and return statement)
    let code_block = extract_code_block(function_text);
    
    Ok(FunctionMetadata {
        name,
        parameters,
        output,
        code_block,
    })
}

fn extract_function_name(debug_str: &str) -> String {
    // Find the function name in the signature
    if let Some(sig_start) = debug_str.find("signature: Signature") {
        let sig_section = &debug_str[sig_start..];
        if let Some(ident_start) = sig_section.find("ident: \"") {
            let name_start = ident_start + 8;
            if let Some(name_end) = sig_section[name_start..].find("\"") {
                return sig_section[name_start..name_start + name_end].to_string();
            }
        }
    }
    "unknown".to_string()
}

fn extract_parameters(debug_str: &str) -> Vec<Parameter> {
    let mut parameters = Vec::new();
    
    // Find the args section first
    if let Some(args_start) = debug_str.find("args: [") {
        let args_section = &debug_str[args_start..];
        
        // Find all Argument blocks within the args section
        let mut remaining = args_section;
        while let Some(arg_start) = remaining.find("Argument {") {
            let arg_section = &remaining[arg_start..];
            
            // Find the end of this argument block (look for the next Argument or the end of args)
            let next_arg = remaining[arg_start + 10..].find("Argument {").map(|p| p + arg_start + 10);
            let output_pos = remaining.find("],\n        output:");
            
            let arg_end = next_arg.unwrap_or(output_pos.unwrap_or(arg_section.len()));
            let current_arg = &remaining[arg_start..arg_end];
            
            // Extract variable name
            let var_name = if let Some(var_start) = current_arg.find("ident: \"") {
                let name_start = var_start + 8;
                if let Some(name_end) = current_arg[name_start..].find("\"") {
                    current_arg[name_start..name_start + name_end].to_string()
                } else {
                    remaining = &remaining[arg_start + 10..];
                    continue;
                }
            } else {
                remaining = &remaining[arg_start + 10..];
                continue;
            };
            
            // Extract type - look for the type_ field in this argument
            let type_name = if let Some(type_start) = current_arg.find("type_: Simple(") {
                let type_section = &current_arg[type_start..];
                
                // Check for BuiltinValueType first (for primitive types like double)
                if let Some(builtin_start) = type_section.find("BuiltinValueType(") {
                    let builtin_section = &type_section[builtin_start..];
                    if let Some(token_start) = builtin_section.find("token: ") {
                        let token_start = token_start + 7;
                        if let Some(token_end) = builtin_section[token_start..].find(",").or(builtin_section[token_start..].find("\n")) {
                            builtin_section[token_start..token_start + token_end]
                                .trim()
                                .trim_end_matches(',')
                                .to_lowercase()
                        } else {
                            "unknown".to_string()
                        }
                    } else {
                        "unknown".to_string()
                    }
                }
                // Then check for Label type (for custom types)
                else if let Some(label_start) = type_section.find("Label(") {
                    let label_section = &type_section[label_start..];
                    if let Some(ident_start) = label_section.find("ident: \"") {
                        let name_start = ident_start + 8;
                        if let Some(name_end) = label_section[name_start..].find("\"") {
                            label_section[name_start..name_start + name_end].to_string()
                        } else {
                            "unknown".to_string()
                        }
                    } else {
                        "unknown".to_string()
                    }
                } else {
                    "unknown".to_string()
                }
            } else {
                "unknown".to_string()
            };
            
            parameters.push(Parameter {
                name: var_name,
                type_name,
            });
            
            // Move to next argument
            remaining = &remaining[arg_start + 10..];
            
            // Stop if we've reached the end of args
            if output_pos.is_some() && arg_start > output_pos.unwrap() {
                break;
            }
        }
    }
    
    parameters
}

fn extract_output(debug_str: &str) -> String {
    // Check if it's a stream output
    if debug_str.contains("output: Stream(") {
        // Extract stream content
        if let Some(stream_start) = debug_str.find("output: Stream(") {
            let stream_section = &debug_str[stream_start..];
            let mut output_types = Vec::new();
            
            // Look for types in the stream
            if stream_section.contains("ident: \"") {
                let mut section = stream_section;
                while let Some(ident_start) = section.find("ident: \"") {
                    let name_start = ident_start + 8;
                    if let Some(name_end) = section[name_start..].find("\"") {
                        let type_name = section[name_start..name_start + name_end].to_string();
                        output_types.push(type_name);
                        section = &section[name_start + name_end..];
                        // Stop at the end of output section
                        if section.find("},").is_some() && section.find("},").unwrap() < 50 {
                            break;
                        }
                    } else {
                        break;
                    }
                }
            }
            
            if !output_types.is_empty() {
                format!("{{ {} }}", output_types.join(", "))
            } else {
                "{ stream }".to_string()
            }
        } else {
            "stream".to_string()
        }
    }
    // Single output
    else if let Some(output_start) = debug_str.find("output: Single(") {
        let output_section = &debug_str[output_start..];
        let mut output_types = Vec::new();
        
        // Look for the first type only (avoid collecting noise)
        if let Some(builtin_start) = output_section.find("BuiltinValueType(") {
            let builtin_section = &output_section[builtin_start..];
            if let Some(token_start) = builtin_section.find("token: ") {
                let token_start = token_start + 7;
                if let Some(token_end) = builtin_section[token_start..].find(",").or(builtin_section[token_start..].find("\n")) {
                    let type_name = builtin_section[token_start..token_start + token_end]
                        .trim()
                        .to_lowercase();
                    return type_name;
                }
            }
        }
        
        // Check for Label types (for tuple returns)
        let mut section = output_section;
        let mut depth = 0;
        while let Some(label_pos) = section.find("Label(") {
            if depth > 4 { break; }  // Limit to first few return types
            depth += 1;
            
            let label_section = &section[label_pos..];
            if let Some(ident_start) = label_section.find("ident: \"") {
                let name_start = ident_start + 8;
                if let Some(name_end) = label_section[name_start..].find("\"") {
                    let type_name = label_section[name_start..name_start + name_end].to_string();
                    output_types.push(type_name);
                }
            }
            section = &section[label_pos + 6..];
            
            // Stop at the end of the Single output section
            if section.find("],").is_some() && section.find("],").unwrap() < 100 {
                break;
            }
        }
        
        if !output_types.is_empty() {
            output_types[..output_types.len().min(4)].join(", ")  // Limit to first 4 types
        } else {
            "unknown".to_string()
        }
    } else {
        "unknown".to_string()
    }
}

fn extract_code_block(function_text: &str) -> String {
    // Find the match block and return statement
    // Look for the actual start of the match block or first statement after the colon
    if let Some(match_pos) = function_text.find("match") {
        let code_part = &function_text[match_pos..];
        
        // Clean up indentation
        let lines: Vec<&str> = code_part.lines().collect();
        let cleaned_lines: Vec<String> = lines.iter().map(|line| {
            line.trim_start().to_string()
        }).collect();
        
        cleaned_lines.join("\n")
    } else if let Some(colon_pos) = function_text.rfind("->") {
        // Find content after the return type declaration
        if let Some(actual_colon) = function_text[colon_pos..].find(':') {
            let start = colon_pos + actual_colon + 1;
            let code_part = function_text[start..].trim();
            
            // Clean up indentation
            let lines: Vec<&str> = code_part.lines().collect();
            let cleaned_lines: Vec<String> = lines.iter().map(|line| {
                line.trim_start().to_string()
            }).collect();
            
            cleaned_lines.join("\n")
        } else {
            function_text.to_string()
        }
    } else {
        function_text.to_string()
    }
}