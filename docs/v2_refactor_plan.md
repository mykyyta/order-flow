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

1. [x] Створити app `warehouses` і модель `Warehouse`.
2. [x] Додати `warehouse` у:
   - `inventory.StockRecord`
   - `materials.MaterialStockRecord`
   - `materials.GoodsReceipt`
3. [x] Додати дефолтний склад (`MAIN`) data migration-ом.
4. [x] Переглянути unique constraints stock-таблиць з урахуванням складу.

## Етап 3. Виділення procurement/material_inventory

1. [x] Створити app `procurement`:
   - `Supplier`, `SupplierOffer`, `PurchaseOrder`, `PurchaseOrderLine`,
     `GoodsReceipt`, `GoodsReceiptLine`.
2. [x] Створити app `material_inventory`:
   - `MaterialStockRecord`, `MaterialStockMovement`, `MaterialStockTransfer*`.
3. [x] Перенести бізнес-логіку із `apps/materials/services/*` в нові контексти.
4. [x] Залишити compatibility imports на перехідний період.

## Етап 4. Sales/Production/Inventory V2 контексти

1. [x] Створити app `sales` (`SalesOrder*`) і мапінг зі `customer_orders`.
2. [x] Створити app `production` (`ProductionOrder*`) і мапінг зі `orders`.
3. [x] Розширити `inventory` до:
   - `FinishedStock*`
   - `WIPStock*`
   - transfer-моделей.
4. [~] Перенести статусні політики у відповідні контексти.

## Етап 5. Fulfillment orchestration

1. [x] Додати app `fulfillment` (без ORM).
2. [~] Перенести міжконтекстні сценарії:
   - create sales order
   - create production orders
   - receive purchase order line
  - complete production order
  - transfer finished/material stock
3. [~] Інтеграційні тести оркестрації (happy-path + rollback-перевірки).

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
    використання цього шляху в production-planning;
  - `warehouses` app + `Warehouse` модель;
  - додано `warehouse` в `inventory.StockRecord`, `materials.MaterialStockRecord`,
    `materials.GoodsReceipt`;
  - data migrations: seed `MAIN` + backfill `warehouse_id` у stock/receipt таблицях;
  - stock services (`inventory`, `materials`) працюють з optional `warehouse_id` і
    default fallback на `MAIN`;
  - створено `procurement` і `material_inventory` app-контексти;
  - додано compatibility model exports (`apps.procurement.models`,
    `apps.material_inventory.models`);
  - винесено material stock логіку в `apps.material_inventory.services`;
  - винесено purchase receipt логіку в `apps.procurement.services`;
  - збережено legacy-імпорти через `apps.materials.procurement_services`;
  - замінено основні імпорти в тестах/сервісах на нові контексти
    (`apps.procurement.*`, `apps.material_inventory.*`);
  - додано окремий compatibility test для legacy export API.
  - перенесено адмін-реєстрації procurement/material inventory з `materials` у нові app-и;
  - додано `sales` і `production` app-контексти з compatibility models/services
    (`apps.sales.*`, `apps.production.*`);
  - в `inventory` додано `FinishedStock*` aliases і нові `WIPStockRecord` / `WIPStockMovement`;
  - додано WIP stock services (`get_wip_stock_quantity`, `add_to_wip_stock`, `remove_from_wip_stock`);
  - додано `FinishedStockTransfer` / `FinishedStockTransferLine`;
  - додано `MaterialStockTransfer` / `MaterialStockTransferLine` і exports у `material_inventory`;
  - додано `sales.domain` і `production.domain` як нові точки входу для статусів/переходів;
  - додано `fulfillment` app із orchestration wrappers:
    `create_sales_order_orchestrated`, `create_production_orders_for_sales_order`,
    `receive_purchase_order_line_orchestrated`, `complete_production_order`, `scrap_wip`,
    `transfer_finished_stock_orchestrated`, `transfer_material_stock_orchestrated`;
  - додано інтеграційні тести оркестрації для основних happy-path сценаріїв;
  - додано transfer use-cases в сервісах:
    `inventory.transfer_finished_stock`,
    `material_inventory.transfer_material_stock`;
  - додано `TRANSFER_IN` / `TRANSFER_OUT` причини рухів у finished/material stock;
  - додано тести на transfer-сервіси і згенеровано міграції:
    `inventory.0007_alter_stockmovement_reason`,
    `materials.0009_alter_materialmovement_reason`.
  - додано rollback тести оркестрації у `fulfillment`
    (over-receive PO line, material transfer without stock).
  - почато перенос status source-of-truth у `production.domain`:
    `production.domain.order_statuses` став базовим модулем, а `orders.domain.order_statuses`
    тепер працює як compatibility re-export.
  - production-related імпорти в `customer_orders/production/fulfillment` переведено на
    `apps.production.domain.status`.
- Наступний інкремент: завершити Етап 4/5
  (перенести status source-of-truth у `production/sales` і доповнити rollback/integration тести).
