#!/bin/bash
# ============================================================================
# Schema Code Generation Script
# ============================================================================
# Generates Python (Pydantic) and TypeScript types from JSON Schema files
#
# Usage: ./generate-types.sh
#
# Requirements:
#   - datamodel-code-generator (Python): pip install datamodel-code-generator
#   - json-schema-to-typescript (Node): npm install -g json-schema-to-typescript
#
# This script reads JSON Schema files from packages/contracts/schemas/
# and generates:
#   - Pydantic models → packages/contracts/generated/python/
#   - TypeScript types → packages/contracts/generated/typescript/

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SCHEMAS_DIR="$PROJECT_ROOT/packages/contracts/schemas"
PYTHON_OUT="$PROJECT_ROOT/packages/contracts/generated/python"
TS_OUT="$PROJECT_ROOT/packages/contracts/generated/typescript"

echo "🔨 SOLVER Schema Code Generation"
echo "================================="
echo ""

# Check if required tools are installed
if ! command -v datamodel-codegen &> /dev/null; then
    echo "❌ datamodel-code-generator not found"
    echo "Install with: pip install datamodel-code-generator"
    exit 1
fi

if ! command -v json2ts &> /dev/null; then
    echo "❌ json-schema-to-typescript not found"
    echo "Install with: npm install -g json-schema-to-typescript"
    exit 1
fi

# Create output directories
mkdir -p "$PYTHON_OUT"
mkdir -p "$TS_OUT"

echo "📁 Schema directory: $SCHEMAS_DIR"
echo "📁 Python output: $PYTHON_OUT"
echo "📁 TypeScript output: $TS_OUT"
echo ""

# ============================================================================
# Generate Python (Pydantic) Models
# ============================================================================
echo "🐍 Generating Python (Pydantic) models..."

# Find all JSON schema files
SCHEMA_FILES=$(find "$SCHEMAS_DIR" -name "*.json" -type f)

if [ -z "$SCHEMA_FILES" ]; then
    echo "⚠️  No schema files found in $SCHEMAS_DIR"
else
    for schema in $SCHEMA_FILES; do
        filename=$(basename "$schema" .json)
        echo "  - $filename.json → $filename.py"

        datamodel-codegen \
            --input "$schema" \
            --output "$PYTHON_OUT/${filename}.py" \
            --output-model-type pydantic_v2.BaseModel \
            --use-standard-collections \
            --use-schema-description \
            --field-constraints \
            --snake-case-field
    done

    # Create __init__.py to make it a package
    echo "# Auto-generated Pydantic models from JSON Schema" > "$PYTHON_OUT/__init__.py"
    echo "# Do not edit manually - regenerate with scripts/generate-types.sh" >> "$PYTHON_OUT/__init__.py"
    echo "" >> "$PYTHON_OUT/__init__.py"

    for schema in $SCHEMA_FILES; do
        filename=$(basename "$schema" .json)
        module_name=$(echo "$filename" | sed 's/-/_/g')
        echo "from .${module_name} import *" >> "$PYTHON_OUT/__init__.py"
    done

    echo "✓ Python models generated"
fi

echo ""

# ============================================================================
# Generate TypeScript Types
# ============================================================================
echo "📘 Generating TypeScript types..."

if [ -z "$SCHEMA_FILES" ]; then
    echo "⚠️  No schema files found in $SCHEMAS_DIR"
else
    for schema in $SCHEMA_FILES; do
        filename=$(basename "$schema" .json)
        echo "  - $filename.json → $filename.ts"

        json2ts \
            --input "$schema" \
            --output "$TS_OUT/${filename}.ts" \
            --bannerComment "/* Auto-generated from JSON Schema - Do not edit manually */"
    done

    # Create index.ts barrel export
    echo "/* Auto-generated barrel export - Do not edit manually */" > "$TS_OUT/index.ts"
    echo "" >> "$TS_OUT/index.ts"

    for schema in $SCHEMA_FILES; do
        filename=$(basename "$schema" .json)
        echo "export * from './${filename}';" >> "$TS_OUT/index.ts"
    done

    echo "✓ TypeScript types generated"
fi

echo ""
echo "✅ Code generation complete!"
echo ""
echo "Usage:"
echo "  Python: from contracts.generated.python import ProblemDefinitionPackage"
echo "  TypeScript: import { ProblemDefinitionPackage } from '@solver/contracts'"
