# V2 Cleanup Recommendations

Рекомендації для чистої, масштабованої кодової бази після V2 рефакторингу.

## Пріоритети

- 🔴 **Зробити зараз** — блокує чистий код або створює технічний борг
- 🟡 **Зробити при нагоді** — покращує архітектуру
- 📘 **Довідка** — знадобиться при великих навантаженнях


---

## 🔴 Зробити зараз

### 1. Видалити legacy apps з репозиторію

`apps/orders/` та `apps/customer_orders/` видалені з runtime, але файли залишились.

```bash
git rm -r src/apps/orders/
git rm -r src/apps/customer_orders/
```


### 2. Видалити дублювання legacy полів

`SalesOrderLine` і `ProductionOrder` мають і `product_variant`, і legacy поля:

```python
# Залишити (V2 canonical key)
product_variant = FK(ProductVariant)

# Видалити (legacy дублювання)
product_model = FK(ProductModel)
color = FK(Color)
primary_material_color = FK(MaterialColor)
secondary_material_color = FK(MaterialColor)
```

Також видалити `product_variant_matches_legacy_fields()` валідацію — вона більше не потрібна.


### 3. Зробити `warehouse_id` NOT NULL

Поля `StockRecord.warehouse`, `MaterialStockRecord.warehouse`, `GoodsReceipt.warehouse`
мають `null=True` як перехідний стан.

1. Міграція: backfill null → MAIN
2. Змінити на `null=False`
3. Видалити `resolve_warehouse_id()` fallback


### 4. Закомітити untracked files

В `apps/production/` є untracked файли:
- `forms.py`, `views/`, `urls.py`
- `legacy_import.py`, `legacy_import_mappings.py`
- `management/commands/`
- `telegram_bot.py`, `notifications.py`

Додати потрібне, видалити зайве.


### 5. Видалити re-export apps

`procurement`, `material_inventory`, `product_inventory` — це тільки re-export моделей.
Створюють ілюзію окремих bounded contexts без реальної ізоляції.

**Варіант A (рекомендований):** видалити apps, імпортувати напряму:
```python
# Було
from apps.procurement.models import Supplier
from apps.material_inventory.models import MaterialStockRecord

# Стало
from apps.materials.models import Supplier, MaterialStockRecord
```

**Варіант B:** залишити як namespace aliases, але:
- Видалити дублювання в `INSTALLED_APPS`
- Задокументувати що це aliases, а не окремі таблиці


### 6. Naming refactor

Повна уніфікація naming для чистої кодової бази.

#### 6.1 Структура apps (фінальна)

```
catalog/       → Product, Variant, Color, Bundle*
materials/     → Material, MaterialColor, BOM, Supplier, PurchaseOrder*,
                 MaterialStock, MaterialStockMovement, MaterialStockTransfer*
inventory/     → ProductStock, ProductStockMovement, WIPStock,
                 WIPStockMovement, ProductStockTransfer*
sales/         → SalesOrder, SalesOrderLine
production/    → ProductionOrder, ProductionOrderStatusHistory
warehouses/    → Warehouse
accounts/      → User
fulfillment/   → (no models, orchestration only)
```

**Видалити fake re-export apps:**
- `procurement/` → імпортувати з `materials`
- `material_inventory/` → імпортувати з `materials`
- `product_inventory/` → імпортувати з `inventory`

#### 6.2 Перейменування моделей

| App | Було | Стало |
|-----|------|-------|
| `catalog` | `ProductModel` | `Product` |
| `catalog` | `ProductVariant` | `Variant` |
| `catalog` | `ProductMaterial` | `BOM` |
| `inventory` | `StockRecord` | `ProductStock` |
| `inventory` | `StockMovement` | `ProductStockMovement` |
| `inventory` | `FinishedStockTransfer` | `ProductStockTransfer` |
| `inventory` | `FinishedStockTransferLine` | `ProductStockTransferLine` |
| `materials` | `MaterialStockRecord` | `MaterialStock` |
| `materials` | `MaterialMovement` | `MaterialStockMovement` |
| `accounts` | `CustomUser` | `User` |

**Видалити всі aliases:**
```python
# ❌ Видалити
FinishedStockRecord = StockRecord
Order = ProductionOrder
SupplierOffer = SupplierMaterialOffer
```

#### 6.3 Перейменування полів

**FK поля — єдиний патерн `{model_name}`:**

| Модель | Було | Стало |
|--------|------|-------|
| `ProductionOrder` | `model` | `product` |
| `ProductionOrder` | `customer_order_line` | `sales_order_line` |
| `SalesOrderLine` | `customer_order` (property) | видалити alias |
| `inventory/*` | `related_customer_order_line` | `sales_order_line` |
| `*` | `product_model` | `product` |
| `*` | `product_variant` | `variant` |

**Status поля — просто `status`:**

| Модель | Було | Стало |
|--------|------|-------|
| `ProductionOrder` | `current_status` | `status` |
| `Color` | `availability_status` | `status` |

**Boolean поля — `is_*` prefix:**

| Модель | Було | Стало |
|--------|------|-------|
| `ProductionOrder` | `urgent` | `is_urgent` |
| `ProductionOrder` | `embroidery` | `is_embroidery` |
| `ProductionOrder` | `etsy` | `is_etsy` |

#### 6.4 Conventions (для нового коду)

| Аспект | Конвенція | Приклад |
|--------|-----------|---------|
| FK naming | `{model_name}` (snake_case, без `_id`) | `warehouse`, `variant`, `product` |
| Status | `status` | `status = CharField(choices=...)` |
| Timestamps | `*_at` + auto_now | `created_at`, `updated_at`, `finished_at` |
| Boolean | `is_*` prefix | `is_active`, `is_urgent`, `is_bundle` |
| Quantity | `quantity` (не qty/amount/count) | `quantity`, `quantity_change` |

#### 6.5 Міграційна стратегія

Нова БД → міграції з нуля:

```bash
# 1. Видалити всі міграції (крім __init__.py)
find src/apps -path "*/migrations/*.py" -not -name "__init__.py" -delete

# 2. Перейменувати моделі та поля в models.py

# 3. Оновити imports в services, views, tests

# 4. Згенерувати fresh initial migrations
python manage.py makemigrations

# 5. Застосувати
python manage.py migrate

# 6. Прогнати тести
pytest
```

Без RenameModel/RenameField — просто нові таблиці з правильними назвами.


### 7. Бізнес-моделі

Критичні для повноцінної роботи системи.

#### 7.1 Ціна продукту

```python
# catalog/models.py
class Product:
    ...
    price = DecimalField(max_digits=10, decimal_places=2)
    currency = CharField(max_length=3, default='UAH')
    cost_price = DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
```

- `price` — роздрібна ціна для клієнтів
- `cost_price` — собівартість для аналітики маржі (optional)

#### 7.2 Модель клієнта

```python
# sales/models.py
class Customer:
    name = CharField(max_length=200)
    phone = CharField(max_length=20, blank=True)
    email = EmailField(blank=True)
    instagram = CharField(max_length=100, blank=True)
    notes = TextField(blank=True)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sales_customer'
```

Оновити `SalesOrder`:
```python
class SalesOrder:
    customer = ForeignKey(Customer, on_delete=PROTECT, null=True, blank=True)
    customer_info = TextField(blank=True)  # fallback для швидких/анонімних
```

#### 7.3 Статус оплати

```python
# sales/models.py
class PaymentStatus(models.TextChoices):
    PENDING = 'pending', 'Очікує'
    PARTIAL = 'partial', 'Частково'
    PAID = 'paid', 'Оплачено'

class PaymentMethod(models.TextChoices):
    CASH = 'cash', 'Готівка'
    CARD = 'card', 'Карта'
    TRANSFER = 'transfer', 'Переказ'
    OTHER = 'other', 'Інше'

class SalesOrder:
    ...
    payment_status = CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    payment_method = CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        blank=True,
    )
    paid_amount = DecimalField(max_digits=10, decimal_places=2, default=0)
```

Логіка:
- `total_amount` — рахується з order lines (variant.price * quantity)
- `paid_amount` — скільки вже сплачено
- `payment_status` — автоматично оновлюється при зміні `paid_amount`


---

## 🟡 Зробити при нагоді

### 8. Розв'язати circular dependencies

Поточний стан (працює через `TYPE_CHECKING`):
```
sales.services → production.services → inventory.services
                        ↑___________________________|
```

**Рішення:** dependency inversion через callbacks або protocols:

```python
# inventory/services.py
def complete_production(
    order_id: int,
    on_stock_added: Callable[[int, int], None] | None = None
) -> None:
    ...
    if on_stock_added:
        on_stock_added(variant_id, quantity)
```

Або винести orchestration в `fulfillment` (вже частково зроблено).


### 9. Explicit warehouse context

Замість implicit fallback на MAIN, вимагати warehouse_id явно:

```python
# Було
def get_stock_quantity(product_variant_id: int, warehouse_id: int | None = None):
    warehouse_id = resolve_warehouse_id(warehouse_id)  # fallback to MAIN
    ...

# Стало
def get_stock_quantity(product_variant_id: int, warehouse_id: int):
    ...
```

Caller відповідає за вибір складу.


### 10. Query managers для повторюваних запитів

Якщо query повторюється 3+ рази — винести в manager:

```python
class StockRecordManager(models.Manager):
    def for_warehouse(self, warehouse_id: int):
        return self.filter(warehouse_id=warehouse_id)

    def with_positive_quantity(self):
        return self.filter(quantity__gt=0)

    def for_variant(self, variant_id: int):
        return self.filter(product_variant_id=variant_id)
```


### 11. Domain types замість primitives

Для критичних domain concepts використовувати NewType або dataclasses:

```python
from typing import NewType

VariantId = NewType('VariantId', int)
WarehouseId = NewType('WarehouseId', int)
Quantity = NewType('Quantity', int)

def add_to_stock(
    variant_id: VariantId,
    warehouse_id: WarehouseId,
    quantity: Quantity,
) -> None:
    ...
```

Допомагає IDE та type checker ловити помилки.


---

## 📘 Довідка на майбутнє

Ці патерни знадобляться при значному зростанні навантаження (10k+ операцій/день,
кілька розробників, кілька складів).

### Event-driven stock movements

**Коли потрібно:** синхронні stock operations блокують requests > 100ms.

**Рішення:** Celery/Django-Q tasks для async processing:
```python
# Замість прямого виклику
inventory.add_to_stock(variant_id, warehouse_id, qty)

# Event + async handler
events.emit('production.completed', {'order_id': order_id})

# Handler (async worker)
@task
def on_production_completed(order_id: int):
    order = ProductionOrder.objects.get(id=order_id)
    inventory.add_to_stock(...)
```


### Read models для dashboards

**Коли потрібно:** dashboard queries > 500ms, складні JOINs гальмують.

**Рішення:** денормалізовані таблиці або materialized views:
```python
class DashboardStockSummary(models.Model):
    """Денормалізована таблиця для швидкого читання."""
    warehouse = FK(Warehouse)
    total_variants = PositiveIntegerField()
    total_quantity = PositiveIntegerField()
    last_movement_at = DateTimeField()

    class Meta:
        managed = False  # Materialized view
```


### Query caching

**Коли потрібно:** hot queries (stock lookup) викликаються > 100 разів/хвилину.

**Рішення:** cache layer з invalidation:
```python
from django.core.cache import cache

def get_stock_quantity(variant_id: int, warehouse_id: int) -> int:
    cache_key = f'stock:{warehouse_id}:{variant_id}'
    qty = cache.get(cache_key)
    if qty is None:
        qty = StockRecord.objects.filter(...).values_list('quantity', flat=True).first() or 0
        cache.set(cache_key, qty, timeout=60)
    return qty

# Invalidation при зміні
@receiver(post_save, sender=StockMovement)
def invalidate_stock_cache(sender, instance, **kwargs):
    cache.delete(f'stock:{instance.warehouse_id}:{instance.product_variant_id}')
```


### Repository pattern

**Коли потрібно:** тести потребують mock data access, або міграція на іншу БД.

**Рішення:** абстракція над ORM:
```python
class StockRepository(Protocol):
    def get_quantity(self, variant_id: int, warehouse_id: int) -> int: ...
    def add(self, variant_id: int, warehouse_id: int, qty: int) -> None: ...

class DjangoStockRepository:
    def get_quantity(self, variant_id: int, warehouse_id: int) -> int:
        return StockRecord.objects.filter(...).first()?.quantity or 0
```


### API versioning

**Коли потрібно:** зовнішні клієнти (mobile app, integrations) залежать від API.

**Рішення:** DTO layer між ORM і API:
```python
@dataclass
class StockDTO:
    variant_id: int
    warehouse_id: int
    quantity: int
    last_updated: datetime

def to_dto(record: StockRecord) -> StockDTO:
    return StockDTO(
        variant_id=record.product_variant_id,
        warehouse_id=record.warehouse_id,
        quantity=record.quantity,
        last_updated=record.updated_at,
    )
```


---

## Чек-лист

```
Cleanup:
[ ] git rm apps/orders apps/customer_orders
[ ] git rm apps/procurement apps/material_inventory apps/product_inventory
[ ] git add production/ untracked files
[ ] Видалити legacy поля з SalesOrderLine, ProductionOrder
[ ] warehouse_id NOT NULL

Naming refactor (models):
[ ] ProductModel → Product
[ ] ProductVariant → Variant
[ ] ProductMaterial → BOM
[ ] StockRecord → ProductStock
[ ] StockMovement → ProductStockMovement
[ ] FinishedStockTransfer → ProductStockTransfer
[ ] MaterialStockRecord → MaterialStock
[ ] MaterialMovement → MaterialStockMovement
[ ] CustomUser → User
[ ] Видалити всі model aliases

Naming refactor (fields):
[ ] ProductionOrder.model → product
[ ] ProductionOrder.current_status → status
[ ] ProductionOrder.customer_order_line → sales_order_line
[ ] ProductionOrder: urgent/embroidery/etsy → is_*
[ ] Color.availability_status → status
[ ] Всі product_model → product
[ ] Всі product_variant → variant

Бізнес-моделі:
[ ] Product: додати price, currency, cost_price
[ ] Customer: створити модель (name, phone, email, instagram, notes)
[ ] SalesOrder: додати customer FK
[ ] SalesOrder: додати payment_status, payment_method, paid_amount

При нагоді:
[ ] Розв'язати circular deps через DI/callbacks
[ ] Explicit warehouse_id в API
[ ] Query managers для повторюваних запитів
[ ] Domain types (NewType/dataclass)

Міграції (нова БД):
[ ] Видалити всі migrations/*.py (крім __init__.py)
[ ] python manage.py makemigrations
[ ] python manage.py migrate

Validation:
[ ] pytest
[ ] python manage.py check --deploy
```
