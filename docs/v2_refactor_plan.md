# V2 Refactoring Plan (Execution)

Цей план адаптований під поточний стан репозиторію (`apps/orders`, `apps/customer_orders`,
`apps/inventory`, `apps/materials`, `apps/catalog`) і базується на `docs/v2_model_design_proposal.md`.

## Підхід

- Рефакторинг іде інкрементально, без одномоментного перейменування всіх legacy-моделей.
- Кожен етап має сумісний перехідний стан (nullable FK, adapter services, data migrations).
- Кожна зміна закривається тестами (моделі + сервіси + інтеграційні сценарії).

## Етап 1. Variant Key і розрив циклів

1. [x] Додати `catalog.ProductVariant` як єдиний ключ варіанту.
2. [x] Додати nullable `product_variant` у:
   - `orders.Order`
   - `customer_orders.CustomerOrderLine`
   - `customer_orders.CustomerOrderLineComponent`
   - `inventory.StockRecord`
3. [x] Backfill migration:
   - `get_or_create` варіанта на основі `(product_model, color, primary_material_color, secondary_material_color)`
   - заповнити `product_variant_id` у всіх таблицях вище.
4. [x] Перевести нові сервіси читання/запису на `product_variant`, старі поля лишити тимчасово.
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
4. [x] Перенести статусні політики у відповідні контексти.

## Етап 5. Fulfillment orchestration

1. [x] Додати app `fulfillment` (без ORM).
2. [x] Перенести міжконтекстні сценарії:
   - create sales order
   - create production orders
   - receive purchase order line
  - complete production order
  - transfer finished/material stock
3. [x] Інтеграційні тести оркестрації (happy-path + rollback-перевірки).

## Етап 6. Legacy import pipeline

1. [x] Команда `import_legacy` з режимами:
   - `--dry-run`
   - `--apply`
   - `--verify`
2. [x] Таблиця мапінгу статусів і причин рухів.
3. [x] Звірка агрегатів після імпорту (orders, stock balances, матеріали).

## Етап 7. Cutover

1. [x] Переключити UI на V2-моделі.
2. [x] Freeze legacy writes.
3. [x] Final import + verify.
4. [x] Видалити legacy write-paths і ізолювати compatibility-шар на runtime-рівні.

## Поточний статус

- `2026-02-09`: Етап 1 стартував.
- `2026-02-10`: старт baseline/reset гілки для clean V2 migration history.
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
  - статусну бізнес-логіку sales (line production + order rollup) винесено в
    `apps.sales.domain.policies` і підключено з `customer_orders.services`.
  - додано scaffolding для Етапу 6: command `import_legacy`
    (`--dry-run`, `--apply`, `--verify`) + тести команд.
  - додано таблиці мапінгу legacy → V2 (`orders/stock/material movement`) у
    `apps.orders.legacy_import_mappings`;
  - `import_legacy --verify` повертає базовий aggregate snapshot
    (orders/sales/variants/stock counts) + тести.
  - `import_legacy --verify` розширено метриками балансів
    (finished/material stock totals, movement net totals, delta).
  - додано деталізацію verify-звірки:
    finished balances по складах, material balances по складах+unit.
  - `import_legacy --apply` більше не заглушка:
    додано нормалізацію legacy статусів/причин через mapping-таблиці + тести.
  - додано `--strict` для `import_legacy --verify`:
    команда падає при ненульових verify-дельтах.
  - `import_legacy --dry-run` тепер рахує pending updates і unknown values без запису в БД;
  - `import_legacy --verify` перевіряє:
    глобальні дельти, дельти по складах/одиницях, і наявність unmapped значень;
  - `import_legacy --apply` обгорнуто в транзакцію, а після застосування повертаються
    залишкові pending updates.
  - додано cutover-прапорець `FREEZE_LEGACY_WRITES` і блокування запису через
    `apps.materials.procurement_services` (legacy compatibility write path).
  - UI production-потік (`orders` views/forms) перемкнено на `apps.production.*`
    (models/services/domain) замість прямих імпортів `apps.orders.*`;
  - freeze-перевірки поширено на legacy service entrypoints:
    `apps.orders.services` і `apps.customer_orders.services`;
  - V2 wrappers (`apps.production.services`, `apps.sales.services`) працюють при freeze
    через `via_v2_context` bypass, додано тести на цей контракт.
  - додано режим `--final` у `import_legacy` (apply + strict verify в одному кроці)
    та тести на success/failure і конфліктні прапорці.
  - у `customer_orders.services` creation-потік production order переведено на
    `apps.production.services` (без прямого виклику `apps.orders.services.create_order`).
  - `orders` UI і статусна презентація переведені на production контекст
    (`apps.production.models/services/domain`) у views/forms/template tags.
  - переведено status imports у legacy orders-контурі на production domain
    (`orders.services`, management commands, telegram bot, policies);
  - додано freeze-guard для `sync_customer_order_line_production` /
    `_sync_customer_order_status`, щоб закрити remaining legacy write path;
  - додано тест, що `create_sales_order(..., create_production_orders=True)` працює
    при `FREEZE_LEGACY_WRITES=True`.
  - `apps.orders.domain.status` і `apps.orders.domain.transitions` переведено
    на прямі compatibility re-export з `apps.production.domain.*`.
  - type contracts у V2 сервісах (`sales/production/fulfillment/inventory/procurement/material_inventory`)
    переведено на `AbstractBaseUser` + V2 aliases (`SalesOrder*`/`ProductionOrder*`)
    без прямих type-only імпортів legacy моделей;
  - `apps.sales.domain.status` і sales/production тести переведені на імпорти через
    `apps.sales.models` / `apps.production.models` (замість прямих legacy model imports);
  - `orders.services` більше не ходить напряму в `customer_orders.services` для sync:
    додано `sales.services.sync_sales_order_line_production` wrapper як V2 boundary;
  - `sales.services` і `production.services` переведені на lazy imports
    для legacy compatibility calls (менша жорстка зв'язність на рівні module import graph);
  - додано архітектурний guard-test `orders/tests/test_cutover_boundaries.py`,
    який блокує нові прямі імпорти `apps.orders.*` / `apps.customer_orders.*`
    у V2 app-ах (крім явно дозволених compatibility wrapper файлів);
  - введено V2 namespace `apps.product_inventory` як доменний alias для finished/WIP
    інвентарю поверх `apps.inventory` (без ризикового перейменування app label);
  - після cleanup у non-legacy app-ах залишилися лише очікувані compatibility wrappers:
    `apps.sales.models`, `apps.sales.services`, `apps.production.models`, `apps.production.services`.
  - зафіксовано scope cut для пришвидшення cutover:
    фізичне видалення legacy-колонок/таблиць переноситься в окремий фінальний
    migration-пакет під нову БД (без ризикових руйнівних змін у поточному інкременті).
  - виконано baseline/reset migration history:
    видалено історичні migration chain-и і згенеровано нові initial migration-и для
    поточного стану моделей (`accounts`, `catalog`, `customer_orders`, `inventory`,
    `materials`, `orders`, `warehouses`);
  - відновлено data-seed для default складу у `warehouses.0002_seed_main_warehouse`;
  - для cutover на клон старої БД оновлено migrate-job command на
    `migrate --noinput --fake-initial` (`infra/environments/prod/main.tf`).
- Наступний інкремент: фінальний migration-пакет для нової БД
  (фізичний drop legacy-колонок/таблиць після окремого dry-run на копії прод-даних).
