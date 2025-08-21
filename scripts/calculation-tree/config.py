"""Configuration for the tax calculation tree visualization"""

# Database configuration
DATABASE_CONFIG = {
    "name": "tax-system",
    "host": "localhost:1729",
    "username": "admin",
    "password": "password",
    "tls_enabled": False
}

# Visualization configuration
VISUALIZATION_CONFIG = {
    "default_root_field": "1040-line-16",  # Federal Income Tax
    "show_line_numbers": True,
    "show_function_names": True,
    "show_attributes": True
}

# Sample data configuration (for testing/demo)
SAMPLE_DATA_CONFIG = {
    "default_tax_year": 2024,
    "default_filing_status": "single",
    "default_taxpayer_ssn": "123-45-6789"
}