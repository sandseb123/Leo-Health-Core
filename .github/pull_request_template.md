## What does this PR do?

<!-- One paragraph summary of the change -->

## Type of change

- [ ] Bug fix
- [ ] New feature (parser, table, metric)
- [ ] Refactor / code quality
- [ ] CI / tooling
- [ ] Documentation

## Checklist

- [ ] `python -m pytest tests/` passes locally
- [ ] `ruff check leo_health/` passes with no errors
- [ ] No new `import requests` / network imports added (`grep -r "import requests" leo_health/` returns nothing)
- [ ] New parser functions have corresponding tests in `tests/test_parsers.py`
- [ ] Schema changes include `CREATE TABLE IF NOT EXISTS` (safe to re-run)
- [ ] `CHANGELOG.md` updated under `[Unreleased]`

## Testing

<!-- Describe how you tested this. Include sample data if adding a new parser. -->

## Privacy impact

<!-- Does this change touch network code, file paths, or external services? If yes, explain. -->
