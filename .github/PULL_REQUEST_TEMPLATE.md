## Summary

<!-- What changed, and why? Keep this short and concrete. -->

## Scope

- [ ] Desktop app
- [ ] CLI
- [ ] MCP server
- [ ] Core file operations
- [ ] Documentation
- [ ] CI / packaging

## Safety Checklist

- [ ] File moves/deletes remain preview-first or explicitly confirmed.
- [ ] MCP paths stay scoped to allowed roots.
- [ ] Write-like MCP behavior is guarded by write mode and tests.
- [ ] User files are not overwritten silently.
- [ ] Documentation does not overstate implemented behavior.

## Validation

<!-- List the exact checks you ran. -->

- [ ] `pre-commit run --all-files`
- [ ] `python -m pytest`
- [ ] Manual UI check, if relevant

## Screenshots / Notes

<!-- Add screenshots, logs, or follow-up notes when useful. -->
