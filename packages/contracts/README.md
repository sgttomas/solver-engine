# SOLVER Contracts

Shared schemas and type definitions for SOLVER API and Web applications.

## Overview

This package contains:
- **JSON Schema** definitions (source of truth)
- **Auto-generated** Pydantic models (Python)
- **Auto-generated** TypeScript types

## Structure

```
contracts/
├── schemas/              # JSON Schema files (SOURCE OF TRUTH)
│   ├── problem_definition_package.json
│   ├── requirements_package.json
│   └── objectives_package.json
├── generated/            # Auto-generated code (DO NOT EDIT)
│   ├── python/          # Pydantic models
│   └── typescript/      # TypeScript types
└── scripts/
    └── generate-types.sh # Code generation script
```

## Usage

### Adding a New Schema

1. Create JSON Schema file in `schemas/`:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "MyNewType",
  "type": "object",
  "properties": {
    "field_name": { "type": "string" }
  },
  "required": ["field_name"]
}
```

2. Run code generation:
```bash
cd packages/contracts
./scripts/generate-types.sh
```

3. Use generated types:

**Python:**
```python
from contracts.generated.python import MyNewType

obj = MyNewType(field_name="value")
```

**TypeScript:**
```typescript
import { MyNewType } from '@solver/contracts';

const obj: MyNewType = { fieldName: "value" };
```

## Installation

### Prerequisites

```bash
# Python
pip install datamodel-code-generator

# TypeScript
npm install -g json-schema-to-typescript
```

### Generate Types

```bash
./scripts/generate-types.sh
```

Or via make:
```bash
make generate-schemas  # From project root
```

## Notes

- **DO NOT** manually edit files in `generated/` - they will be overwritten
- JSON Schema files are the source of truth
- Generated files are committed to git for easier consumption
- Run code generation after any schema changes
