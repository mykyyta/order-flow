# V2 Refactoring Plan (Execution)

Цей план адаптований під поточний стан репозиторію (`apps/orders`, `apps/customer_orders`,
`apps/inventory`, `apps/materials`, `apps/catalog`) і базується на `docs/v2_model_design_proposal.md`.

## Підхід

- Рефакторинг іде інкрементально, без одномоментного перейменування всіх legacy-моделей.
- Кожен етап має сумісний перехідний стан (nullable FK, adapter services, data migrations).
- Кожна зміна закривається тестами (моделі + сервіси + інтеграційні сценарії).

## Етап 1. Variant Key і розрив циклів (in progress)

1. [x] Додати `catalog.ProductVariant` як єдиний ключ варіанту.
2. [x] Додати nullable `product_variant` у:
   - `orders.Order`
   - `customer_orders.CustomerOrderLine`
   - `customer_orders.CustomerOrderLineComponent`
   - `inventory.StockRecord`
3. [x] Backfill migration:
   - `get_or_create` варіанта на основі `(product_model, color, primary_material_color, secondary_material_color)`
   - заповнити `product_variant_id` у всіх таблицях вище.
4. [~] Перевести нові сервіси читання/запису на `product_variant`, старі поля лишити тимчасово.
5. [x] Додати валідацію узгодженості: якщо `product_variant` заданий, він має відповідати legacy-полям.

## Етап 2. Multi-warehouse foundation

1. [ ] Створити app `warehouses` і модель `Warehouse`.
2. [ ] Додати `warehouse` у:
   - `inventory.StockRecord`
   - `materials.MaterialStockRecord`
   - `materials.GoodsReceipt`
3. [ ] Додати дефолтний склад (`MAIN`) data migration-ом.
4. [ ] Переглянути unique constraints stock-таблиць з урахуванням складу.

## Етап 3. Виділення procurement/material_inventory

1. [ ] Створити app `procurement`:
   - `Supplier`, `SupplierOffer`, `PurchaseOrder`, `PurchaseOrderLine`,
     `GoodsReceipt`, `GoodsReceiptLine`.
2. [ ] Створити app `material_inventory`:
   - `MaterialStockRecord`, `MaterialStockMovement`, `MaterialStockTransfer*`.
3. [ ] Перенести бізнес-логіку із `apps/materials/services/*` в нові контексти.
4. [ ] Залишити compatibility imports на перехідний період.

## Етап 4. Sales/Production/Inventory V2 контексти

1. [ ] Створити app `sales` (`SalesOrder*`) і мапінг зі `customer_orders`.
2. [ ] Створити app `production` (`ProductionOrder*`) і мапінг зі `orders`.
3. [ ] Розширити `inventory` до:
   - `FinishedStock*`
   - `WIPStock*`
   - transfer-моделей.
4. [ ] Перенести статусні політики у відповідні контексти.

## Етап 5. Fulfillment orchestration

1. [ ] Додати app `fulfillment` (без ORM).
2. [ ] Перенести міжконтекстні сценарії:
   - create sales order
   - create production orders
   - receive purchase order line
   - complete production order
3. [ ] Інтеграційні тести оркестрації (happy-path + rollback-перевірки).

## Етап 6. Legacy import pipeline

1. [ ] Команда `import_legacy` з режимами:
   - `--dry-run`
   - `--apply`
   - `--verify`
2. [ ] Таблиця мапінгу статусів і причин рухів.
3. [ ] Звірка агрегатів після імпорту (orders, stock balances, матеріали).

## Етап 7. Cutover

1. [ ] Переключити UI на V2-моделі.
2. [ ] Freeze legacy writes.
3. [ ] Final import + verify.
4. [ ] Видалити legacy-поля і compatibility-шар.

## Поточний статус

- `2026-02-09`: Етап 1 стартував.
- Реалізовано:
  - `catalog.ProductVariant` + міграція + тести constraints;
  - nullable `product_variant` у `orders/customer_orders/inventory`;
  - backfill-міграції для існуючих записів;
  - автопроставлення `product_variant` у сервісах створення (order, customer_order_line, stock);
  - model-level валідація узгодженості `product_variant` з legacy-полями в `orders`,
    `customer_orders`, `inventory`;
  - variant-first API у `inventory.services` (`get/add/remove` по `product_variant_id`) і
    використання цього шляху в production-planning.
- Наступний інкремент: почати Етап 2 (`warehouses` app + дефолтний `MAIN`).
