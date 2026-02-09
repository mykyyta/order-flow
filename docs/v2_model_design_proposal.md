# V2 Model Design Proposal

Це пропозиція цільової схеми даних для V2 (greenfield) з подальшим імпортом даних з legacy БД.

## 1. Цілі

- Прибрати цикли залежностей між `orders`, `customer_orders`, `inventory`.
- Уніфікувати "варіант виробу" в єдину сутність.
- Підтримати multi-warehouse без ускладнення щоденного UI.
- Розділити закупівлі, матеріали і склад матеріалів на окремі bounded contexts.
- Спроєктувати схему так, щоб імпорт legacy даних був простим та контрольованим.

## 2. Принципи дизайну

1. Один контекст = одна апка.
2. Міжконтекстні сценарії тільки через orchestrator (`fulfillment`), не через взаємні виклики сервісів.
3. `ProductVariant` є source of truth для ключа складського обліку готового виробу.
4. Складські рухи ведемо через ledger-підхід (`...Movement` + поточний баланс в `...StockRecord`).
5. У коді англійська, у UI українська.
6. Усі сутності з операційною історією мають `created_at` (і де потрібно `updated_at`).
7. У ключових таблицях V2 додаємо `legacy_id` для трасування імпорту.

## 3. Цільова структура апок V2

### `users`

Відповідальність:
- `AUTH_USER_MODEL`
- персональні налаштування
- нотифікаційні налаштування

Моделі:
- `User`
- `UserPreference`
- `NotificationPreference`

### `catalog`

Відповідальність:
- каталог продуктів
- варіанти продуктів
- бандли та пресети
- норми витрат матеріалів на продукт

Моделі:
- `Product`
- `ProductVariant`
- `ProductComponent`
- `BundlePreset`
- `BundlePresetComponent`
- `ProductMaterialNorm`

### `sales`

Відповідальність:
- клієнтські замовлення
- позиції замовлення
- кастомні вибори компонентів для бандлів

Моделі:
- `SalesOrder`
- `SalesOrderLine`
- `SalesOrderLineComponentSelection`

### `production`

Відповідальність:
- виробничі завдання
- статусний workflow та історія статусів

Моделі:
- `WorkOrder`
- `WorkOrderStatusHistory`

### `warehouses`

Відповідальність:
- довідник складів
- тип складу і дефолтний виробничий склад

Моделі:
- `Warehouse`

### `inventory`

Відповідальність:
- склад готової продукції по варіантах
- рухи готової продукції
- міжскладські переміщення готової продукції

Моделі:
- `FinishedStockRecord`
- `FinishedStockMovement`
- `FinishedStockTransfer`
- `FinishedStockTransferLine`

### `materials`

Відповідальність:
- довідник матеріалів і кольорів матеріалів

Моделі:
- `Material`
- `MaterialColor`

### `procurement`

Відповідальність:
- постачальники
- оффери
- закупівельні документи
- приходи

Моделі:
- `Supplier`
- `SupplierOffer`
- `PurchaseOrder`
- `PurchaseOrderLine`
- `GoodsReceipt`
- `GoodsReceiptLine`

### `material_inventory`

Відповідальність:
- залишки матеріалів по складах
- рухи матеріалів
- міжскладські переміщення матеріалів

Моделі:
- `MaterialStockRecord`
- `MaterialStockMovement`
- `MaterialStockTransfer`
- `MaterialStockTransferLine`

### `fulfillment`

Відповідальність:
- orchestration use-cases між `sales`, `production`, `inventory`, `procurement`,
  `material_inventory`

Примітка:
- без ORM-моделей, тільки application services.

## 4. Правила залежностей між апками

1. `sales`, `production`, `inventory`, `procurement`, `material_inventory` не викликають одна одну
   напряму.
2. Міжконтекстні сценарії виконуються тільки через `fulfillment`.
3. `catalog`, `materials`, `warehouses`, `users` є upstream-довідниками.
4. Події/нотифікації (Telegram та інші інтеграції) не відправляються всередині критичних транзакцій
   створення/зміни стану.

## 5. Product та ProductVariant (ключова зміна)

### `Product`

Ключові поля:
- `name`
- `kind`: `simple | bundle`
- `category`: `bag | accessory | case | strap | other`
- `is_sellable`: чи можна додавати товар напряму в `SalesOrderLine`
- `variant_mode`: `none | color | material_single | material_pair`
- `archived_at`

Правила:
- `kind=bundle` може бути `is_sellable=True` (продаємо набір) або `False` (службовий шаблон).
- `kind=simple` і `is_sellable=False` означає "тільки компонент бандла".

### `ProductVariant`

Ключові поля:
- `product` (FK)
- `color` (nullable FK)
- `primary_material_color` (nullable FK)
- `secondary_material_color` (nullable FK)
- `sku` (nullable)
- `is_active`

Правила:
- унікальність комбінації (`product`, `color`, `primary_material_color`, `secondary_material_color`).
- заборонений "порожній" варіант без `color` і без `primary_material_color`.
- `secondary_material_color` не може бути заповнений без `primary_material_color`.

### Використання `ProductVariant`

Наступні моделі мають зберігати `product_variant_id`:
- `sales.SalesOrderLine`
- `production.WorkOrder`
- `inventory.FinishedStockRecord`

Це прибирає дублювання 4 полів (`product + color + primary + secondary`) у кількох таблицях.

## 6. Бандли

### `ProductComponent`

Призначення:
- опис складу бандла (які `simple` товари входять до `bundle`)

Ключові поля:
- `bundle` (FK на `Product` з `kind=bundle`)
- `component` (FK на `Product` з `kind=simple`)
- `quantity`
- `is_primary`

### `BundlePreset` і `BundlePresetComponent`

Призначення:
- готові пресети кольорів/компонентів для швидкого створення позиції замовлення.

## 7. Склади (2-3 склади, але чистий UI)

### `Warehouse`

Ключові поля:
- `name`
- `code` (unique)
- `kind`: `production | storage | retail | transit`
- `is_default_for_production`
- `is_active`

Правила:
- має бути не більше одного активного складу з `is_default_for_production=True`.

### UX принцип

- Щоденний виробничий UI працює з дефолтним виробничим складом автоматично.
- Вибір складу показується лише в "розширених" операціях:
  переміщення, ручні коригування, приймання в нетиповий склад.

## 8. Документи і стани

### `SalesOrder`

Стан замовлення клієнта:
- `new | processing | production | ready | shipped | completed | cancelled`

### `WorkOrder`

Стан виробництва:
- окрема status machine у `production` (з історією `WorkOrderStatusHistory`).

### `PurchaseOrder`

Стан закупівлі:
- `draft | sent | partially_received | received | cancelled`

## 9. Складський облік

### Готова продукція (`inventory`)

- `FinishedStockRecord` з унікальністю: `warehouse + product_variant`.
- `FinishedStockMovement` для аудиту (`reason`, `quantity_change`, `related_*`).

### Матеріали (`material_inventory`)

- `MaterialStockRecord` з унікальністю:
  - `warehouse + material + unit` для `material_color IS NULL`
  - `warehouse + material + material_color + unit` для кольорового обліку
- `MaterialStockMovement` з типами причин (`purchase_in`, `production_out`, `adjustment`, `transfer`).

## 10. Оркестрація (приклади use-cases у `fulfillment`)

1. `create_sales_order`:
   - створює `SalesOrder`/`SalesOrderLine`
   - перевіряє доступний сток
   - створює відсутні `WorkOrder`

2. `complete_work_order`:
   - змінює статус `WorkOrder`
   - робить `FinishedStockMovement` (`production_in`)
   - синхронізує статуси `SalesOrderLine`/`SalesOrder`

3. `receive_purchase_order_line`:
   - створює `GoodsReceiptLine`
   - робить `MaterialStockMovement` (`purchase_in`)
   - оновлює статус `PurchaseOrder`

## 11. Перейменування з legacy

- `orders.Order` -> `production.WorkOrder`
- `customer_orders.CustomerOrder` -> `sales.SalesOrder`
- `customer_orders.CustomerOrderLine` -> `sales.SalesOrderLine`
- `inventory.StockRecord` -> `inventory.FinishedStockRecord`
- `inventory.StockMovement` -> `inventory.FinishedStockMovement`
- `orders.CustomUser` -> `users.User`

## 12. Імпорт даних із legacy

1. Legacy БД відкриваємо у read-only режимі.
2. Пишемо idempotent команду `import_legacy_data` з режимами `--dry-run` і `--apply`.
3. Для ключових сутностей зберігаємо `legacy_id`.
4. Перевірки після імпорту:
   - кількість замовлень та позицій
   - кількість виробничих завдань
   - залишки по складах
   - консистентність статусів

## 13. Ризики і контроль

Ризики:
- неправильне мапування legacy статусів,
- дублікати варіантів при імпорті,
- розходження балансів після трансферів.

Контроль:
- обов'язковий `--dry-run` з деталізованим звітом,
- інтеграційні тести імпорту на копії legacy,
- пост-імпорт звірки агрегатів.

## 14. Рекомендований порядок впровадження

1. Затвердити цей blueprint як target state.
2. Створити skeleton апок і базові моделі V2.
3. Реалізувати `ProductVariant` + складські моделі з `warehouse`.
4. Реалізувати `fulfillment` use-cases.
5. Реалізувати і прогнати імпорт legacy.
6. Провести cutover на V2 БД.
