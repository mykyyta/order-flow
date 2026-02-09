# Архітектура: замовлення клієнтів, бандли, склад

Аналіз бізнес-потреб та план розширення системи для підтримки:
- Замовлення клієнтів (сайт, Etsy, опт)
- Складені товари (бандли)
- Склад готової продукції
- Зв'язок із виробництвом

---

## Поточний стан

```
Order (виробниче завдання)
  ├── ProductModel (FK) — що робимо
  ├── Color (FK) — якого кольору
  ├── current_status — new/doing/embroidery/deciding/on_hold/finished
  └── OrderStatusHistory — аудит змін

Material (довідник матеріалів)
  └── поки не зв'язаний з Order
```

**Ключове розуміння**: поточний `Order` — це **виробниче завдання** на одну позицію, а не замовлення клієнта.

---

## Бізнес-потреби

### Джерела замовлень
- Сайт (роздріб)
- Etsy (роздріб, міжнародний)
- Опт (багато позицій, інші умови)

### Каталог
- Десятки товарів (ProductModel)
- Багато кольорів для кожного
- Товари можуть продаватись окремо або в складі бандла

### Бандли (складені товари)
Приклад: "Клатч з ремінцем" = один артикул для клієнта, але:
- Клатч (основний) — клієнт обирає колір
- Ремінець (додатковий) — клієнт обирає колір окремо
- Ті самі компоненти можуть продаватись і окремо

Варіанти комбінацій:
- **Фіксовані**: "Total black" = чорний клатч + чорний ремінець
- **На вибір**: клієнт обирає колір кожного компонента

### Потік виконання
```
Замовлення клієнта
       │
       ├── Є на складі? → Резервуємо → Відвантажуємо
       │
       └── Немає на складі? → Виробниче завдання (Order)
                                      │
                                      └── Готово → На склад → Відвантажуємо
```

---

## Запропонована архітектура

### Діаграма сутностей

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CATALOG                                     │
│                                                                          │
│  ProductModel                                                            │
│    ├── name: "Клатч", "Ремінець", "Клатч з ремінцем"                     │
│    └── is_bundle: bool                                                   │
│                                                                          │
│  Color                                                                   │
│    ├── name: "чорний", "синій", "total black", "total blue"              │
│    └── (для бандлів "колір" = назва комбінації)                          │
│                                                                          │
│  BundleComponent                                                         │
│    ├── bundle → ProductModel (is_bundle=True)                            │
│    ├── component → ProductModel (is_bundle=False)                        │
│    ├── is_primary: bool (основний компонент)                             │
│    └── quantity: int                                                     │
│                                                                          │
│  BundleColorMapping (для фіксованих комбінацій)                          │
│    ├── bundle → ProductModel                                             │
│    ├── bundle_color → Color ("total black")                              │
│    ├── component → ProductModel ("Клатч")                                │
│    └── component_color → Color ("чорний")                                │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                           CUSTOMER ORDERS                                │
│                                                                          │
│  CustomerOrder                                                           │
│    ├── source: site / etsy / wholesale                                   │
│    ├── customer_info: текст або структуровані поля                       │
│    ├── status: new / processing / shipped / completed                    │
│    └── created_at, updated_at                                            │
│                                                                          │
│  CustomerOrderLine                                                       │
│    ├── customer_order → CustomerOrder                                    │
│    ├── product_model → ProductModel (може бути бандл)                    │
│    ├── color → Color (null для бандлів з вільним вибором)                │
│    └── quantity: int                                                     │
│                                                                          │
│  CustomerOrderLineComponent (кольори компонентів бандла)                 │
│    ├── order_line → CustomerOrderLine                                    │
│    ├── component → ProductModel                                          │
│    └── color → Color                                                     │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                             INVENTORY                                    │
│                                                                          │
│  StockRecord                                                             │
│    ├── product_model → ProductModel (тільки is_bundle=False)             │
│    ├── color → Color                                                     │
│    ├── quantity: int                                                     │
│    └── unique_together: (product_model, color)                           │
│                                                                          │
│  StockMovement (опційно, для аудиту)                                     │
│    ├── stock_record → StockRecord                                        │
│    ├── quantity_change: int (+/-)                                        │
│    ├── reason: production_in / order_out / adjustment                    │
│    ├── related_order → Order (null)                                      │
│    ├── related_customer_order_line → CustomerOrderLine (null)            │
│    └── created_at                                                        │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                            PRODUCTION                                    │
│                                                                          │
│  Order (існуюча модель = виробниче завдання)                             │
│    ├── model → ProductModel                                              │
│    ├── color → Color                                                     │
│    ├── current_status: new / doing / ... / finished                      │
│    ├── customer_order_line → CustomerOrderLine (null, optional)          │
│    └── ... існуючі поля                                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Зв'язки між сутностями

```
CustomerOrder (замовлення Марії з Etsy)
    │
    └── CustomerOrderLine: "Клатч з ремінцем" × 1
            │
            ├── CustomerOrderLineComponent: Клатч → синій
            ├── CustomerOrderLineComponent: Ремінець → чорний
            │
            │   Перевірка складу:
            │   ├── StockRecord(Клатч, синій) = 0 → потрібне виробництво
            │   └── StockRecord(Ремінець, чорний) = 5 → є на складі
            │
            └── Order (виробниче): Клатч, синій
                    │
                    └── finished → StockRecord(Клатч, синій) += 1
                                          │
                                          └── Відвантаження → StockRecord -= 1
```

---

## Моделі Django

### catalog/models.py (зміни)

```python
class ProductModel(models.Model):
    name = models.CharField(max_length=255, unique=True)
    is_bundle = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)

    def __str__(self):
        return self.name


class BundleComponent(models.Model):
    """Компоненти бандла"""
    bundle = models.ForeignKey(
        ProductModel,
        on_delete=models.CASCADE,
        related_name='components',
        limit_choices_to={'is_bundle': True},
    )
    component = models.ForeignKey(
        ProductModel,
        on_delete=models.CASCADE,
        related_name='part_of_bundles',
        limit_choices_to={'is_bundle': False},
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Основний компонент, колір якого обирається першим",
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ['bundle', 'component']
        ordering = ['-is_primary', 'id']

    def __str__(self):
        return f"{self.bundle.name} → {self.component.name}"


class BundleColorMapping(models.Model):
    """Маппінг 'кольору' бандла на кольори компонентів (для фіксованих комбінацій)"""
    bundle = models.ForeignKey(
        ProductModel,
        on_delete=models.CASCADE,
        related_name='color_mappings',
    )
    bundle_color = models.ForeignKey(
        Color,
        on_delete=models.CASCADE,
        related_name='as_bundle_color',
        help_text="Колір/варіант бандла (напр. 'total black')",
    )
    component = models.ForeignKey(
        ProductModel,
        on_delete=models.CASCADE,
    )
    component_color = models.ForeignKey(
        Color,
        on_delete=models.CASCADE,
        related_name='as_component_color',
    )

    class Meta:
        unique_together = ['bundle', 'bundle_color', 'component']

    def __str__(self):
        return f"{self.bundle.name}[{self.bundle_color.name}]: {self.component.name}={self.component_color.name}"
```

### orders/models.py (зміни до Order)

```python
class Order(models.Model):
    """Виробниче завдання на одну позицію"""
    # ... існуючі поля ...

    # Новий зв'язок (опційний)
    customer_order_line = models.ForeignKey(
        'CustomerOrderLine',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='production_orders',
        help_text="Позиція замовлення клієнта, для якої створено це виробництво",
    )
```

### Новий app: customer_orders/models.py

```python
class CustomerOrder(models.Model):
    """Замовлення клієнта"""
    SOURCE_CHOICES = [
        ('site', 'Сайт'),
        ('etsy', 'Etsy'),
        ('wholesale', 'Опт'),
    ]
    STATUS_CHOICES = [
        ('new', 'Нове'),
        ('processing', 'В обробці'),
        ('production', 'На виробництві'),
        ('ready', 'Готове до відправки'),
        ('shipped', 'Відправлено'),
        ('completed', 'Завершено'),
        ('cancelled', 'Скасовано'),
    ]

    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    customer_info = models.TextField(blank=True, help_text="Ім'я, контакти, адреса")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"#{self.id} ({self.get_source_display()})"


class CustomerOrderLine(models.Model):
    """Позиція замовлення клієнта"""
    customer_order = models.ForeignKey(
        CustomerOrder,
        on_delete=models.CASCADE,
        related_name='lines',
    )
    product_model = models.ForeignKey(
        'catalog.ProductModel',
        on_delete=models.PROTECT,
    )
    # Для звичайного товару або бандла з фіксованою комбінацією
    color = models.ForeignKey(
        'catalog.Color',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Колір товару або варіант бандла. Null якщо бандл з вільним вибором.",
    )
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        color_str = self.color.name if self.color else "custom"
        return f"{self.product_model.name} ({color_str}) × {self.quantity}"

    @property
    def is_bundle(self):
        return self.product_model.is_bundle


class CustomerOrderLineComponent(models.Model):
    """Кольори компонентів бандла (для вільного вибору або розгорнуті з фіксованої комбінації)"""
    order_line = models.ForeignKey(
        CustomerOrderLine,
        on_delete=models.CASCADE,
        related_name='component_colors',
    )
    component = models.ForeignKey(
        'catalog.ProductModel',
        on_delete=models.PROTECT,
    )
    color = models.ForeignKey(
        'catalog.Color',
        on_delete=models.PROTECT,
    )

    class Meta:
        unique_together = ['order_line', 'component']

    def __str__(self):
        return f"{self.component.name} → {self.color.name}"
```

### Новий app: inventory/models.py

```python
class StockRecord(models.Model):
    """Залишки готової продукції на складі"""
    product_model = models.ForeignKey(
        'catalog.ProductModel',
        on_delete=models.PROTECT,
        limit_choices_to={'is_bundle': False},
    )
    color = models.ForeignKey(
        'catalog.Color',
        on_delete=models.PROTECT,
    )
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ['product_model', 'color']
        verbose_name = 'Залишок на складі'
        verbose_name_plural = 'Залишки на складі'

    def __str__(self):
        return f"{self.product_model.name} ({self.color.name}): {self.quantity}"


class StockMovement(models.Model):
    """Рух товарів на складі (аудит)"""
    REASON_CHOICES = [
        ('production_in', 'Надходження з виробництва'),
        ('order_out', 'Відвантаження клієнту'),
        ('adjustment_in', 'Коригування +'),
        ('adjustment_out', 'Коригування -'),
        ('return_in', 'Повернення'),
    ]

    stock_record = models.ForeignKey(
        StockRecord,
        on_delete=models.CASCADE,
        related_name='movements',
    )
    quantity_change = models.IntegerField(help_text="+ надходження, - витрата")
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    related_production_order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    related_customer_order_line = models.ForeignKey(
        'customer_orders.CustomerOrderLine',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'orders.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.quantity_change > 0 else ''
        return f"{self.stock_record}: {sign}{self.quantity_change}"
```

---

## Бізнес-логіка (services)

### customer_orders/services.py

```python
from django.db import transaction
from catalog.models import BundleColorMapping

@transaction.atomic
def create_customer_order(
    *,
    source: str,
    customer_info: str,
    lines_data: list[dict],
) -> CustomerOrder:
    """
    Створює замовлення клієнта з позиціями.

    lines_data: [
        {
            'product_model_id': 1,
            'color_id': 10,  # або None для бандла з вільним вибором
            'quantity': 1,
            'component_colors': [  # тільки для бандлів з вільним вибором
                {'component_id': 2, 'color_id': 11},
            ]
        }
    ]
    """
    order = CustomerOrder.objects.create(
        source=source,
        customer_info=customer_info,
    )

    for line_data in lines_data:
        line = CustomerOrderLine.objects.create(
            customer_order=order,
            product_model_id=line_data['product_model_id'],
            color_id=line_data.get('color_id'),
            quantity=line_data['quantity'],
        )

        # Для бандлів — зберігаємо кольори компонентів
        if line.is_bundle:
            _save_bundle_component_colors(line, line_data)

    return order


def _save_bundle_component_colors(line: CustomerOrderLine, line_data: dict):
    """Зберігає кольори компонентів бандла"""
    if line.color:
        # Фіксована комбінація — беремо з BundleColorMapping
        mappings = BundleColorMapping.objects.filter(
            bundle=line.product_model,
            bundle_color=line.color,
        )
        for mapping in mappings:
            CustomerOrderLineComponent.objects.create(
                order_line=line,
                component=mapping.component,
                color=mapping.component_color,
            )
    else:
        # Вільний вибір — беремо з line_data
        for comp_data in line_data.get('component_colors', []):
            CustomerOrderLineComponent.objects.create(
                order_line=line,
                component_id=comp_data['component_id'],
                color_id=comp_data['color_id'],
            )
```

### inventory/services.py

```python
from django.db import transaction
from .models import StockRecord, StockMovement

def get_stock_quantity(product_model_id: int, color_id: int) -> int:
    """Повертає кількість на складі"""
    try:
        record = StockRecord.objects.get(
            product_model_id=product_model_id,
            color_id=color_id,
        )
        return record.quantity
    except StockRecord.DoesNotExist:
        return 0


@transaction.atomic
def add_to_stock(
    *,
    product_model_id: int,
    color_id: int,
    quantity: int,
    reason: str,
    production_order=None,
    user=None,
    notes: str = '',
):
    """Додає товар на склад"""
    record, _ = StockRecord.objects.get_or_create(
        product_model_id=product_model_id,
        color_id=color_id,
    )
    record.quantity += quantity
    record.save()

    StockMovement.objects.create(
        stock_record=record,
        quantity_change=quantity,
        reason=reason,
        related_production_order=production_order,
        created_by=user,
        notes=notes,
    )
    return record


@transaction.atomic
def remove_from_stock(
    *,
    product_model_id: int,
    color_id: int,
    quantity: int,
    reason: str,
    customer_order_line=None,
    user=None,
    notes: str = '',
):
    """Списує товар зі складу"""
    record = StockRecord.objects.get(
        product_model_id=product_model_id,
        color_id=color_id,
    )
    if record.quantity < quantity:
        raise ValueError(f"Недостатньо на складі: є {record.quantity}, потрібно {quantity}")

    record.quantity -= quantity
    record.save()

    StockMovement.objects.create(
        stock_record=record,
        quantity_change=-quantity,
        reason=reason,
        related_customer_order_line=customer_order_line,
        created_by=user,
        notes=notes,
    )
    return record
```

---

## Сценарії використання

### Сценарій 1: Звичайний товар зі складу

```
1. Клієнт замовляє "Клатч синій" × 1
2. Система перевіряє StockRecord(Клатч, синій)
3. Є на складі → резервуємо
4. Відвантаження → StockMovement(reason='order_out')
5. CustomerOrder.status = 'shipped'
```

### Сценарій 2: Звичайний товар — виробництво

```
1. Клієнт замовляє "Клатч синій" × 1
2. Система перевіряє StockRecord(Клатч, синій) = 0
3. Створюється Order (виробниче) з customer_order_line
4. Виробництво: Order.status = 'finished'
5. Тригер: StockMovement(reason='production_in')
6. Відвантаження → StockMovement(reason='order_out')
```

### Сценарій 3: Бандл з фіксованою комбінацією

```
1. Клієнт замовляє "Клатч з ремінцем — total black" × 1
2. CustomerOrderLine: product="Клатч з ремінцем", color="total black"
3. Система через BundleColorMapping визначає:
   - Клатч → чорний
   - Ремінець → чорний
4. Зберігає в CustomerOrderLineComponent
5. Перевіряє склад кожного компонента окремо
6. Створює Order для відсутніх компонентів
```

### Сценарій 4: Бандл з вільним вибором

```
1. Клієнт замовляє "Клатч з ремінцем", обирає:
   - Клатч: синій
   - Ремінець: чорний
2. CustomerOrderLine: product="Клатч з ремінцем", color=NULL
3. CustomerOrderLineComponent:
   - Клатч → синій
   - Ремінець → чорний
4. Далі як у сценарії 3
```

---

## Етапи реалізації

### Етап 1: CustomerOrder без бандлів (1-2 PR)

**Scope:**
- Новий app `customer_orders`
- Моделі: `CustomerOrder`, `CustomerOrderLine`
- UI: список, створення, перегляд
- Без бандлів (тільки звичайні товари)
- Без складу (тільки облік замовлень)

**Результат:** можна приймати замовлення клієнтів.

### Етап 2: Склад — StockRecord (1 PR)

**Scope:**
- Новий app `inventory`
- Моделі: `StockRecord`, `StockMovement`
- UI: перегляд залишків, ручне коригування
- Інтеграція з Order: при `finished` → `production_in`

**Результат:** облік готової продукції.

### Етап 3: Зв'язок CustomerOrder ↔ Order ↔ Stock (1-2 PR)

**Scope:**
- `Order.customer_order_line` FK
- Логіка: при створенні CustomerOrderLine → перевірка складу → створення Order якщо потрібно
- При відвантаженні → `order_out`

**Результат:** повний потік від замовлення до відвантаження.

### Етап 4: Бандли (2-3 PR)

**Scope:**
- `ProductModel.is_bundle`
- `BundleComponent`, `BundleColorMapping`
- `CustomerOrderLineComponent`
- UI для створення бандлів в каталозі
- UI для замовлення бандлів (вибір кольорів компонентів)

**Результат:** повна підтримка складених товарів.

### Етап 5: BOM — матеріали для виробництва (опційно)

**Scope:**
- `ProductMaterial` (зв'язок ProductModel → Material)
- При створенні Order → перевірка наявності матеріалів
- Інтеграція з існуючим MaterialRequest

**Результат:** планування матеріалів для виробництва.

---

## Відкриті питання

1. **Статуси CustomerOrder** — чи потрібні додаткові статуси для опту?

2. **Часткове виконання** — чи можна відвантажити частину замовлення (наприклад, 2 з 3 позицій)?

3. **Резервування** — чи потрібно резервувати товар на складі до відвантаження?

4. **Ціни** — чи зберігати ціну в CustomerOrderLine? Різні ціни для опту?

5. **Опт** — чи є специфічні поля/логіка для оптових замовлень?

---

## Конвенції (узгоджено з проєктом)

- Поля: `snake_case`, англійською
- FK без `_id`: `customer_order`, `product_model`
- Таймстемпи: `created_at`, `updated_at`, `archived_at`
- Кількість: `quantity` (не `qty`)
- Статуси: `snake_case` рядки
- Транзакції: `@transaction.atomic` для multi-record операцій
