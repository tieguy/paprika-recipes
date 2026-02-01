# AGENTS.md

This file provides guidance to AI coding assistants working on this codebase.

## Project Overview

This is a maintained fork of [coddingtonbear/paprika-recipes](https://github.com/coddingtonbear/paprika-recipes), updated to work with modern Python (3.11+) and current Paprika API changes.

## Key Changes from Upstream

1. **Relaxed dependency constraints** - Removed upper bounds on pyyaml, keyring, rich, questionary to allow installation with modern package versions
2. **v1 API login** - Paprika blocked unauthorized clients on v2 login endpoint; now uses v1
3. **Runtime version checking disabled** - `pkg_resources.load(require=False)` to avoid version conflicts

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

## Development

```bash
# Install with uv
uv sync

# Run CLI
uv run paprika-recipes --help
```

## Testing Changes

Before any release:
1. Test `store-password` with real credentials
2. Test `download-recipes` to verify API access works
3. Test `upload-recipes` with a test recipe
