# Pult

## Principles

- **Test-driven**: write tests first, also check with linters
- **Comments**: explain *why*, not *what*
- **No over-engineering**: use Django directly, extract only when duplication hurts


## Style

- Line length: 100
- Code: English. UI: Ukrainian
- Keyword args for 3+ params
- `@transaction.atomic` for multi-record changes
- Type hints for function signatures
