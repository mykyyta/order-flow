# V2 Model Design Proposal

Це пропозиція цільової схеми даних для V2 (greenfield) з подальшим імпортом даних з legacy БД.

## 1. Цілі

- Прибрати цикли залежностей між `orders`, `customer_orders`, `inventory`.
- Уніфікувати "варіант виробу" в єдину сутність (`ProductVariant`).
- Підтримати multi-warehouse без ускладнення щоденного UI.
- Розділити закупівлі, матеріали і склад матеріалів на окремі bounded contexts.
- Спроєктувати схему так, щоб імпорт legacy даних був простим та контрольованим.

## 2. Принципи дизайну

1. Один контекст = одна апка.
2. Міжконтекстні сценарії тільки через orchestrator (`fulfillment`), не через взаємні виклики
   сервісів.
3. `ProductVariant` є source of truth для ключа складського обліку готового виробу.
4. Складські рухи ведемо через ledger-підхід (`...Movement` + поточний баланс в `...StockRecord`).
5. У коді англійська, у UI українська.
6. Усі сутності з операційною історією мають `created_at` (і де потрібно `updated_at`).
7. У ключових таблицях V2 додаємо `legacy_id` для трасування імпорту.

## 3. Цільова структура апок V2

```
users/              # AUTH_USER_MODEL, налаштування
catalog/            # Product, ProductVariant, бандли, норми матеріалів
sales/              # SalesOrder, SalesOrderLine
production/         # ProductionOrder (cutting/finishing/full), статуси
warehouses/         # Warehouse довідник
product_inventory/  # Готова продукція (Product/FinishedStock*) + WIP (runtime alias to apps.inventory)
materials/          # Material, MaterialColor довідники
procurement/        # Supplier, PurchaseOrder, GoodsReceipt
material_inventory/ # Матеріали на складах: MaterialStock*
fulfillment/        # Orchestration services (без ORM моделей)
notifications/      # Telegram, email, логи нотифікацій
```

---

## 4. Детальний опис моделей

### 4.1 `users`

**Відповідальність:** автентифікація, персональні налаштування, нотифікаційні преференції.

#### `User`
| Поле | Тип | Опис |
|------|-----|------|
| username | CharField | Логін |
| email | EmailField | |
| telegram_id | CharField(unique, null) | Для Telegram нотифікацій |
| theme | CharField | UI тема (light/dark/auto) |
| is_active, is_staff | Boolean | Стандартні Django поля |

#### `UserPreference`
| Поле | Тип | Опис |
|------|-----|------|
| user | OneToOneField(User) | |
| default_warehouse | FK(Warehouse, null) | Дефолтний склад для UI |
| locale | CharField | uk/en |

---

### 4.2 `catalog`

**Відповідальність:** каталог продуктів, варіанти, бандли, норми матеріалів.

#### `Product`
| Поле | Тип | Опис |
|------|-----|------|
| name | CharField(unique) | Назва продукту |
| kind | CharField | `simple` / `bundle` |
| is_sellable | Boolean | Чи можна продавати напряму |
| variant_mode | CharField | `none` / `color` / `material_single` / `material_pair` |
| primary_material | FK(Material, null) | Основний матеріал (для material_* modes) |
| secondary_material | FK(Material, null) | Додатковий матеріал |
| archived_at | DateTime(null) | Soft delete |
| legacy_id | Integer(null, unique) | ID з legacy ProductModel |

**variant_mode пояснення:**
- `none` — продукт без варіантів (наприклад, послуга)
- `color` — варіанти по Color (legacy система)
- `material_single` — варіанти по primary_material_color
- `material_pair` — варіанти по primary + secondary material colors

#### `Color`
| Поле | Тип | Опис |
|------|-----|------|
| name | CharField(unique) | Назва кольору |
| code | Integer(unique) | Код для швидкого вибору |
| availability_status | CharField | `in_stock` / `low_stock` / `out_of_stock` |
| archived_at | DateTime(null) | |
| legacy_id | Integer(null, unique) | |

**Примітка:** Color — legacy система для продуктів з `variant_mode=color`. Нові продукти
використовують MaterialColor.

#### `ProductVariant`
| Поле | Тип | Опис |
|------|-----|------|
| product | FK(Product) | |
| color | FK(Color, null) | Для variant_mode=color |
| primary_material_color | FK(MaterialColor, null) | |
| secondary_material_color | FK(MaterialColor, null) | |
| sku | CharField(null) | SKU для інтеграцій |
| is_active | Boolean | Активний для продажу |
| legacy_id | Integer(null) | Composite key з legacy |

**Constraints:**
- unique_together: (product, color, primary_material_color, secondary_material_color)
- CHECK: NOT (color IS NULL AND primary_material_color IS NULL)
- CHECK: secondary_material_color IS NULL OR primary_material_color IS NOT NULL

#### `ProductComponent`
| Поле | Тип | Опис |
|------|-----|------|
| bundle | FK(Product, kind=bundle) | Бандл |
| component | FK(Product, kind=simple) | Компонент |
| quantity | PositiveInteger | Кількість в бандлі |
| is_primary | Boolean | Головний компонент |
| is_required | Boolean | Обов'язковий компонент |
| group | CharField(null) | Група взаємозаміни |

**Constraints:**
- unique_together: (bundle, component)

**Логіка груп:**
```
is_required=True,  group=NULL    → Обов'язковий, завжди входить
is_required=False, group=NULL    → Опціональний add-on
is_required=True,  group="strap" → Один з групи обов'язковий
is_required=False, group="strap" → Один з групи опціональний
```

#### `BundlePreset`
| Поле | Тип | Опис |
|------|-----|------|
| bundle | FK(Product) | |
| name | CharField | Назва пресету |
| archived_at | DateTime(null) | |

**Constraints:**
- unique_together: (bundle, name)

#### `BundlePresetComponent`
| Поле | Тип | Опис |
|------|-----|------|
| preset | FK(BundlePreset) | |
| component | FK(Product) | |
| primary_material_color | FK(MaterialColor) | |
| secondary_material_color | FK(MaterialColor, null) | |

**Constraints:**
- unique_together: (preset, component)

#### `ProductMaterialNorm`
| Поле | Тип | Опис |
|------|-----|------|
| product | FK(Product, kind=simple) | |
| material | FK(Material) | |
| quantity_per_unit | Decimal | Витрата на одиницю |
| unit | CharField | `pcs` / `m` / `m²` / `g` / `ml` |
| notes | CharField(blank) | |

**Constraints:**
- unique_together: (product, material)

---

### 4.3 `materials`

**Відповідальність:** довідники матеріалів і кольорів.

#### `Material`
| Поле | Тип | Опис |
|------|-----|------|
| name | CharField(unique) | Назва матеріалу |
| archived_at | DateTime(null) | |
| legacy_id | Integer(null, unique) | |

#### `MaterialColor`
| Поле | Тип | Опис |
|------|-----|------|
| material | FK(Material) | |
| name | CharField | Назва кольору |
| code | Integer | Код |
| archived_at | DateTime(null) | |
| legacy_id | Integer(null, unique) | |

**Constraints:**
- unique_together: (material, name)
- unique_together: (material, code)

---

### 4.4 `warehouses`

**Відповідальність:** довідник складів.

#### `Warehouse`
| Поле | Тип | Опис |
|------|-----|------|
| name | CharField | Назва |
| code | CharField(unique) | Код (MAIN, RETAIL, etc.) |
| kind | CharField | `production` / `storage` / `retail` / `transit` |
| is_default_for_production | Boolean | Дефолт для виробництва |
| is_active | Boolean | |

**Constraints:**
- Максимум один активний склад з is_default_for_production=True

**UX принцип:**
- Щоденний UI працює з дефолтним складом автоматично.
- Вибір складу тільки в розширених операціях (переміщення, коригування).

---

### 4.5 `sales`

**Відповідальність:** клієнтські замовлення.

#### `SalesOrder`
| Поле | Тип | Опис |
|------|-----|------|
| source | CharField | `site` / `etsy` / `wholesale` |
| status | CharField | Статус (див. нижче) |
| customer_info | TextField | Контакти клієнта |
| notes | TextField | Внутрішні нотатки |
| created_at | DateTime | |
| updated_at | DateTime | |
| legacy_id | Integer(null, unique) | |

**Статуси SalesOrder:**
```
new → processing → production → ready → shipped → completed
                                    ↘ cancelled
```

#### `SalesOrderLine`
| Поле | Тип | Опис |
|------|-----|------|
| sales_order | FK(SalesOrder) | |
| product_variant | FK(ProductVariant) | Для simple products |
| bundle_preset | FK(BundlePreset, null) | Для bundle з пресетом |
| quantity | PositiveInteger | |
| production_mode | CharField | `auto` / `manual` / `force` |
| production_status | CharField | `pending` / `in_progress` / `done` |

**production_mode:**
- `auto` — використати наявний сток, решту виготовити
- `manual` — не створювати ProductionOrder автоматично
- `force` — завжди виготовляти, ігнорувати сток

#### `SalesOrderLineComponentSelection`
| Поле | Тип | Опис |
|------|-----|------|
| order_line | FK(SalesOrderLine) | |
| component | FK(Product) | Компонент бандла |
| product_variant | FK(ProductVariant) | Обраний варіант компонента |

**Constraints:**
- unique_together: (order_line, component)

---

### 4.6 `production`

**Відповідальність:** виробничі завдання.

#### `ProductionOrder`
| Поле | Тип | Опис |
|------|-----|------|
| product_variant | FK(ProductVariant) | Що виготовляємо |
| kind | CharField | Тип ордера (див. нижче) |
| sales_order_line | FK(SalesOrderLine, null) | Зв'язок з клієнтським замовленням |
| current_status | CharField | Поточний статус |
| embroidery | Boolean | Потрібна вишивка |
| is_urgent | Boolean | Терміново |
| source | CharField(null) | `site` / `etsy` / `wholesale` / null |
| comment | TextField(blank) | Коментар |
| created_at | DateTime | |
| finished_at | DateTime(null) | |
| legacy_id | Integer(null, unique) | |

**kind choices:**
| Kind | Опис | Вхід | Вихід |
|------|------|------|-------|
| `cutting` | Порізка на склад | MaterialStock | WIPStock |
| `finishing` | Доробка з напівфабрикату | WIPStock | FinishedStock |
| `full` | Повний цикл | MaterialStock | FinishedStock |

**Статуси ProductionOrder:**
```
new        → Нове (очікує в черзі)
doing      → Робимо
embroidery → Вишиваємо
deciding   → Рішаємо (потрібне рішення)
on_hold    → Чогось нема (заблоковано)
finished   → Фініш (термінальний)
```

**Дозволені переходи:**
- З будь-якого не-термінального можна перейти в будь-який інший статус
- Виняток: з не-new не можна повернутися в new
- finished — термінальний, без виходу

#### `ProductionOrderStatusHistory`
| Поле | Тип | Опис |
|------|-----|------|
| production_order | FK(ProductionOrder) | |
| new_status | CharField | |
| changed_by | FK(User) | |
| changed_at | DateTime | |

---

### 4.7 `inventory`

**Відповідальність:** склад готової продукції та напівфабрикатів (WIP).

#### Три рівні складського обліку виробів

```
MaterialStock ──(cutting)──→ WIPStock ──(finishing)──→ FinishedStock
   (шкіра)                  (порізано)                 (готовий виріб)
                                ↓
                           scrap (брак)
```

**WIP (Work In Progress)** — напівфабрикати (порізані деталі), які ще не дофінішовані. Матеріал вже
списаний, але готового виробу ще немає. Створюється через `ProductionOrder(kind=cutting)`.

---

#### `FinishedStockRecord`
| Поле | Тип | Опис |
|------|-----|------|
| warehouse | FK(Warehouse) | |
| product_variant | FK(ProductVariant) | |
| quantity | PositiveInteger | Поточний залишок |

**Constraints:**
- unique_together: (warehouse, product_variant)

#### `FinishedStockMovement`
| Поле | Тип | Опис |
|------|-----|------|
| stock_record | FK(FinishedStockRecord) | |
| quantity_change | Integer | +/- кількість |
| reason | CharField | Тип руху |
| related_production_order | FK(ProductionOrder, null) | |
| related_sales_order_line | FK(SalesOrderLine, null) | |
| related_transfer | FK(FinishedStockTransfer, null) | |
| created_by | FK(User) | |
| notes | TextField | |
| created_at | DateTime | |

**reason choices:**
- `production_in` — надходження з виробництва
- `order_out` — відвантаження клієнту
- `transfer_in` — надходження з іншого складу
- `transfer_out` — переміщення на інший склад
- `adjustment_in` — коригування +
- `adjustment_out` — коригування -
- `return_in` — повернення

#### `FinishedStockTransfer`
| Поле | Тип | Опис |
|------|-----|------|
| from_warehouse | FK(Warehouse) | |
| to_warehouse | FK(Warehouse) | |
| status | CharField | `draft` / `in_transit` / `completed` / `cancelled` |
| created_by | FK(User) | |
| notes | TextField | |
| created_at | DateTime | |
| completed_at | DateTime(null) | |

#### `FinishedStockTransferLine`
| Поле | Тип | Опис |
|------|-----|------|
| transfer | FK(FinishedStockTransfer) | |
| product_variant | FK(ProductVariant) | |
| quantity | PositiveInteger | |

---

#### `WIPStockRecord`

**Напівфабрикати** — порізані деталі, що чекають на пошив.

| Поле | Тип | Опис |
|------|-----|------|
| warehouse | FK(Warehouse) | |
| product_variant | FK(ProductVariant) | |
| quantity | PositiveInteger | Кількість комплектів деталей |

**Constraints:**
- unique_together: (warehouse, product_variant)

#### `WIPStockMovement`
| Поле | Тип | Опис |
|------|-----|------|
| stock_record | FK(WIPStockRecord) | |
| quantity_change | Integer | +/- кількість |
| reason | CharField | Тип руху |
| related_production_order | FK(ProductionOrder, null) | Якщо пошив через ProductionOrder |
| created_by | FK(User) | |
| notes | TextField | |
| created_at | DateTime | |

**reason choices:**
- `cutting_in` — порізано (матеріал → WIP)
- `finishing_out` — доробка завершена (WIP → готове)
- `scrap_out` — списано як брак
- `adjustment_in` / `adjustment_out` — коригування

---

### 4.8 `procurement`

**Відповідальність:** постачальники, закупівлі, приходи.

#### `Supplier`
| Поле | Тип | Опис |
|------|-----|------|
| name | CharField(unique) | |
| contact_name | CharField(blank) | |
| phone | CharField(blank) | |
| email | EmailField(blank) | |
| website | URLField(blank) | |
| notes | TextField(blank) | |
| archived_at | DateTime(null) | |
| legacy_id | Integer(null, unique) | |

#### `SupplierOffer`
| Поле | Тип | Опис |
|------|-----|------|
| supplier | FK(Supplier) | |
| material | FK(Material) | |
| material_color | FK(MaterialColor, null) | |
| title | CharField | Назва позиції у постачальника |
| sku | CharField(blank) | Артикул постачальника |
| url | URLField(blank) | |
| unit | CharField | Одиниця |
| price_per_unit | Decimal | |
| currency | CharField | `UAH` / `USD` / `EUR` |
| min_order_quantity | Decimal(null) | |
| lead_time_days | Integer(null) | |
| notes | TextField(blank) | |
| archived_at | DateTime(null) | |

**Constraint:** material_color.material == material (валідація в clean)

#### `PurchaseOrder`
| Поле | Тип | Опис |
|------|-----|------|
| supplier | FK(Supplier) | |
| status | CharField | `draft` / `sent` / `partially_received` / `received` / `cancelled` |
| expected_at | Date(null) | Очікувана дата поставки |
| created_by | FK(User) | |
| notes | TextField(blank) | |
| created_at | DateTime | |
| updated_at | DateTime | |
| legacy_id | Integer(null, unique) | |

#### `PurchaseOrderLine`
| Поле | Тип | Опис |
|------|-----|------|
| purchase_order | FK(PurchaseOrder) | |
| material | FK(Material) | |
| material_color | FK(MaterialColor, null) | |
| quantity | Decimal | Замовлена кількість |
| received_quantity | Decimal | Отримана кількість |
| unit | CharField | |
| unit_price | Decimal | |
| notes | TextField(blank) | |

**Property:** `remaining_quantity = max(quantity - received_quantity, 0)`

#### `GoodsReceipt`
| Поле | Тип | Опис |
|------|-----|------|
| supplier | FK(Supplier) | |
| purchase_order | FK(PurchaseOrder, null) | |
| warehouse | FK(Warehouse) | Склад приймання |
| received_by | FK(User) | |
| notes | TextField(blank) | |
| received_at | DateTime | |

#### `GoodsReceiptLine`
| Поле | Тип | Опис |
|------|-----|------|
| receipt | FK(GoodsReceipt) | |
| purchase_order_line | FK(PurchaseOrderLine, null) | |
| material | FK(Material) | |
| material_color | FK(MaterialColor, null) | |
| quantity | Decimal | |
| unit | CharField | |
| unit_cost | Decimal | |
| notes | TextField(blank) | |

---

### 4.9 `material_inventory`

**Відповідальність:** залишки матеріалів на складах.

#### `MaterialStockRecord`
| Поле | Тип | Опис |
|------|-----|------|
| warehouse | FK(Warehouse) | |
| material | FK(Material) | |
| material_color | FK(MaterialColor, null) | |
| unit | CharField | |
| quantity | Decimal | |

**Constraints:**
- unique_together: (warehouse, material, unit) for material_color IS NULL
- unique_together: (warehouse, material, material_color, unit) for material_color IS NOT NULL

#### `MaterialStockMovement`
| Поле | Тип | Опис |
|------|-----|------|
| stock_record | FK(MaterialStockRecord) | |
| quantity_change | Decimal | |
| reason | CharField | |
| related_purchase_order_line | FK(PurchaseOrderLine, null) | |
| related_receipt_line | FK(GoodsReceiptLine, null) | |
| related_production_order | FK(ProductionOrder, null) | |
| related_transfer | FK(MaterialStockTransfer, null) | |
| created_by | FK(User) | |
| notes | TextField | |
| created_at | DateTime | |

**reason choices:**
- `purchase_in` — надходження від постачальника
- `production_out` — списання на виробництво
- `transfer_in` / `transfer_out` — міжскладські
- `adjustment_in` / `adjustment_out` — коригування
- `return_in` — повернення

#### `MaterialStockTransfer`
| Поле | Тип | Опис |
|------|-----|------|
| from_warehouse | FK(Warehouse) | |
| to_warehouse | FK(Warehouse) | |
| status | CharField | `draft` / `in_transit` / `completed` / `cancelled` |
| created_by | FK(User) | |
| notes | TextField | |
| created_at | DateTime | |
| completed_at | DateTime(null) | |

#### `MaterialStockTransferLine`
| Поле | Тип | Опис |
|------|-----|------|
| transfer | FK(MaterialStockTransfer) | |
| material | FK(Material) | |
| material_color | FK(MaterialColor, null) | |
| quantity | Decimal | |
| unit | CharField | |

---

### 4.10 `notifications`

**Відповідальність:** логування нотифікацій, запобігання дублікатам.

#### `NotificationLog`
| Поле | Тип | Опис |
|------|-----|------|
| user | FK(User) | |
| channel | CharField | `telegram` / `email` |
| event_type | CharField | `production_order_created` / `production_order_finished` / ... |
| related_production_order | FK(ProductionOrder, null) | |
| related_sales_order | FK(SalesOrder, null) | |
| sent_at | DateTime | |

**Constraints:**
- unique_together: (user, channel, event_type, related_production_order) — запобігає дублям

---

### 4.11 `fulfillment`

**Відповідальність:** orchestration use-cases між контекстами. Без ORM моделей, тільки сервіси.

**Ключові сервіси:**

#### `create_sales_order()`
1. Створює `SalesOrder` + `SalesOrderLine`
2. Для бандлів зберігає `SalesOrderLineComponentSelection`
3. Якщо `create_production_orders=True`:
   - Викликає `create_production_orders_for_sales_order()`
4. Синхронізує статуси

#### `receive_purchase_order_line(po_line, quantity, warehouse, user)`
1. Створює `GoodsReceipt` + `GoodsReceiptLine`
2. Оновлює `po_line.received_quantity`
3. Додає в сток: `MaterialStockMovement(reason=purchase_in)`
4. Оновлює статус `PurchaseOrder`

#### `complete_production_order(production_order, user)`
Завершити виробниче завдання. Поведінка залежить від `kind`:

**kind=CUTTING** (порізка на склад):
1. Списує матеріали: `MaterialStockMovement(reason=production_out)`
2. Додає в WIP: `WIPStockMovement(reason=cutting_in)`
3. Змінює статус на `finished`

**kind=FINISHING** (доробка з WIP):
1. Забирає з WIP: `WIPStockMovement(reason=finishing_out)`
2. Додає в готові: `FinishedStockMovement(reason=production_in)`
3. Змінює статус на `finished`
4. Синхронізує статуси SalesOrder (якщо є)

**kind=FULL** (повний цикл):
1. Списує матеріали: `MaterialStockMovement(reason=production_out)`
2. Додає в готові: `FinishedStockMovement(reason=production_in)`
3. Змінює статус на `finished`
4. Синхронізує статуси SalesOrder (якщо є)

**Спільне для всіх:**
- Створює `ProductionOrderStatusHistory`
- Надсилає нотифікацію (поза транзакцією)

#### `scrap_wip(product_variant, quantity, warehouse, user, notes)`
Списати брак з WIP:
1. Списує з WIP: `WIPStockMovement(reason=scrap_out)`
2. Матеріали вже були списані при cutting — додаткових дій не потрібно

#### `create_production_orders_for_sales_order(sales_order, user)`
Створити виробничі ордери для клієнтського замовлення:
1. Для кожної позиції перевіряє наявність в FinishedStock
2. Якщо є готове — бере зі складу
3. Якщо є в WIP — створює `ProductionOrder(kind=finishing)`
4. Якщо немає нічого — створює `ProductionOrder(kind=full)`

#### `reserve_stock_for_order()` (майбутнє)
- Резервування стоку для SalesOrder без негайного списання

---

## 5. Правила залежностей між апками

```
                    ┌─────────────────────────────────────────┐
                    │            fulfillment                  │
                    │        (orchestration layer)            │
                    └─────────────────────────────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          │                           │                           │
          ▼                           ▼                           ▼
    ┌──────────┐              ┌────────────┐              ┌────────────────┐
    │  sales   │              │ production │              │   inventory    │
    └──────────┘              └────────────┘              └────────────────┘
          │                         │                           │
          │                         │                           │
          ▼                         ▼                           ▼
    ┌──────────┐              ┌────────────┐              ┌────────────────┐
    │ catalog  │◄─────────────│ warehouses │◄─────────────│ material_inv.  │
    └──────────┘              └────────────┘              └────────────────┘
          │                                                     │
          ▼                                                     ▼
    ┌──────────┐                                         ┌────────────────┐
    │materials │◄────────────────────────────────────────│  procurement   │
    └──────────┘                                         └────────────────┘
```

**Правила:**
1. `sales`, `production`, `inventory`, `procurement`, `material_inventory` НЕ викликають одна одну.
2. Міжконтекстні сценарії — тільки через `fulfillment`.
3. `catalog`, `materials`, `warehouses`, `users` — upstream довідники.
4. Нотифікації відправляються ПОЗА критичними транзакціями.

---

## 6. Мапування Legacy → V2

| Legacy | V2 | Примітки |
|--------|-----|----------|
| `catalog.ProductModel` | `catalog.Product` | `is_bundle` → `kind` |
| `catalog.Color` | `catalog.Color` | Без змін |
| `catalog.BundleComponent` | `catalog.ProductComponent` | + `is_required`, `group` |
| `catalog.BundleColorMapping` | — | Видалено (вільний вибір компонентів) |
| `catalog.BundlePreset` | `catalog.BundlePreset` | Без змін |
| `catalog.BundlePresetComponent` | `catalog.BundlePresetComponent` | Без змін |
| — | `catalog.ProductVariant` | Нова модель (генерується при імпорті) |
| `materials.Material` | `materials.Material` | Без змін |
| `materials.MaterialColor` | `materials.MaterialColor` | Без змін |
| `materials.ProductMaterial` | `catalog.ProductMaterialNorm` | Перейменовано, перенесено в catalog |
| `materials.Supplier` | `procurement.Supplier` | Перенесено |
| `materials.SupplierMaterialOffer` | `procurement.SupplierOffer` | Перенесено |
| `materials.PurchaseOrder` | `procurement.PurchaseOrder` | Перенесено |
| `materials.PurchaseOrderLine` | `procurement.PurchaseOrderLine` | Перенесено |
| `materials.GoodsReceipt` | `procurement.GoodsReceipt` | + `warehouse` |
| `materials.GoodsReceiptLine` | `procurement.GoodsReceiptLine` | Без змін |
| `materials.MaterialStockRecord` | `material_inventory.MaterialStockRecord` | + `warehouse` |
| `materials.MaterialMovement` | `material_inventory.MaterialStockMovement` | Перейменовано |
| `orders.CustomUser` | `users.User` | Перенесено |
| `orders.Order` | `production.ProductionOrder` | + `product_variant`, `kind`, `source` |
| `orders.OrderStatusHistory` | `production.ProductionOrderStatusHistory` | Перейменовано |
| `orders.DelayedNotificationLog` | `notifications.NotificationLog` | Узагальнено |
| `customer_orders.CustomerOrder` | `sales.SalesOrder` | Перейменовано |
| `customer_orders.CustomerOrderLine` | `sales.SalesOrderLine` | + `product_variant` |
| `customer_orders.CustomerOrderLineComponent` | `sales.SalesOrderLineComponentSelection` | + `product_variant` |
| `inventory.StockRecord` | `inventory.FinishedStockRecord` | + `warehouse`, `product_variant` |
| `inventory.StockMovement` | `inventory.FinishedStockMovement` | Перейменовано |

---

## 7. Генерація ProductVariant при імпорті

Алгоритм для кожної унікальної комбінації з legacy:

```python
# Збираємо унікальні комбінації з:
# - Order (model, color, primary_material_color, secondary_material_color)
# - CustomerOrderLine (те саме)
# - CustomerOrderLineComponent (component as model, ...)
# - StockRecord (product_model, color, primary_material_color, secondary_material_color)

unique_variants = set()

for order in Order.objects.all():
    unique_variants.add((
        order.model_id,
        order.color_id,
        order.primary_material_color_id,
        order.secondary_material_color_id,
    ))

# ... аналогічно для інших моделей

for (product_id, color_id, pmc_id, smc_id) in unique_variants:
    ProductVariant.objects.get_or_create(
        product_id=product_id,
        color_id=color_id,
        primary_material_color_id=pmc_id,
        secondary_material_color_id=smc_id,
        defaults={"is_active": True},
    )
```

---

## 8. Імпорт даних із legacy

### Етапи імпорту

1. **Довідники (незалежні)**
   - User, Material, MaterialColor, Color, Warehouse (створити дефолтний)
   - Supplier

2. **Каталог**
   - Product (з ProductModel)
   - ProductComponent (з BundleComponent + нові поля)
   - BundlePreset, BundlePresetComponent
   - ProductMaterialNorm (з ProductMaterial)

3. **Генерація варіантів**
   - Сканування всіх legacy таблиць
   - Створення ProductVariant

4. **Документи**
   - SalesOrder, SalesOrderLine, SalesOrderLineComponentSelection
   - ProductionOrder, ProductionOrderStatusHistory
   - PurchaseOrder, PurchaseOrderLine
   - GoodsReceipt, GoodsReceiptLine

5. **Складські залишки**
   - FinishedStockRecord, FinishedStockMovement
   - MaterialStockRecord, MaterialStockMovement

### Команда імпорту

```bash
python manage.py import_legacy --dry-run    # Перевірка без змін
python manage.py import_legacy --apply       # Виконання імпорту
python manage.py import_legacy --verify      # Верифікація після імпорту
```

### Верифікація

- [ ] Кількість Products == кількість ProductModel
- [ ] Кількість SalesOrders == кількість CustomerOrders
- [ ] Кількість ProductionOrders == кількість Orders
- [ ] Сума залишків FinishedStockRecord == сума StockRecord
- [ ] Сума залишків MaterialStockRecord == сума materials.MaterialStockRecord
- [ ] Всі статуси коректно замаплені

---

## 9. Ризики і контроль

| Ризик | Контроль |
|-------|----------|
| Неправильне мапування статусів | Таблиця відповідності + тести |
| Дублікати варіантів | unique constraint + idempotent import |
| Розходження балансів | Пост-імпорт звірка агрегатів |
| Втрата зв'язків | legacy_id на всіх ключових моделях |
| Проблеми з FK ordering | Правильна послідовність імпорту |

---

## 10. Рекомендований порядок впровадження

### Фаза 1: Підготовка
1. [ ] Затвердити цей blueprint
2. [ ] Створити V2 Django project skeleton
3. [ ] Налаштувати dual-database config (legacy read-only + v2)

### Фаза 2: Моделі
4. [ ] users app
5. [ ] materials app (тільки довідники)
6. [ ] warehouses app
7. [ ] catalog app (Product, ProductVariant, ProductComponent, etc.)
8. [ ] procurement app
9. [ ] material_inventory app
10. [ ] sales app
11. [ ] production app
12. [ ] inventory app (FinishedStock + WIPStock)
13. [ ] notifications app

### Фаза 3: Fulfillment
14. [ ] fulfillment services
15. [ ] Integration tests для key use-cases

### Фаза 4: Імпорт
16. [ ] import_legacy management command
17. [ ] Dry-run на копії production
18. [ ] Верифікація та фікси

### Фаза 5: Cutover
19. [ ] UI для V2
20. [ ] Фінальний імпорт
21. [ ] Переключення на V2

---

## 11. Відкриті питання

1. **Резервування стоку** — реалізувати зараз чи відкласти?
2. **Повернення від клієнта** — окрема апка чи інтегрувати в sales/inventory?
3. **Pricing на SalesOrderLine** — потрібно для аналітики?
4. **Batch production** — групове виробництво в майбутньому?

---

## 12. Потоки виробництва

### Через ProductionOrder.kind

```
┌─────────────────────────────────────────────────────────────────┐
│                     ProductionOrder                              │
├─────────────────────────────────────────────────────────────────┤
│  kind=CUTTING     MaterialStock ───────────────→ WIPStock       │
│  kind=FINISHING   WIPStock ────────────────────→ FinishedStock  │
│  kind=FULL        MaterialStock ───────────────→ FinishedStock  │
└─────────────────────────────────────────────────────────────────┘
```

### Make-to-Stock (на склад)

**Крок 1: Порізати на склад**
```
ProductionOrder(kind=cutting) → finished → MaterialStock(-), WIPStock(+)
```

**Крок 2: Дофінішувати (коли потрібно)**
```
ProductionOrder(kind=finishing) → finished → WIPStock(-), FinishedStock(+)
```

### Make-to-Order (на замовлення)

```
SalesOrder
    ↓
create_production_orders_for_sales_order()
    ↓
    ├── Є в FinishedStock? → Бере зі складу, ордер не потрібен
    ├── Є в WIPStock? → ProductionOrder(kind=finishing)
    └── Нічого немає? → ProductionOrder(kind=full)
```

### Звіти для контролю

| Звіт | Що показує |
|------|------------|
| WIP залишки | Скільки порізано, чекає доробки |
| WIP aging | Як довго лежить порізане (заморожені матеріали) |
| Conversion rate | WIP → Finished за період |
| Scrap rate | Відсоток браку |
