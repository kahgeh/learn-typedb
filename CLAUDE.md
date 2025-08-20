# TypeDB Project Notes

## ⚠️ CRITICAL: Always Check Documentation First

Use v3.x syntax.

**BEFORE writing any TypeDB query, schema definition, or data insertion:**
1. Check the official TypeDB 3.x documentation in `docs/typedb-docs-3.x/`
2. Reference the correct syntax from the documentation
3. Do NOT rely on memory or assumptions about TypeDB syntax

### Documentation Reference Paths
- **TypeQL Syntax**: `docs/typedb-docs-3.x/core-concepts/modules/ROOT/pages/typeql/`
- **Schema & Data**: `docs/typedb-docs-3.x/core-concepts/modules/ROOT/pages/typeql/schema-data.adoc`
- **Query Clauses**: `docs/typedb-docs-3.x/core-concepts/modules/ROOT/pages/typeql/query-clauses.adoc`
- **Examples**: `docs/typedb-docs-3.x/examples/modules/ROOT/pages/`

The documentation is maintained as a git submodule from:
```
https://github.com/typedb/typedb-docs/tree/3.x-development/
```

To update the documentation:
```bash
git submodule update --remote docs/typedb-docs-3.x
```

### Tools to verify your work
**Running Queries:**
```bash
typedb console --address=localhost:1729 --username=admin --tls-disabled --password password --script=queries/file.tqls
```

### User Preferences

1. **Query Organization**: Keep queries as plain text files in `queries/` folder
2. **File Extension**: Use `.tqls` for TypeDB console script files
3. **Separation of Concerns**: Queries should be separate from execution scripts
4. **Focus**: Plain query text helps maintain focus on TypeQL logic
5. **Documentation**: Each query file should be self-contained and runnable

### Common Issues Encountered

1. **Connection**: Requires credentials and `is_tls_enabled=False` for local setup
2. **Script Path**: Must run from project root to avoid path doubling issues

### Project Structure That Works

```
queries/        # Plain TypeQL scripts (.tqls)
schemas/        # Schema definitions (.tql)
data/          # Data files (.tql)
scripts/       # Python automation scripts
```

### Tax System Domain Model

- Uses semantic modeling for tax forms, fields, calculations, and validations
- Relations as first-class citizens with attributes
- Validation rules and calculations stored in database (not application layer)
- Supports temporal versioning for different tax years

### Setup Commands

⚠️ CRITICAL: Always use uv to run any python scripts 

```bash
# Start TypeDB
typedb server

# Load database
uv run python scripts/setup_database_simple.py

# Verify
uv run python scripts/verify_database.py

# Run queries
typedb console --address=localhost:1729 --username=admin --tls-disabled --password password --script=queries/01-count-entities.tqls
```

### Future Interactions

When working with TypeDB in this project:
1. Assume TypeDB 3.0 syntax and conventions
2. Keep queries in plain `.tqls` files
3. Test with actual console commands, not just Python driver
4. Focus on semantic modeling benefits for complex domains like tax systems
