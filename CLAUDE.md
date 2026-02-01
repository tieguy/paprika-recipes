# CLAUDE.md

Project instructions for AI coding assistants working on this codebase.

## Project Overview

Maintained fork of [coddingtonbear/paprika-recipes](https://github.com/coddingtonbear/paprika-recipes) - a CLI tool for managing Paprika recipe app data via API or exported archives. Updated to work with Python 3.11+ and current Paprika API changes.

## Key Changes from Upstream

1. **Relaxed dependency constraints** - Removed upper bounds on pyyaml, keyring, rich, questionary to allow installation with modern package versions
2. **v1 API login** - Paprika blocked unauthorized clients on v2 login endpoint; now uses v1
3. **Replaced pkg_resources with importlib.metadata** - Removes setuptools dependency and deprecation warnings
4. **Rate limiting** - 2-second minimum interval between API requests (configurable via `min_request_interval` parameter)
5. **Filename sanitization** - Recipe names with `/` or other special characters are sanitized when saving files

## Maintenance Notes

This fork is maintained with LLM assistance (Claude). Changes should be:
- Minimal and focused on keeping the tool functional
- Well-documented in commit messages
- Tested before release

## API Considerations

- The Paprika API is **unofficial** and reverse-engineered
- Rate limit: ~40 API calls/hour before temporary IP block
- Cache locally, sync minimally
- Be respectful of the service

## Quick Reference

```bash
# Install dependencies
uv sync

# Run CLI
uv run paprika-recipes --help

# Test authentication
uv run paprika-recipes store-password
```

## Key Files

- `paprika_recipes/remote.py` - API client with rate limiting
- `paprika_recipes/recipe.py` - Recipe data model
- `paprika_recipes/commands/` - CLI command implementations
- `requirements.txt` - Dependencies (relaxed version constraints)

## Testing Changes

Before any release:
1. Test `store-password` with real credentials
2. Test `download-recipes` to verify API access works
3. Test `upload-recipes` with a test recipe

## Constraints

- Keep changes minimal - this fork exists to fix compatibility, not add features
- Maintain backwards compatibility with upstream where possible
- Be respectful of Paprika's unofficial API (~40 calls/hour limit)
