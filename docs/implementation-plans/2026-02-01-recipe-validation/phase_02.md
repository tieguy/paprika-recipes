# Recipe Validation Implementation Plan - Phase 2

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:executing-an-implementation-plan to implement this plan task-by-task.

**Goal:** Add standalone `validate-recipes` command

**Architecture:** New command class that loads recipes from disk and validates them using RecipeValidator. Reports errors grouped by file and exits non-zero if any invalid.

**Tech Stack:** Python, argparse (via BaseCommand), pathlib

**Scope:** Phase 2 of 3

**Codebase verified:** 2026-02-01

**Dependencies:** Phase 1 (RecipeValidator must exist)

---

## Phase 2: Validate Command

**Goal:** Standalone validate-recipes command

### Task 1: Write failing tests for validate command

**Files:**
- Modify: `tests/test_validation.py` (add new test class)

**Step 1: Add imports and test class**

Add to end of `tests/test_validation.py`:

```python
import tempfile
import os
from pathlib import Path
from paprika_recipes.utils import dump_recipe_yaml


class TestValidateCommand:
    """Test validate-recipes command."""

    def test_validate_valid_recipes_returns_no_errors(self, tmp_path):
        """Valid recipes should pass validation."""
        # Create a valid recipe file
        recipe = BaseRecipe(
            name="Valid Recipe",
            uid="4578C83D-3DFE-48D6-9C4A-628C4E62DA92",
        )
        recipe_file = tmp_path / "valid.paprikarecipe.yaml"
        with open(recipe_file, "w") as f:
            dump_recipe_yaml(recipe, f)

        # Import and test command
        from paprika_recipes.commands.validate_recipes import Command

        # Create mock options
        class MockOptions:
            validate_path = tmp_path

        cmd = Command(MockOptions(), {})
        errors = cmd.validate_recipes()
        assert errors == {}

    def test_validate_invalid_recipes_returns_errors(self, tmp_path):
        """Invalid recipes should return errors grouped by file."""
        # Create an invalid recipe file (missing name)
        recipe = BaseRecipe(name="", uid="4578C83D-3DFE-48D6-9C4A-628C4E62DA92")
        recipe_file = tmp_path / "invalid.paprikarecipe.yaml"
        with open(recipe_file, "w") as f:
            dump_recipe_yaml(recipe, f)

        from paprika_recipes.commands.validate_recipes import Command

        class MockOptions:
            validate_path = tmp_path

        cmd = Command(MockOptions(), {})
        errors = cmd.validate_recipes()

        # Should have errors for the invalid file
        assert len(errors) == 1
        assert "invalid.paprikarecipe.yaml" in str(list(errors.keys())[0])

    def test_validate_multiple_files(self, tmp_path):
        """Should validate all recipe files in directory."""
        # Create mix of valid and invalid
        valid = BaseRecipe(name="Valid", uid="4578C83D-3DFE-48D6-9C4A-628C4E62DA92")
        invalid = BaseRecipe(name="", uid="bad-uid")

        with open(tmp_path / "valid.paprikarecipe.yaml", "w") as f:
            dump_recipe_yaml(valid, f)
        with open(tmp_path / "invalid.paprikarecipe.yaml", "w") as f:
            dump_recipe_yaml(invalid, f)

        from paprika_recipes.commands.validate_recipes import Command

        class MockOptions:
            validate_path = tmp_path

        cmd = Command(MockOptions(), {})
        errors = cmd.validate_recipes()

        # Should only have errors for invalid file
        assert len(errors) == 1
```

**Step 2: Run tests to verify they fail**

```bash
cd /var/home/louie/Projects/family/krissa.org/tools/paprika-sync && \
uv run pytest ../paprika-recipes-fork/tests/test_validation.py::TestValidateCommand -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'paprika_recipes.commands.validate_recipes'`

### Task 2: Implement validate-recipes command

**Files:**
- Create: `paprika_recipes/commands/validate_recipes.py`

**Step 1: Create the command file**

```python
"""Validate recipe files without uploading."""

import argparse
import sys
from pathlib import Path
from typing import Dict, List

from yaml import safe_load

from ..command import BaseCommand
from ..recipe import BaseRecipe, RecipeValidator, ValidationError
from ..types import ConfigDict


class Command(BaseCommand):
    """Validates recipe files without uploading to Paprika."""

    @classmethod
    def get_help(cls) -> str:
        return """Validates recipe files without uploading."""

    @classmethod
    def add_arguments(cls, parser: argparse.ArgumentParser, config: ConfigDict) -> None:
        parser.add_argument("validate_path", type=Path)

    def handle(self) -> None:
        errors = self.validate_recipes()

        if errors:
            self._print_errors(errors)
            sys.exit(1)
        else:
            file_count = len(list(self.options.validate_path.glob("*.paprikarecipe.yaml")))
            print(f"All {file_count} recipes valid.")

    def validate_recipes(self) -> Dict[Path, List[ValidationError]]:
        """Validate all recipes in path. Returns dict of file -> errors."""
        all_errors: Dict[Path, List[ValidationError]] = {}

        for recipe_file in self.options.validate_path.glob("*.paprikarecipe.yaml"):
            with open(recipe_file, "r") as f:
                data = safe_load(f)

            recipe = BaseRecipe.from_dict(data)
            errors = RecipeValidator.validate(recipe)

            if errors:
                all_errors[recipe_file] = errors

        return all_errors

    def _print_errors(self, errors: Dict[Path, List[ValidationError]]) -> None:
        """Print validation errors grouped by file."""
        print(f"\nValidation failed for {len(errors)} recipe(s):\n")

        for recipe_file, file_errors in errors.items():
            print(f"  {recipe_file.name}:")
            for error in file_errors:
                if error.value:
                    print(f"    - {error.field}: {error.message} (value: {error.value!r})")
                else:
                    print(f"    - {error.field}: {error.message}")
            print()

        print("Fix these errors before uploading.")
```

**Step 2: Run tests to verify they pass**

```bash
cd /var/home/louie/Projects/family/krissa.org/tools/paprika-sync && \
uv run pytest ../paprika-recipes-fork/tests/test_validation.py::TestValidateCommand -v
```

Expected: All tests PASS

### Task 3: Register command in setup.cfg

**Files:**
- Modify: `setup.cfg` (line 22 area)

**Step 1: Add entry point**

In `setup.cfg`, after line 29 (after `edit-recipe` entry), add:

```ini
    validate-recipes = paprika_recipes.commands.validate_recipes:Command
```

The full `paprika_recipes.commands` section should now be:

```ini
paprika_recipes.commands =
    extract-archive = paprika_recipes.commands.extract_archive:Command
    create-archive = paprika_recipes.commands.create_archive:Command
    store-password = paprika_recipes.commands.store_password:Command
    download-recipes = paprika_recipes.commands.download_recipes:Command
    upload-recipes = paprika_recipes.commands.upload_recipes:Command
    create-recipe = paprika_recipes.commands.create_recipe:Command
    edit-recipe = paprika_recipes.commands.edit_recipe:Command
    validate-recipes = paprika_recipes.commands.validate_recipes:Command
```

**Step 2: Reinstall package to register new command**

```bash
cd /var/home/louie/Projects/family/krissa.org/tools/paprika-sync && \
uv sync
```

**Step 3: Verify command is available**

```bash
cd /var/home/louie/Projects/family/krissa.org/tools/paprika-sync && \
uv run paprika-recipes --help
```

Expected: `validate-recipes` should appear in the command list

**Step 4: Run full test suite**

```bash
cd /var/home/louie/Projects/family/krissa.org/tools/paprika-sync && \
uv run pytest ../paprika-recipes-fork/tests/ -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
cd /var/home/louie/Projects/family/krissa.org/tools/paprika-recipes-fork && \
git add paprika_recipes/commands/validate_recipes.py setup.cfg tests/test_validation.py && \
git commit -m "$(cat <<'EOF'
feat: add validate-recipes command

- New standalone command to validate recipe files
- Reports errors grouped by file
- Exits non-zero if any recipes invalid
- Does not require API credentials (local validation only)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```
