# Recipe Validation Before Upload Design

## Summary

This design introduces client-side validation for recipe data before uploading to the Paprika API. Currently, the tool relies on server-side validation which returns cryptic error messages like "Invalid uid" without indicating which recipe failed or why. The new validation system inspects recipes locally, checking required fields (name, UID) and data formats (UID structure, categories) before making any API calls. This provides clear, actionable error messages and prevents wasted API requests against Paprika's rate-limited service.

The implementation adds a `RecipeValidator` class with pluggable validation rules, a standalone `validate-recipes` command for checking recipe files without uploading, and integration into the existing `upload-recipes` command to fail fast when invalid recipes are detected. Validation happens after recipes are loaded from disk but before any network activity, allowing developers to catch data issues during local development rather than discovering them mid-upload.

## Definition of Done
- RecipeValidator class exists in recipe.py with validate() method
- Validation checks: UID format, name required, categories format
- New `validate-recipes` command validates files without uploading
- `upload-recipes` command validates all recipes before any uploads
- All validation tests pass
- Documentation updated

## Glossary

- **BaseRecipe**: Python dataclass representing a Paprika recipe with fields like name, UID, categories, ingredients, etc. Loaded from YAML files on disk.
- **UID**: Unique Identifier for recipes in Paprika's system. Must follow UUID format (e.g., `4578C83D-3DFE-48D6-9C4A-628C4E62DA92`).
- **ValidationError**: Dataclass representing a single validation failure, containing the field name that failed, an error message, and the problematic value.
- **Paprika API**: Unofficial, reverse-engineered REST API for the Paprika recipe manager app. Has undocumented rate limits (~40 calls/hour).
- **Fail fast**: Design principle where the system stops immediately upon detecting an error rather than attempting to continue.

## Architecture

Recipe validation uses a standalone validator class that checks recipes against known API requirements before upload. The validator is separate from the BaseRecipe dataclass to allow loading invalid recipes for inspection.

**Components:**
- `RecipeValidator` class in `paprika_recipes/recipe.py` - validates recipes, returns list of errors
- `ValidationError` dataclass in `paprika_recipes/recipe.py` - represents a single validation failure
- `validate-recipes` command in `paprika_recipes/commands/validate_recipes.py` - standalone validation
- Modified `upload-recipes` command - validates all before uploading any

**Data flow:**
1. User runs `validate-recipes` or `upload-recipes`
2. Recipe files loaded from disk as BaseRecipe objects
3. RecipeValidator.validate() called on each recipe
4. Errors collected and displayed grouped by file
5. For upload: proceed only if zero errors

## Existing Patterns

Investigation found no existing validation in the codebase. The current approach trusts server-side validation, which provides poor error messages.

This design introduces validation following patterns from:
- Error handling in `remote.py` (raise specific exceptions)
- Command structure in `commands/` directory (BaseCommand subclasses)
- Recipe operations in `recipe.py` (class methods on dataclasses)

## Implementation Phases

### Phase 1: Validator Core
**Goal:** RecipeValidator class with validation rules

**Components:**
- `ValidationError` dataclass in `paprika_recipes/recipe.py` - field, message, value
- `RecipeValidator` class in `paprika_recipes/recipe.py` - validate() class method
- Validation rules: _validate_uid(), _validate_name(), _validate_categories()

**Dependencies:** None

**Done when:** RecipeValidator.validate() returns errors for invalid recipes, empty list for valid recipes. Tests pass.

### Phase 2: Validate Command
**Goal:** Standalone validate-recipes command

**Components:**
- `paprika_recipes/commands/validate_recipes.py` - new Command class
- Entry point registration in `setup.cfg`

**Dependencies:** Phase 1 (validator exists)

**Done when:** `paprika-recipes validate-recipes <path>` validates all recipes in directory, reports errors, exits non-zero if any invalid. Tests pass.

### Phase 3: Upload Integration
**Goal:** Upload command validates before uploading

**Components:**
- Modified `paprika_recipes/commands/upload_recipes.py` - add validation step

**Dependencies:** Phase 1 (validator exists)

**Done when:** `upload-recipes` fails fast with validation errors before any API calls. Tests pass.

## Additional Considerations

**Error output format:** Errors grouped by file for readability. Each error shows field name, message, and problematic value (if relevant).

**Future extensibility:** Validator class structure allows easy addition of new validation rules without changing command code.
