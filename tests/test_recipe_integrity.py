"""Data integrity tests for recipe round-trip serialization."""

import gzip
import io
import json
import os
from pathlib import Path

import pytest

from paprika_recipes.recipe import BaseRecipe
from paprika_recipes.utils import dump_recipe_yaml, load_yaml


# Path to real recipe data for integration tests
REAL_RECIPES_DIR = Path(__file__).parent.parent.parent / "paprika-sync" / "test-download"


class TestYamlRoundTrip:
    """Test that YAML serialization/deserialization preserves all data."""

    def test_all_fields_preserved_after_round_trip(self):
        """All recipe fields should survive YAML round-trip."""
        original = BaseRecipe(
            name="Test Recipe",
            description="A test description",
            ingredients="1 cup flour\n2 eggs",
            directions="Mix well.\nBake at 350F.",
            notes="Some notes here",
            nutritional_info="100 calories per serving",
            categories=["cat-uuid-1", "cat-uuid-2"],
            cook_time="30 minutes",
            difficulty="easy",
            image_url="https://example.com/image.jpg",
            prep_time="15 minutes",
            rating=4,
            servings="4",
            source="Test Kitchen",
            source_url="https://example.com/recipe",
            total_time="45 minutes",
        )
        # Capture the auto-generated fields
        original_uid = original.uid
        original_hash = original.hash
        original_created = original.created

        # Serialize to YAML
        buffer = io.StringIO()
        dump_recipe_yaml(original, buffer)
        yaml_content = buffer.getvalue()

        # Deserialize back
        buffer.seek(0)
        loaded_dict = load_yaml(buffer)
        restored = BaseRecipe.from_dict(loaded_dict)

        # Verify all fields match
        assert restored.name == "Test Recipe"
        assert restored.description == "A test description"
        assert restored.ingredients == "1 cup flour\n2 eggs"
        assert restored.directions == "Mix well.\nBake at 350F."
        assert restored.notes == "Some notes here"
        assert restored.nutritional_info == "100 calories per serving"
        assert restored.categories == ["cat-uuid-1", "cat-uuid-2"]
        assert restored.cook_time == "30 minutes"
        assert restored.difficulty == "easy"
        assert restored.image_url == "https://example.com/image.jpg"
        assert restored.prep_time == "15 minutes"
        assert restored.rating == 4
        assert restored.servings == "4"
        assert restored.source == "Test Kitchen"
        assert restored.source_url == "https://example.com/recipe"
        assert restored.total_time == "45 minutes"
        assert restored.uid == original_uid
        assert restored.hash == original_hash
        assert restored.created == original_created

    def test_unicode_characters_preserved(self):
        """Unicode characters in ingredients and directions should survive round-trip."""
        original = BaseRecipe(
            name="Crème Brûlée",
            ingredients="200g crème fraîche\n1 gousse de vanille\n50g de sucre",
            directions="Préchauffez le four à 150°C.\nMélangez les ingrédients.",
            notes="Très délicieux! 美味しい! Вкусно!",
        )

        buffer = io.StringIO()
        dump_recipe_yaml(original, buffer)
        buffer.seek(0)
        loaded_dict = load_yaml(buffer)
        restored = BaseRecipe.from_dict(loaded_dict)

        assert restored.name == "Crème Brûlée"
        assert "crème fraîche" in restored.ingredients
        assert "vanille" in restored.ingredients
        assert "150°C" in restored.directions
        assert "Très délicieux!" in restored.notes
        assert "美味しい!" in restored.notes
        assert "Вкусно!" in restored.notes

    def test_special_characters_in_name(self):
        """Special characters in recipe names should survive round-trip."""
        test_names = [
            "Mom's Famous Cake",
            'Recipe "Special Edition"',
            "Spicy & Sweet Chicken",
            "50/50 Mix",
            "Recipe #1",
            "Test: A Recipe",
            "Recipe (Family Version)",
        ]

        for name in test_names:
            original = BaseRecipe(name=name)
            buffer = io.StringIO()
            dump_recipe_yaml(original, buffer)
            buffer.seek(0)
            loaded_dict = load_yaml(buffer)
            restored = BaseRecipe.from_dict(loaded_dict)
            assert restored.name == name, f"Name '{name}' not preserved"

    def test_empty_and_null_fields_preserved(self):
        """Empty strings and null fields should not cause data loss."""
        original = BaseRecipe(
            name="Minimal Recipe",
            description="",
            ingredients="",
            directions="",
            notes="",
            nutritional_info="",
            categories=[],
            cook_time="",
            difficulty="",
            image_url=None,
            in_trash=False,
            is_pinned=False,
            on_favorites=False,
            on_grocery_list=False,
            prep_time="",
            rating=0,
            servings="",
            source="",
            source_url="",
            total_time="",
            photo=None,
            photo_hash=None,
            photo_large=None,
            photo_url=None,
            scale=None,
        )

        buffer = io.StringIO()
        dump_recipe_yaml(original, buffer)
        buffer.seek(0)
        loaded_dict = load_yaml(buffer)
        restored = BaseRecipe.from_dict(loaded_dict)

        assert restored.name == "Minimal Recipe"
        assert restored.description == ""
        assert restored.ingredients == ""
        assert restored.categories == []
        assert restored.rating == 0
        assert restored.photo is None
        assert restored.photo_large is None
        assert restored.in_trash is False
        assert restored.is_pinned is False
        assert restored.on_favorites is False
        assert restored.on_grocery_list is False

    def test_base64_photo_data_preserved(self):
        """Base64-encoded photo data should survive round-trip."""
        # Small test image (1x1 red pixel PNG, base64 encoded)
        test_photo = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="

        original = BaseRecipe(
            name="Recipe with Photo",
            photo=test_photo,
            photo_hash="abc123",
        )

        buffer = io.StringIO()
        dump_recipe_yaml(original, buffer)
        buffer.seek(0)
        loaded_dict = load_yaml(buffer)
        restored = BaseRecipe.from_dict(loaded_dict)

        assert restored.photo == test_photo
        assert restored.photo_hash == "abc123"

    def test_multiline_text_formatting_preserved(self):
        """Multiline text should preserve exact formatting including blank lines."""
        ingredients = """1 cup flour
2 eggs

For the sauce:
1 cup cream
2 tbsp butter"""

        directions = """Step 1: Mix dry ingredients.

Step 2: Add wet ingredients.

Note: Let rest for 10 minutes.

Step 3: Bake."""

        original = BaseRecipe(
            name="Multiline Test",
            ingredients=ingredients,
            directions=directions,
        )

        buffer = io.StringIO()
        dump_recipe_yaml(original, buffer)
        buffer.seek(0)
        loaded_dict = load_yaml(buffer)
        restored = BaseRecipe.from_dict(loaded_dict)

        assert restored.ingredients == ingredients
        assert restored.directions == directions

    def test_hash_calculation_consistent(self):
        """Hash should be calculable and consistent after round-trip."""
        original = BaseRecipe(
            name="Hash Test",
            ingredients="1 cup test",
            directions="Mix well",
        )
        original_calculated = original.calculate_hash()

        buffer = io.StringIO()
        dump_recipe_yaml(original, buffer)
        buffer.seek(0)
        loaded_dict = load_yaml(buffer)
        restored = BaseRecipe.from_dict(loaded_dict)

        restored_calculated = restored.calculate_hash()
        assert restored_calculated == original_calculated


class TestPaprikaRecipeFormat:
    """Test .paprikarecipe format (gzipped JSON) round-trip."""

    def test_paprikarecipe_round_trip(self):
        """Recipe should survive gzip/JSON round-trip (.paprikarecipe format)."""
        original = BaseRecipe(
            name="Gzip Test Recipe",
            ingredients="1 cup flour\n2 eggs",
            directions="Mix and bake.",
            categories=["uuid-1", "uuid-2"],
            rating=5,
        )
        original_uid = original.uid

        # Serialize to .paprikarecipe format (gzipped JSON)
        compressed = original.as_paprikarecipe()

        # Decompress and parse
        decompressed = gzip.decompress(compressed)
        data = json.loads(decompressed)
        restored = BaseRecipe.from_dict(data)

        assert restored.name == "Gzip Test Recipe"
        assert restored.ingredients == "1 cup flour\n2 eggs"
        assert restored.directions == "Mix and bake."
        assert restored.categories == ["uuid-1", "uuid-2"]
        assert restored.rating == 5
        assert restored.uid == original_uid

    def test_paprikarecipe_unicode_preserved(self):
        """Unicode should survive gzip/JSON round-trip."""
        original = BaseRecipe(
            name="Crêpes Suzette",
            ingredients="Crème fraîche",
            notes="日本語テスト Ελληνικά",
        )

        compressed = original.as_paprikarecipe()
        decompressed = gzip.decompress(compressed)
        data = json.loads(decompressed)
        restored = BaseRecipe.from_dict(data)

        assert restored.name == "Crêpes Suzette"
        assert "Crème fraîche" in restored.ingredients
        assert "日本語テスト" in restored.notes
        assert "Ελληνικά" in restored.notes


class TestFieldTypeCoercion:
    """Test that field types are handled correctly."""

    def test_rating_stays_integer(self):
        """Rating should remain an integer after round-trip."""
        original = BaseRecipe(name="Rating Test", rating=3)

        buffer = io.StringIO()
        dump_recipe_yaml(original, buffer)
        buffer.seek(0)
        loaded_dict = load_yaml(buffer)
        restored = BaseRecipe.from_dict(loaded_dict)

        assert restored.rating == 3
        assert isinstance(restored.rating, int)

    def test_categories_stays_list(self):
        """Categories should remain a list after round-trip."""
        original = BaseRecipe(
            name="Categories Test",
            categories=["uuid-1", "uuid-2", "uuid-3"],
        )

        buffer = io.StringIO()
        dump_recipe_yaml(original, buffer)
        buffer.seek(0)
        loaded_dict = load_yaml(buffer)
        restored = BaseRecipe.from_dict(loaded_dict)

        assert restored.categories == ["uuid-1", "uuid-2", "uuid-3"]
        assert isinstance(restored.categories, list)

    def test_empty_categories_stays_list(self):
        """Empty categories should remain a list, not become None."""
        original = BaseRecipe(name="Empty Categories", categories=[])

        buffer = io.StringIO()
        dump_recipe_yaml(original, buffer)
        buffer.seek(0)
        loaded_dict = load_yaml(buffer)
        restored = BaseRecipe.from_dict(loaded_dict)

        assert restored.categories == []
        assert isinstance(restored.categories, list)


class TestFilenameEdgeCases:
    """Test filename sanitization for problematic recipe names."""

    def test_sanitize_filename_slash(self):
        """Forward slash should be replaced in filenames."""
        from paprika_recipes.utils import sanitize_filename

        assert "/" not in sanitize_filename("50/50 Mix")
        assert sanitize_filename("50/50 Mix") == "50-50 Mix"

    def test_sanitize_filename_backslash(self):
        """Backslash should be replaced in filenames."""
        from paprika_recipes.utils import sanitize_filename

        assert "\\" not in sanitize_filename("Path\\Recipe")
        assert sanitize_filename("Path\\Recipe") == "Path-Recipe"

    def test_sanitize_filename_special_chars(self):
        """Special characters should be replaced in filenames."""
        from paprika_recipes.utils import sanitize_filename

        result = sanitize_filename('Recipe: "Test" <special>')
        assert ":" not in result
        assert '"' not in result
        assert "<" not in result
        assert ">" not in result

    def test_sanitize_filename_preserves_normal_chars(self):
        """Normal characters should be preserved."""
        from paprika_recipes.utils import sanitize_filename

        assert sanitize_filename("Normal Recipe Name") == "Normal Recipe Name"
        assert sanitize_filename("Recipe #1") == "Recipe #1"
        assert sanitize_filename("Mom's Cookies") == "Mom's Cookies"


@pytest.mark.skipif(
    not REAL_RECIPES_DIR.exists(),
    reason="Real recipe data not available"
)
class TestRealRecipeData:
    """Integration tests using real downloaded recipe data."""

    def get_recipe_files(self):
        """Get all recipe YAML files from test-download directory."""
        return list(REAL_RECIPES_DIR.glob("*.paprikarecipe.yaml"))

    def test_real_recipes_load_without_error(self):
        """All real recipes should load without errors."""
        recipe_files = self.get_recipe_files()
        assert len(recipe_files) > 0, "No recipe files found"

        errors = []
        for recipe_file in recipe_files:
            try:
                with open(recipe_file) as f:
                    data = load_yaml(f)
                    BaseRecipe.from_dict(data)
            except Exception as e:
                errors.append(f"{recipe_file.name}: {e}")

        assert not errors, f"Failed to load {len(errors)} recipes:\n" + "\n".join(errors[:10])

    def test_real_recipes_round_trip(self):
        """Real recipes should survive YAML round-trip."""
        recipe_files = self.get_recipe_files()[:50]  # Test first 50 to keep fast

        errors = []
        for recipe_file in recipe_files:
            try:
                # Load original
                with open(recipe_file) as f:
                    original_data = load_yaml(f)
                original = BaseRecipe.from_dict(original_data)

                # Round-trip
                buffer = io.StringIO()
                dump_recipe_yaml(original, buffer)
                buffer.seek(0)
                restored_data = load_yaml(buffer)
                restored = BaseRecipe.from_dict(restored_data)

                # Verify key fields
                assert restored.name == original.name, f"Name mismatch in {recipe_file.name}"
                assert restored.uid == original.uid, f"UID mismatch in {recipe_file.name}"
                assert restored.ingredients == original.ingredients, f"Ingredients mismatch in {recipe_file.name}"

            except Exception as e:
                errors.append(f"{recipe_file.name}: {e}")

        assert not errors, f"Round-trip failed for {len(errors)} recipes:\n" + "\n".join(errors[:10])

    def test_real_recipes_have_required_fields(self):
        """All real recipes should have name and uid."""
        recipe_files = self.get_recipe_files()

        missing_fields = []
        for recipe_file in recipe_files:
            with open(recipe_file) as f:
                data = load_yaml(f)

            if not data.get("name"):
                missing_fields.append(f"{recipe_file.name}: missing name")
            if not data.get("uid"):
                missing_fields.append(f"{recipe_file.name}: missing uid")

        assert not missing_fields, f"Missing required fields:\n" + "\n".join(missing_fields[:10])

    def test_real_recipes_hash_calculation(self):
        """Hash calculation should work on real recipes."""
        recipe_files = self.get_recipe_files()[:20]  # Test subset

        for recipe_file in recipe_files:
            with open(recipe_file) as f:
                data = load_yaml(f)
            recipe = BaseRecipe.from_dict(data)

            # Should not raise
            calculated_hash = recipe.calculate_hash()
            assert isinstance(calculated_hash, str)
            assert len(calculated_hash) == 64  # SHA256 hex
