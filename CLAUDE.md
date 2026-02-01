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
4. Test `trash` by setting `in_trash: true` and uploading

## Constraints

- Keep changes minimal - this fork exists to fix compatibility, not add features
- Maintain backwards compatibility with upstream where possible
- Be respectful of Paprika's unofficial API (~40 calls/hour limit)

---

## Lessons Learned (January 2026)

### UID Format Requirements

Paprika rejects recipes with invalid UIDs. Valid format:
```
XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX-XXXXX-XXXXXXXXXXXXXXXX
```
Example: `4578C83D-3DFE-48D6-9C4A-628C4E62DA92-63733-0000147775974853`

The `BaseRecipe` class auto-generates valid UIDs for new recipes, but manually created YAML files must use this format.

### Recipe Deletion

There is no delete API. To "delete" a recipe:
1. Set `in_trash: true` in the recipe YAML
2. Upload the modified recipe
3. Recipe moves to Paprika's trash (reversible)

### Download Validation

Downloaded recipes should be validated:
- All files should be valid YAML
- Required fields: `name`, `uid`
- `in_trash: true` recipes appear in download but not in app's main list
- Recipe count from API may differ from app display (trashed recipes)

### Upload Behavior

- Upload overwrites existing recipes (matched by UID)
- Upload writes server response back to local file (updates hash, etc.)
- `notify()` is called after upload to trigger sync on devices
- Empty `hash` field is OK - will be calculated before upload

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "Invalid uid" on upload | UID not in Paprika format | Use auto-generated UID or proper format |
| Silent upload failure at 0% | Missing `--account` or bad credentials | Check `~/.config/paprika-recipes/config.yaml` |
| FileNotFoundError on download | Recipe name contains `/` | Fixed in this fork with filename sanitization |
| "Unrecognized client" on login | Using v2 API | Fixed in this fork - uses v1 API |

### Recipe Field Notes

- `categories`: List of UUID strings (not human-readable names)
- `rating`: Integer 0-5
- `created`: String format `YYYY-MM-DD HH:MM:SS`
- `photo`: Base64 encoded image data (can be large)
- `in_trash`: Boolean, controls visibility in app
- `hash`: SHA256 of recipe content, auto-calculated on upload

### Testing Without Destruction

To test upload safely:
1. Create a new test recipe (auto-generates new UID)
2. Upload it
3. Verify in app
4. Set `in_trash: true` and upload again to remove

To test with existing recipes:
- Upload unchanged recipe (idempotent, same data)
- Avoid modifying real recipes until confident
