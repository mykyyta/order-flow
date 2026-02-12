# Pult

Order management system for production brand.

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


## Key Apps

| App | Purpose |
|-----|---------|
| `catalog` | Product, Variant, Color, Bundle, BOM |
| `sales` | Customer, SalesOrder |
| `production` | ProductionOrder, status flow |
| `inventory` | ProductStock, WIPStock |
| `materials` | Material, Supplier, PurchaseOrder, MaterialStock |
| `fulfillment` | Cross-context orchestration (no models) |


## Docs

- [Architecture](docs/architecture.md) — bounded contexts, data flow
- [Conventions](docs/conventions.md) — code style, naming, patterns
