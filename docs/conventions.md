# Конвенції розробки

## Принципи

- **Test-driven**: пиши тести першими, перевіряй лінтерами
- **Comments**: пояснюй *чому*, а не *що*
- **No over-engineering**: використовуй Django напряму, виділяй абстракції тільки коли дублювання болить


## Code Style

### Загальне

| Аспект | Правило |
|--------|---------|
| Довжина рядка | 100 символів |
| Мова коду | English |
| Мова UI | Ukrainian |
| Форматування | ruff format |
| Лінтинг | ruff check |

### Python

```python
# Keyword args для 3+ параметрів
def create_order(*, product: Product, variant: Variant, quantity: int): ...

# Type hints для сигнатур функцій
def get_stock(warehouse_id: int, variant_id: int) -> int: ...

# @transaction.atomic для multi-record операцій
@transaction.atomic
def complete_order(order: ProductionOrder, user: User) -> None: ...
```


## Naming Conventions

### Моделі

- **Імена класів**: PascalCase, однина, доменні імена
- **Приклади**: `Product`, `Variant`, `SalesOrder`, `ProductionOrder`

### Поля моделей

| Тип | Конвенція | Приклад |
|-----|-----------|---------|
| FK | `{model_name}` без `_id` | `product`, `warehouse`, `variant` |
| Status | просто `status` | `status = CharField(choices=...)` |
| Timestamps | `*_at` | `created_at`, `updated_at`, `finished_at` |
| Boolean | `is_*` або `has_*` | `is_active`, `is_urgent`, `has_telegram` |
| Quantity | `quantity` (не qty/amount) | `quantity`, `quantity_change` |
| Archive | `archived_at` (не is_archived) | `archived_at = DateTimeField(null=True)` |
| Notes | `notes` | `notes = TextField(blank=True)` |

### БД (автоматично Django)

- FK колонки: `{field}_id` (`product_id`, `warehouse_id`)
- Таблиці: `{app}_{model}` (`sales_salesorder`, `production_productionorder`)

### Індекси та constraints

```python
# Формат: {app}_{entity}_{purpose}_{type}
models.Index(fields=["status"], name="prod_order_status_idx")
models.UniqueConstraint(fields=["warehouse", "variant"], name="inv_stock_warehouse_variant_uniq")
```


## Service Layer

### Структура

```python
# apps/{app}/services.py

@transaction.atomic
def create_something(
    *,
    required_field: Type,
    optional_field: Type | None = None,
) -> Model:
    """Один public entrypoint на use case."""
    # Validation
    # Business logic
    # Side effects (notifications, etc.)
    return result
```

### Правила

1. **Один файл services.py на app** (або services/ директорія для великих)
2. **@transaction.atomic** для операцій з кількома моделями
3. **Keyword-only arguments** (`*` після self/cls)
4. **Domain exceptions** замість Django exceptions
5. **Callbacks** для cross-context side effects:

```python
def change_status(
    *,
    order: ProductionOrder,
    new_status: str,
    on_done: Callable[[ProductionOrder], None] | None = None,
) -> None:
    order.status = new_status
    order.save()
    if new_status == STATUS_DONE and on_done:
        on_done(order)
```


## Domain Layer

### Структура

```
apps/{app}/domain/
├── __init__.py
├── status.py       # Status constants, choices
├── policies.py     # Business rules
└── transitions.py  # State machine rules
```

### Правила

- **Чисті функції** (без side effects, без DB queries)
- **Константи** в UPPER_CASE
- **Choices** через TextChoices:

```python
class Status(models.TextChoices):
    NEW = "new", "Нове"
    PROCESSING = "processing", "В обробці"
    DONE = "done", "Готово"
```


## Testing

### Структура

```
apps/{app}/tests/
├── __init__.py
├── test_models.py
├── test_services.py
├── test_views.py
└── conftest.py      # Fixtures
```

### Правила

```python
# Descriptive test names
def test_create_order_sets_status_to_new(): ...
def test_complete_order_adds_to_stock(): ...

# Arrange-Act-Assert pattern
def test_something():
    # Arrange
    product = ProductFactory()

    # Act
    result = create_order(product=product)

    # Assert
    assert result.status == STATUS_NEW
```

### Fixtures

```python
# conftest.py
import pytest
from apps.catalog.tests.factories import ProductFactory

@pytest.fixture
def product():
    return ProductFactory()
```


## Views та Forms

### Views

```python
# Function-based для простих випадків
def order_list(request):
    orders = ProductionOrder.objects.filter(...)
    return render(request, "production/order_list.html", {"orders": orders})

# Class-based для CRUD
class OrderDetailView(LoginRequiredMixin, DetailView):
    model = ProductionOrder
    template_name = "production/order_detail.html"
```

### Forms


## Templates (UI)

### Base templates

За замовчуванням сторінки мають розширювати один з базових шаблонів:
- `base_list_page.html` — списки/таблиці
- `base_detail_page.html` — детал-сторінки
- `base_form_page.html` — одна форма в картці
- `base_archive_page.html` — архіви
- `base_drawer_page.html` — drawer/підформи

### Page-level flags (контекст)

- `show_page_header` (для `base_list_page.html`): ховає in-content `h1` і actions (корисно для chips-сторінок).
- `back_url` + `back_label`: back-link рендериться в base-шаблоні, не дублюй вручну.
- У шаблонах для boolean-флагів використовуй `default_if_none`, а не `default`, щоб `False` не перетворювався на `True`.

```python
class OrderForm(forms.ModelForm):
    class Meta:
        model = ProductionOrder
        fields = ["product", "variant", "is_urgent"]

    def clean(self):
        # Cross-field validation
        ...
```


## Imports

### Порядок

```python
# 1. Standard library
from __future__ import annotations
from typing import TYPE_CHECKING

# 2. Django
from django.db import models, transaction

# 3. Third-party
import pytest

# 4. Local apps
from apps.catalog.models import Product
from apps.inventory.services import add_to_stock

# 5. TYPE_CHECKING imports (для уникнення circular imports)
if TYPE_CHECKING:
    from apps.production.models import ProductionOrder
```

### Circular imports

Використовуй `TYPE_CHECKING` для type hints:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.other_app.models import OtherModel

def my_function(obj: "OtherModel") -> None: ...
```


## Migrations

### Правила

- **Не редагуй** згенеровані міграції без потреби
- **Atomic** за замовчуванням (Django default)
- **Data migrations** в окремих файлах
- **Іменування**: Django автогенерація або `{number}_{action}_{target}.py`

### Команди

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py showmigrations
```


## Git

### Commits

```
feat: add customer model to sales
fix: correct stock calculation on transfer
refactor: extract variant resolution to catalog
test: add integration tests for fulfillment
chore: update dependencies
```

### Branches

```
main              # Production
feature/{name}    # New features
fix/{name}        # Bug fixes
refactor/{name}   # Refactoring
```


## Checklist для нового коду

- [ ] Тести написані (або оновлені)
- [ ] Type hints додані
- [ ] @transaction.atomic де потрібно
- [ ] Naming відповідає конвенціям
- [ ] ruff check проходить
- [ ] ruff format застосовано


## Див. також

- [Архітектура](architecture.md)
- [DB Naming Conventions](db_naming_conventions.md)
