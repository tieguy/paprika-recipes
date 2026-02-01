"""Release testing - automated tests for release checklist.

Tests for:
- Authentication flow (login, bearer token)
- Rate limiting (2-second delay between requests)
- Download recipes (API mocking)
- Upload recipes (payload format verification)
"""

import time
from unittest.mock import patch

import pytest
import responses

from paprika_recipes.remote import Remote, RemoteRecipe, DEFAULT_MIN_REQUEST_INTERVAL


class TestAuthentication:
    """Test authentication and bearer token handling."""

    @responses.activate
    def test_login_returns_bearer_token(self):
        """Successful login should return and cache bearer token."""
        responses.add(
            responses.POST,
            "https://www.paprikaapp.com/api/v1/account/login/",
            json={"result": {"token": "test-bearer-token-123"}},
            status=200,
        )

        remote = Remote(
            email="test@example.com",
            password="password123",
            min_request_interval=0,  # Disable rate limiting for test
        )

        token = remote.bearer_token
        assert token == "test-bearer-token-123"

    @responses.activate
    def test_bearer_token_is_cached(self):
        """Bearer token should be cached after first login."""
        responses.add(
            responses.POST,
            "https://www.paprikaapp.com/api/v1/account/login/",
            json={"result": {"token": "cached-token"}},
            status=200,
        )

        remote = Remote(
            email="test@example.com",
            password="password123",
            min_request_interval=0,
        )

        # Access token twice
        token1 = remote.bearer_token
        token2 = remote.bearer_token

        # Should only call API once
        assert len(responses.calls) == 1
        assert token1 == token2 == "cached-token"

    @responses.activate
    def test_login_failure_raises_error(self):
        """Failed login should raise PaprikaError."""
        from paprika_recipes.exceptions import PaprikaError

        responses.add(
            responses.POST,
            "https://www.paprikaapp.com/api/v1/account/login/",
            status=401,
        )

        remote = Remote(
            email="test@example.com",
            password="wrong-password",
            min_request_interval=0,
        )

        with pytest.raises(PaprikaError):
            _ = remote.bearer_token


class TestRateLimiting:
    """Test rate limiting between API requests."""

    @responses.activate
    def test_rate_limiting_delays_requests(self):
        """Requests should be delayed by min_request_interval."""
        # Mock login
        responses.add(
            responses.POST,
            "https://www.paprikaapp.com/api/v1/account/login/",
            json={"result": {"token": "test-token"}},
            status=200,
        )
        # Mock recipes list (called twice)
        responses.add(
            responses.GET,
            "https://www.paprikaapp.com/api/v2/sync/recipes/",
            json={"result": []},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://www.paprikaapp.com/api/v2/sync/recipes/",
            json={"result": []},
            status=200,
        )

        # Use short interval for faster test
        min_interval = 0.1
        remote = Remote(
            email="test@example.com",
            password="password123",
            min_request_interval=min_interval,
        )

        # Make two requests and measure time
        start = time.time()
        remote.count()  # First request (login + recipes list)
        remote.count()  # Second request (recipes list only, token cached)
        elapsed = time.time() - start

        # Should have delayed at least min_interval between the two recipe list calls
        assert elapsed >= min_interval, f"Expected delay of {min_interval}s, got {elapsed}s"

    def test_default_rate_limit_is_2_seconds(self):
        """Default rate limit should be 2 seconds."""
        assert DEFAULT_MIN_REQUEST_INTERVAL == 2.0

    @responses.activate
    def test_rate_limiting_can_be_disabled(self):
        """Rate limiting should be disableable with min_request_interval=0."""
        responses.add(
            responses.POST,
            "https://www.paprikaapp.com/api/v1/account/login/",
            json={"result": {"token": "test-token"}},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://www.paprikaapp.com/api/v2/sync/recipes/",
            json={"result": []},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://www.paprikaapp.com/api/v2/sync/recipes/",
            json={"result": []},
            status=200,
        )

        remote = Remote(
            email="test@example.com",
            password="password123",
            min_request_interval=0,  # Disabled
        )

        start = time.time()
        remote.count()
        remote.count()
        elapsed = time.time() - start

        # Should complete quickly without delay
        assert elapsed < 0.5, f"Expected fast execution, got {elapsed}s"


class TestDownloadRecipes:
    """Test downloading recipes from API."""

    @responses.activate
    def test_get_recipe_list(self):
        """Should fetch and parse recipe list from API."""
        responses.add(
            responses.POST,
            "https://www.paprikaapp.com/api/v1/account/login/",
            json={"result": {"token": "test-token"}},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://www.paprikaapp.com/api/v2/sync/recipes/",
            json={
                "result": [
                    {"uid": "recipe-1", "hash": "hash1"},
                    {"uid": "recipe-2", "hash": "hash2"},
                ]
            },
            status=200,
        )

        remote = Remote(
            email="test@example.com",
            password="password123",
            min_request_interval=0,
        )

        count = remote.count()
        assert count == 2

    @responses.activate
    def test_get_recipe_by_id(self):
        """Should fetch individual recipe details."""
        responses.add(
            responses.POST,
            "https://www.paprikaapp.com/api/v1/account/login/",
            json={"result": {"token": "test-token"}},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://www.paprikaapp.com/api/v2/sync/recipe/recipe-123/",
            json={
                "result": {
                    "uid": "recipe-123",
                    "name": "Test Recipe",
                    "ingredients": "1 cup flour",
                    "directions": "Mix well",
                    "hash": "abc123",
                }
            },
            status=200,
        )

        remote = Remote(
            email="test@example.com",
            password="password123",
            min_request_interval=0,
        )

        recipe = remote.get_recipe_by_id("recipe-123", "abc123")
        assert recipe.name == "Test Recipe"
        assert recipe.ingredients == "1 cup flour"
        assert recipe.directions == "Mix well"


class TestUploadRecipes:
    """Test uploading recipes to API."""

    @responses.activate
    def test_upload_recipe_sends_gzipped_json(self):
        """Upload should send recipe as gzipped JSON."""
        import gzip
        import json

        responses.add(
            responses.POST,
            "https://www.paprikaapp.com/api/v1/account/login/",
            json={"result": {"token": "test-token"}},
            status=200,
        )
        responses.add(
            responses.POST,
            "https://www.paprikaapp.com/api/v2/sync/recipe/test-uid-123/",
            json={"result": {}},
            status=200,
        )
        # Mock the get_recipe_by_id call after upload
        responses.add(
            responses.GET,
            "https://www.paprikaapp.com/api/v2/sync/recipe/test-uid-123/",
            json={
                "result": {
                    "uid": "test-uid-123",
                    "name": "Uploaded Recipe",
                    "hash": "newhash",
                }
            },
            status=200,
        )

        remote = Remote(
            email="test@example.com",
            password="password123",
            min_request_interval=0,
        )

        recipe = RemoteRecipe(
            uid="test-uid-123",
            name="Uploaded Recipe",
            ingredients="Test ingredients",
        )

        result = remote.upload_recipe(recipe)

        # Verify upload request was made
        upload_call = responses.calls[1]  # Second call after login
        assert upload_call.request.url == "https://www.paprikaapp.com/api/v2/sync/recipe/test-uid-123/"

        # Verify returned recipe
        assert result.uid == "test-uid-123"
        assert result.name == "Uploaded Recipe"

    @responses.activate
    def test_upload_recipe_updates_hash(self):
        """Upload should update recipe hash before sending."""
        responses.add(
            responses.POST,
            "https://www.paprikaapp.com/api/v1/account/login/",
            json={"result": {"token": "test-token"}},
            status=200,
        )
        responses.add(
            responses.POST,
            "https://www.paprikaapp.com/api/v2/sync/recipe/test-uid/",
            json={"result": {}},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://www.paprikaapp.com/api/v2/sync/recipe/test-uid/",
            json={"result": {"uid": "test-uid", "name": "Test", "hash": "updated"}},
            status=200,
        )

        remote = Remote(
            email="test@example.com",
            password="password123",
            min_request_interval=0,
        )

        recipe = RemoteRecipe(uid="test-uid", name="Test")
        original_hash = recipe.hash

        remote.upload_recipe(recipe)

        # Hash should have been recalculated
        assert recipe.hash != original_hash


class TestNotify:
    """Test notify API call."""

    @responses.activate
    def test_notify_calls_sync_endpoint(self):
        """Notify should call the sync notify endpoint."""
        responses.add(
            responses.POST,
            "https://www.paprikaapp.com/api/v1/account/login/",
            json={"result": {"token": "test-token"}},
            status=200,
        )
        responses.add(
            responses.POST,
            "https://www.paprikaapp.com/api/v2/sync/notify/",
            json={"result": {}},
            status=200,
        )

        remote = Remote(
            email="test@example.com",
            password="password123",
            min_request_interval=0,
        )

        remote.notify()

        # Verify notify endpoint was called
        assert any("/sync/notify/" in call.request.url for call in responses.calls)


class TestKeyringStorage:
    """Test password storage with keyring."""

    def test_keyring_stores_password(self):
        """Password should be stored in keyring after successful auth."""
        import keyring
        from paprika_recipes.constants import APP_NAME

        # Use a test email that won't conflict
        test_email = "test-keyring@example.com"
        test_password = "test-password-123"

        # Store password
        keyring.set_password(APP_NAME, test_email, test_password)

        # Retrieve and verify
        retrieved = keyring.get_password(APP_NAME, test_email)
        assert retrieved == test_password

        # Clean up
        keyring.delete_password(APP_NAME, test_email)

    def test_get_password_for_email(self):
        """get_password_for_email should retrieve from keyring."""
        import keyring
        from paprika_recipes.constants import APP_NAME
        from paprika_recipes.utils import get_password_for_email

        test_email = "test-util@example.com"
        test_password = "util-test-password"

        # Store password
        keyring.set_password(APP_NAME, test_email, test_password)

        # Retrieve using utility function
        retrieved = get_password_for_email(test_email)
        assert retrieved == test_password

        # Clean up
        keyring.delete_password(APP_NAME, test_email)

    def test_get_password_for_missing_email_raises(self):
        """get_password_for_email should raise for missing email."""
        from paprika_recipes.exceptions import AuthenticationError
        from paprika_recipes.utils import get_password_for_email

        with pytest.raises(AuthenticationError):
            get_password_for_email("nonexistent@example.com")

    def test_get_password_for_empty_email_raises(self):
        """get_password_for_email should raise for empty email."""
        from paprika_recipes.exceptions import AuthenticationError
        from paprika_recipes.utils import get_password_for_email

        with pytest.raises(AuthenticationError):
            get_password_for_email("")
