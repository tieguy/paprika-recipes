# Recipe Validation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:executing-an-implementation-plan to implement this plan task-by-task.

**Goal:** Add RecipeValidator class with validation rules for UID, name, and categories.

**Architecture:** Standalone validator class in recipe.py that checks recipes against known API requirements. Returns list of ValidationError dataclass instances.

**Tech Stack:** Python dataclasses, re module for regex validation

**Scope:** 3 phases from original design (phases 1-3)

**Codebase verified:** 2026-02-01

---

## Phase 1: Validator Core

**Goal:** RecipeValidator class with validation rules

### Task 1: Write failing tests for validation

**Files:**
- Create: `tests/test_validation.py`

**Step 1: Write the failing tests**

```python
"""Tests for recipe validation before upload."""

import re
import pytest
from paprika_recipes.recipe import BaseRecipe, ValidationError, RecipeValidator


class TestValidationError:
    """Test ValidationError dataclass."""

    def test_validation_error_has_required_fields(self):
        """ValidationError should have field, message, and optional value."""
        error = ValidationError(field="name", message="Name is required")
        assert error.field == "name"
        assert error.message == "Name is required"
        assert error.value is None

    def test_validation_error_with_value(self):
        """ValidationError should store problematic value."""
        error = ValidationError(field="uid", message="Invalid format", value="bad-uid")
        assert error.value == "bad-uid"


class TestRecipeValidator:
    """Test RecipeValidator class."""

    def test_valid_recipe_returns_no_errors(self):
        """Valid recipe should return empty error list."""
        recipe = BaseRecipe(
            name="Test Recipe",
            uid="4578C83D-3DFE-48D6-9C4A-628C4E62DA92",
            categories=["9b6deb02-3e9e-40be-add0-fae94ed2eaf8"],
        )
        errors = RecipeValidator.validate(recipe)
        assert errors == []

    def test_missing_name_returns_error(self):
        """Recipe without name should return error."""
        recipe = BaseRecipe(name="", uid="4578C83D-3DFE-48D6-9C4A-628C4E62DA92")
        errors = RecipeValidator.validate(recipe)
        assert len(errors) == 1
        assert errors[0].field == "name"
        assert "required" in errors[0].message.lower()

    def test_whitespace_only_name_returns_error(self):
        """Recipe with whitespace-only name should return error."""
        recipe = BaseRecipe(name="   ", uid="4578C83D-3DFE-48D6-9C4A-628C4E62DA92")
        errors = RecipeValidator.validate(recipe)
        assert any(e.field == "name" for e in errors)

    def test_missing_uid_returns_error(self):
        """Recipe without UID should return error."""
        recipe = BaseRecipe(name="Test Recipe", uid="")
        errors = RecipeValidator.validate(recipe)
        assert any(e.field == "uid" for e in errors)

    def test_invalid_uid_format_returns_error(self):
        """Recipe with invalid UID format should return error."""
        recipe = BaseRecipe(name="Test Recipe", uid="not-a-valid-uuid")
        errors = RecipeValidator.validate(recipe)
        assert any(e.field == "uid" for e in errors)
        # Error should include the bad value
        uid_error = next(e for e in errors if e.field == "uid")
        assert uid_error.value == "not-a-valid-uuid"

    def test_valid_uuid_formats_accepted(self):
        """Both standard and extended UUID formats should be valid."""
        # Standard UUID format
        recipe1 = BaseRecipe(
            name="Test",
            uid="4578C83D-3DFE-48D6-9C4A-628C4E62DA92",
        )
        assert RecipeValidator.validate(recipe1) == []

        # Extended Paprika format
        recipe2 = BaseRecipe(
            name="Test",
            uid="4578C83D-3DFE-48D6-9C4A-628C4E62DA92-63733-0000147775974853",
        )
        assert RecipeValidator.validate(recipe2) == []

        # Lowercase UUID
        recipe3 = BaseRecipe(
            name="Test",
            uid="9b6deb02-3e9e-40be-add0-fae94ed2eaf8",
        )
        assert RecipeValidator.validate(recipe3) == []

    def test_invalid_category_format_returns_error(self):
        """Categories with invalid format should return error."""
        recipe = BaseRecipe(
            name="Test Recipe",
            uid="4578C83D-3DFE-48D6-9C4A-628C4E62DA92",
            categories=["breakfast", "valid-uuid-format-here"],
        )
        errors = RecipeValidator.validate(recipe)
        # Should have error for "breakfast" which is not a UUID
        assert any(e.field == "categories" for e in errors)

    def test_empty_categories_is_valid(self):
        """Empty categories list should be valid."""
        recipe = BaseRecipe(
            name="Test Recipe",
            uid="4578C83D-3DFE-48D6-9C4A-628C4E62DA92",
            categories=[],
        )
        errors = RecipeValidator.validate(recipe)
        assert errors == []

    def test_multiple_errors_returned(self):
        """Multiple validation failures should all be reported."""
        recipe = BaseRecipe(name="", uid="bad", categories=["not-uuid"])
        errors = RecipeValidator.validate(recipe)
        assert len(errors) >= 3  # name, uid, categories
```

**Step 2: Run tests to verify they fail**

```bash
cd /var/home/louie/Projects/family/krissa.org/tools/paprika-sync && \
uv run pytest ../paprika-recipes-fork/tests/test_validation.py -v
```

Expected: FAIL with `ImportError: cannot import name 'ValidationError' from 'paprika_recipes.recipe'`

### Task 2: Implement ValidationError and RecipeValidator

**Files:**
- Modify: `paprika_recipes/recipe.py` (add after line 87)

**Step 1: Add imports at top of file**

Add `import re` to the imports (after line 7):

```python
import re
```

**Step 2: Add ValidationError dataclass and RecipeValidator class**

Add after the BaseRecipe class (after line 87):

```python
@dataclass
class ValidationError:
    """Represents a single validation failure."""
    field: str
    message: str
    value: Any = None


class RecipeValidator:
    """Validates recipes before upload to prevent known API failures."""

    # UUID pattern: standard 36-char or extended Paprika format
    UUID_PATTERN = re.compile(
        r'^[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}'
        r'(-[A-Fa-f0-9]{5}-[A-Fa-f0-9]{16})?$'
    )

    @classmethod
    def validate(cls, recipe: BaseRecipe) -> List[ValidationError]:
        """Validate recipe and return list of errors. Empty list = valid."""
        errors: List[ValidationError] = []
        errors.extend(cls._validate_uid(recipe))
        errors.extend(cls._validate_name(recipe))
        errors.extend(cls._validate_categories(recipe))
        return errors

    @classmethod
    def _validate_uid(cls, recipe: BaseRecipe) -> List[ValidationError]:
        """UID must be valid UUID format."""
        errors: List[ValidationError] = []
        if not recipe.uid:
            errors.append(ValidationError("uid", "UID is required"))
        elif not cls.UUID_PATTERN.match(recipe.uid):
            errors.append(ValidationError(
                "uid",
                "Invalid UID format - must be UUID",
                recipe.uid
            ))
        return errors

    @classmethod
    def _validate_name(cls, recipe: BaseRecipe) -> List[ValidationError]:
        """Name is required."""
        errors: List[ValidationError] = []
        if not recipe.name or not recipe.name.strip():
            errors.append(ValidationError("name", "Recipe name is required"))
        return errors

    @classmethod
    def _validate_categories(cls, recipe: BaseRecipe) -> List[ValidationError]:
        """Categories must be UUID strings if present."""
        errors: List[ValidationError] = []
        if recipe.categories:
            for i, cat in enumerate(recipe.categories):
                if not isinstance(cat, str) or not cls.UUID_PATTERN.match(cat):
                    errors.append(ValidationError(
                        "categories",
                        f"Category {i} is not a valid UUID",
                        cat
                    ))
        return errors
```

**Step 3: Run tests to verify they pass**

```bash
cd /var/home/louie/Projects/family/krissa.org/tools/paprika-sync && \
uv run pytest ../paprika-recipes-fork/tests/test_validation.py -v
```

Expected: All tests PASS

**Step 4: Run full test suite to verify no regressions**

```bash
cd /var/home/louie/Projects/family/krissa.org/tools/paprika-sync && \
uv run pytest ../paprika-recipes-fork/tests/ -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
cd /var/home/louie/Projects/family/krissa.org/tools/paprika-recipes-fork && \
git add paprika_recipes/recipe.py tests/test_validation.py && \
git commit -m "$(cat <<'EOF'
feat: add RecipeValidator for pre-upload validation

- Add ValidationError dataclass to represent validation failures
- Add RecipeValidator class with validate() class method
- Validation rules: UID format, name required, categories format
- Supports standard UUID and extended Paprika UUID formats

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```
