use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use typeql::parse_definition_function;

#[derive(Debug, Serialize, Deserialize)]
pub struct FunctionMetadata {
    pub name: String,
    pub parameters: Vec<Parameter>,
    pub output: String,
    pub return_expression: Option<String>,
    pub code_block: String,
    pub referenced_functions: Vec<String>,
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
    
    // Extract referenced functions from the AST debug string
    let referenced_functions = extract_referenced_functions(&debug_str);
    
    // Extract return expression for native types
    let return_expression = extract_return_expression(&debug_str);
    
    Ok(FunctionMetadata {
        name,
        parameters,
        output,
        return_expression,
        code_block,
        referenced_functions,
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

fn extract_return_expression(debug_str: &str) -> Option<String> {
    // Look for return_stmt in the AST
    if let Some(return_pos) = debug_str.find("return_stmt: ") {
        let return_section = &debug_str[return_pos..];
        
        // Check for Single return with selector (first, last, etc.)
        if return_section.starts_with("return_stmt: Single(") {
            // Extract selector (First, Last, etc.)
            let selector = if return_section.contains("selector: First") {
                "first "
            } else if return_section.contains("selector: Last") {
                "last "
            } else if return_section.contains("selector: Any") {
                ""
            } else {
                ""
            };
            
            // Find the variable in vars array
            if let Some(vars_pos) = return_section.find("vars: [") {
                let vars_section = &return_section[vars_pos..];
                if let Some(ident_pos) = vars_section.find("ident: \"") {
                    let ident_start = ident_pos + 8;
                    if let Some(ident_end) = vars_section[ident_start..].find("\"") {
                        let var_name = &vars_section[ident_start..ident_start + ident_end];
                        return Some(format!("{}${}", selector, var_name));
                    }
                }
            }
        }
        // Check for Reduce return (aggregate functions)
        else if return_section.starts_with("return_stmt: Reduce(") {
            // Look for reduce_operator
            if let Some(op_pos) = return_section.find("reduce_operator: ") {
                let op_start = op_pos + 17;
                let op_section = &return_section[op_start..];
                if let Some(op_end) = op_section.find(",").or(op_section.find("\n")) {
                    let operator = op_section[..op_end].trim().to_lowercase();
                    
                    // Find the variable being aggregated
                    if let Some(var_pos) = return_section.find("variable: Named") {
                        let var_section = &return_section[var_pos..];
                        if let Some(ident_pos) = var_section.find("ident: \"") {
                            let ident_start = ident_pos + 8;
                            if let Some(ident_end) = var_section[ident_start..].find("\"") {
                                let var_name = &var_section[ident_start..ident_start + ident_end];
                                return Some(format!("{}(${})", operator, var_name));
                            }
                        }
                    }
                }
            }
        }
        // Check for Stream return (set of values)
        else if return_section.starts_with("return_stmt: Stream(") {
            // Find the variables in the stream
            if let Some(vars_pos) = return_section.find("vars: [") {
                let vars_section = &return_section[vars_pos..];
                if let Some(ident_pos) = vars_section.find("ident: \"") {
                    let ident_start = ident_pos + 8;
                    if let Some(ident_end) = vars_section[ident_start..].find("\"") {
                        let var_name = &vars_section[ident_start..ident_start + ident_end];
                        return Some(format!("{{ ${} }}", var_name));
                    }
                }
            }
        }
    }
    
    None
}

fn extract_referenced_functions(debug_str: &str) -> Vec<String> {
    let mut referenced_functions = Vec::new();
    let mut seen = HashSet::new();
    
    // Look for function calls in the AST debug output
    // Function calls appear as: FunctionCall { ... name: Identifier( ... ident: "function_name"
    
    let mut remaining = debug_str;
    
    while let Some(call_start) = remaining.find("FunctionCall {") {
        let call_section = &remaining[call_start..];
        
        // Look for the name: Identifier pattern within this FunctionCall
        if let Some(name_start) = call_section.find("name: Identifier(") {
            let name_section = &call_section[name_start..];
            
            // Find the ident field within the Identifier
            if let Some(ident_start) = name_section.find("ident: \"") {
                let ident_start = ident_start + 8;
                if let Some(quote_end) = name_section[ident_start..].find("\"") {
                    let func_name = name_section[ident_start..ident_start + quote_end].to_string();
                    
                    // Only add if we haven't seen this function before
                    if seen.insert(func_name.clone()) {
                        referenced_functions.push(func_name);
                    }
                }
            }
        }
        
        // Move past this FunctionCall
        remaining = &remaining[call_start + 14..];
    }
    
    referenced_functions
}