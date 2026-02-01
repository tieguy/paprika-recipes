# Recipe Validation Implementation Plan - Phase 3

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:executing-an-implementation-plan to implement this plan task-by-task.

**Goal:** Integrate validation into upload-recipes command (fail fast)

**Architecture:** Modify upload_recipes.py to validate ALL recipes before uploading ANY. If validation fails, print errors and exit without making any API calls.

**Tech Stack:** Python

**Scope:** Phase 3 of 3

**Codebase verified:** 2026-02-01

**Dependencies:** Phase 1 (RecipeValidator must exist)

---

## Phase 3: Upload Integration

**Goal:** Upload command validates before uploading

### Task 1: Write failing tests for upload validation

**Files:**
- Modify: `tests/test_validation.py` (add new test class)

**Step 1: Add test class for upload validation**

Add to end of `tests/test_validation.py`:

```python
class TestUploadValidation:
    """Test upload-recipes validates before uploading."""

    def test_upload_validates_all_before_uploading(self, tmp_path):
        """Upload should validate all recipes before any API calls."""
        # Create one valid and one invalid recipe
        valid = BaseRecipe(name="Valid", uid="4578C83D-3DFE-48D6-9C4A-628C4E62DA92")
        invalid = BaseRecipe(name="", uid="bad-uid")

        with open(tmp_path / "valid.paprikarecipe.yaml", "w") as f:
            dump_recipe_yaml(valid, f)
        with open(tmp_path / "invalid.paprikarecipe.yaml", "w") as f:
            dump_recipe_yaml(invalid, f)

        from paprika_recipes.commands.upload_recipes import Command

        class MockOptions:
            import_path = tmp_path

        cmd = Command(MockOptions(), {})

        # Run validation (should fail before any uploads)
        errors = cmd.validate_all_recipes()
        assert len(errors) > 0

    def test_upload_succeeds_when_all_valid(self, tmp_path):
        """Upload validation should pass when all recipes are valid."""
        valid1 = BaseRecipe(name="Recipe 1", uid="4578C83D-3DFE-48D6-9C4A-628C4E62DA92")
        valid2 = BaseRecipe(name="Recipe 2", uid="9b6deb02-3e9e-40be-add0-fae94ed2eaf8")

        with open(tmp_path / "recipe1.paprikarecipe.yaml", "w") as f:
            dump_recipe_yaml(valid1, f)
        with open(tmp_path / "recipe2.paprikarecipe.yaml", "w") as f:
            dump_recipe_yaml(valid2, f)

        from paprika_recipes.commands.upload_recipes import Command

        class MockOptions:
            import_path = tmp_path

        cmd = Command(MockOptions(), {})
        errors = cmd.validate_all_recipes()

        assert errors == {}
```

**Step 2: Run tests to verify they fail**

```bash
cd /var/home/louie/Projects/family/krissa.org/tools/paprika-sync && \
uv run pytest ../paprika-recipes-fork/tests/test_validation.py::TestUploadValidation -v
```

Expected: FAIL with `AttributeError: 'Command' object has no attribute 'validate_all_recipes'`

### Task 2: Add validation to upload-recipes command

**Files:**
- Modify: `paprika_recipes/commands/upload_recipes.py`

**Step 1: Add imports**

At top of file, add these imports (after line 4):

```python
import sys
from typing import Dict, List
from ..recipe import BaseRecipe, RecipeValidator, ValidationError
```

**Step 2: Add validate_all_recipes method**

Add this method to the Command class (before the `handle` method):

```python
    def validate_all_recipes(self) -> Dict[Path, List[ValidationError]]:
        """Validate all recipes before upload. Returns dict of file -> errors."""
        all_errors: Dict[Path, List[ValidationError]] = {}

        for recipe_file in self.options.import_path.glob("*.paprikarecipe.yaml"):
            with open(recipe_file, "r") as f:
                data = safe_load(f)

            recipe = BaseRecipe.from_dict(data)
            errors = RecipeValidator.validate(recipe)

            if errors:
                all_errors[recipe_file] = errors

        return all_errors

    def _print_validation_errors(self, errors: Dict[Path, List[ValidationError]]) -> None:
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

**Step 3: Modify handle method to validate first**

Replace the `handle` method with:

```python
    def handle(self) -> None:
        # Validate ALL recipes before uploading ANY
        validation_errors = self.validate_all_recipes()
        if validation_errors:
            self._print_validation_errors(validation_errors)
            sys.exit(1)

        remote = self.get_remote()

        files = list(self.options.import_path.glob("*.paprikarecipe.yaml"))

        for recipe_file in track(files, description="Uploading Recipes"):
            with open(recipe_file, "r") as inf:
                uploaded = remote.upload_recipe(RemoteRecipe.from_dict(safe_load(inf)))

            with open(recipe_file, "w") as outf:
                dump_recipe_yaml(uploaded, outf)

        remote.notify()
```

**Step 4: Run tests to verify they pass**

```bash
cd /var/home/louie/Projects/family/krissa.org/tools/paprika-sync && \
uv run pytest ../paprika-recipes-fork/tests/test_validation.py::TestUploadValidation -v
```

Expected: All tests PASS

**Step 5: Run full test suite**

```bash
cd /var/home/louie/Projects/family/krissa.org/tools/paprika-sync && \
uv run pytest ../paprika-recipes-fork/tests/ -v
```

Expected: All tests PASS

**Step 6: Commit**

```bash
cd /var/home/louie/Projects/family/krissa.org/tools/paprika-recipes-fork && \
git add paprika_recipes/commands/upload_recipes.py tests/test_validation.py && \
git commit -m "$(cat <<'EOF'
feat: validate recipes before upload (fail fast)

- Upload command now validates ALL recipes before uploading ANY
- Validation errors printed with file names and details
- Exits with error if any recipe invalid
- No API calls made until all recipes pass validation

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

### Task 3: Update documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `readme.md`

**Step 1: Update CLAUDE.md**

Add to the "Lessons Learned" section:

```markdown
### Recipe Validation

The `validate-recipes` command validates recipe files locally before upload:
- Checks UID format (UUID required)
- Checks name is present
- Checks categories are UUID strings

`upload-recipes` automatically validates all recipes before uploading any.
```

**Step 2: Update readme.md**

Add a new section after "Moving Recipes to Trash":

```markdown
### Validating Recipes

You can validate recipe files before uploading:

```
paprika-recipes validate-recipes /path/to/recipes/
```

This checks:
- UID is valid UUID format
- Name is present
- Categories are UUID strings

The `upload-recipes` command automatically validates all recipes first and will refuse to upload if any are invalid.
```

**Step 3: Commit documentation**

```bash
cd /var/home/louie/Projects/family/krissa.org/tools/paprika-recipes-fork && \
git add CLAUDE.md readme.md && \
git commit -m "$(cat <<'EOF'
docs: add recipe validation documentation

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Final Verification

After all phases complete:

```bash
# Run full test suite
cd /var/home/louie/Projects/family/krissa.org/tools/paprika-sync && \
uv run pytest ../paprika-recipes-fork/tests/ -v

# Test validate command manually
uv run paprika-recipes validate-recipes ../paprika-sync/test-download/

# Verify all tests pass
echo "If all tests pass and validate command works, implementation is complete."
```
