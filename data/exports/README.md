# Database Export

This directory contains exported database tables in JSON format.

## Export Summary

- **Export Date**: 2026-04-30
- **Total Tables**: 7
- **Total Records**: 58

## Exported Files

### 1. llm_providers.json (11 records)
LLM provider configurations including:
- Provider identification (code, name in Chinese/English)
- Icon and branding information
- API endpoint and documentation URLs
- Authentication requirements
- Sorting and recommendation settings

### 2. llm_models.json (37 records)
LLM model information including:
- Model specifications (max tokens, version)
- Capability tags (text generation, vision, code, etc.)
- Performance metrics (speed/quality ratings)
- Pricing information (input/output costs)
- Feature support (streaming, function calling, vision)

### 3. llm_configs.json (5 records)
User-configured LLM channel configurations including:
- API keys (encrypted)
- Endpoint configurations
- Model parameters (temperature, max tokens)
- Health status and performance metrics

### 4. ip_assets.json (4 records)
IP (Intellectual Property) asset data including:
- IP names and categories
- Reference images
- Style templates and tags
- Associated LoRA models

### 5. lora_models.json (0 records)
LoRA model configurations (currently empty)

### 6. task_records.json (0 records)
Task execution records (currently empty)

### 7. users.json (1 record)
User account information including:
- Username and email
- Authentication data (hashed passwords)
- User roles and permissions

## Usage

### Export All Tables
```bash
python export_database.py
```

### Export Specific Table
```bash
python export_database.py llm_providers
```

## File Format

All files are in JSON format with UTF-8 encoding:
- DateTime fields are ISO 8601 formatted
- Boolean values are JSON booleans
- NULL values are represented as null
- Arrays maintain their original structure

## Import/Restore

To restore data from these exports, you would need to:
1. Read the JSON files
2. Convert dictionaries back to model instances
3. Insert into the database with proper relationships

## Notes

- These exports are point-in-time snapshots
- Foreign key relationships are preserved through ID references
- Sensitive data (like API keys) are stored in encrypted form
- Export files can be used for backup, analysis, or migration
