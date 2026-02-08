# План рефакторингу Pult

## Огляд

Мета: спростити архітектуру, завершити split apps, покращити DX для швидкої розробки.

**Принципи:**
- Кожен етап — окремий PR, можна мержити незалежно
- Не ламаємо прод між етапами
- Спочатку інфраструктура тестів, потім рефакторинг коду

---

## Етап 1: Інфраструктура тестів (1-2 дні)

### 1.1 Перехід на pytest

```bash
# requirements-dev.txt
pytest==8.3.4
pytest-django==4.9.0
factory-boy==3.3.1
```

```python
# pytest.ini (або в pyproject.toml)
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.local"
python_files = "test_*.py"
addopts = "-v --tb=short"
```

### 1.2 Структура тестів

```
orders/
  tests/
    __init__.py
    conftest.py           # fixtures, factories
    test_domain.py        # status transitions, policies
    test_services.py      # OrderService unit tests
    test_views.py         # HTTP layer integration
    test_commands.py      # management commands
    test_notifications.py # notification logic

catalog/
  tests/
    __init__.py
    conftest.py
    test_views.py

accounts/
  tests/
    __init__.py
    conftest.py
    test_auth.py
    test_profile.py
```

### 1.3 Factories

```python
# orders/tests/conftest.py
import factory
from factory.django import DjangoModelFactory

class UserFactory(DjangoModelFactory):
    class Meta:
        model = "orders.CustomUser"

    username = factory.Sequence(lambda n: f"user_{n}")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class ProductModelFactory(DjangoModelFactory):
    class Meta:
        model = "catalog.ProductModel"

    name = factory.Sequence(lambda n: f"Model {n}")


class ColorFactory(DjangoModelFactory):
    class Meta:
        model = "catalog.Color"

    name = factory.Sequence(lambda n: f"Color {n}")
    code = factory.Sequence(lambda n: n + 100)
    availability_status = "in_stock"


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = "orders.Order"

    model = factory.SubFactory(ProductModelFactory)
    color = factory.SubFactory(ColorFactory)
    current_status = "new"


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def order(db):
    return OrderFactory()
```

### 1.4 Міграція існуючих тестів

1. Перенести тести з `orders/tests.py` → `orders/tests/test_*.py`
2. Замінити `self.assertEqual` → `assert`
3. Замінити ручне створення об'єктів → factories
4. Видалити Fake* класи де можна замінити на `@pytest.fixture` + `mocker.patch`

**PR:** `test/migrate-to-pytest`

---

## Етап 2: Спрощення архітектури (2-3 дні)

### 2.1 Гібридний підхід: бізнес-логіка в моделях

**До:**
```
View → OrderService(dataclass) → Repository(Protocol) → ORM
```

**Після:**
```
View → service function → Model methods → ORM
```

### 2.2 Перенести domain logic в модель Order

```python
# orders/models.py

from orders.domain.order_statuses import STATUS_FINISHED, get_allowed_transitions

class Order(models.Model):
    # ... fields ...

    def can_transition_to(self, new_status: str) -> bool:
        """Чи дозволений перехід до нового статусу."""
        allowed = get_allowed_transitions(self.current_status)
        return new_status in allowed

    def transition_to(self, new_status: str, changed_by: "CustomUser") -> None:
        """Змінити статус (без збереження, без нотифікацій)."""
        if not self.can_transition_to(new_status):
            raise InvalidStatusTransition(self.current_status, new_status)

        self.current_status = new_status
        self.finished_at = self._compute_finished_at(new_status)

        # Створити запис в історії
        OrderStatusHistory.objects.create(
            order=self,
            new_status=new_status,
            changed_by=changed_by,
        )

    def _compute_finished_at(self, new_status: str) -> datetime | None:
        if new_status == STATUS_FINISHED:
            return timezone.now()
        return None
```

### 2.3 Спростити сервісний шар

```python
# orders/services.py (замість application/order_service.py)

from django.db import transaction
from orders.models import Order, OrderStatusHistory
from orders.notifications import send_order_created, send_order_finished


@transaction.atomic
def create_order(
    *,
    model: "ProductModel",
    color: "Color",
    embroidery: bool,
    urgent: bool,
    etsy: bool,
    comment: str | None,
    created_by: "CustomUser",
    orders_url: str | None,
) -> Order:
    """Створити нове замовлення."""
    order = Order.objects.create(
        model=model,
        color=color,
        embroidery=embroidery,
        urgent=urgent,
        etsy=etsy,
        comment=comment,
        current_status="new",
    )

    OrderStatusHistory.objects.create(
        order=order,
        new_status="new",
        changed_by=created_by,
    )

    send_order_created(order=order, orders_url=orders_url)
    return order


@transaction.atomic
def change_order_status(
    *,
    orders: list[Order],
    new_status: str,
    changed_by: "CustomUser",
) -> None:
    """Змінити статус для списку замовлень."""
    for order in orders:
        order.transition_to(new_status, changed_by)
        order.save()

        if new_status == "finished":
            send_order_finished(order=order)
```

### 2.4 Спростити notifications

```python
# orders/notifications.py (замість adapters/notifications.py)

from orders.models import NotificationSetting, DelayedNotificationLog
from orders.utils import send_tg_message, order_detail_text


def send_order_created(*, order: "Order", orders_url: str | None) -> None:
    """Надіслати нотифікацію про нове замовлення."""
    users = _get_users_to_notify("notify_order_created")

    for user in users:
        if _should_delay_notification(user):
            continue  # буде надіслано о 08:00

        text = order_detail_text(order, orders_url)
        send_tg_message(user.telegram_id, text)


def send_order_finished(*, order: "Order") -> None:
    """Надіслати нотифікацію про завершення."""
    users = _get_users_to_notify("notify_order_finished")

    for user in users:
        text = f"✅ Замовлення #{order.id} завершено"
        send_tg_message(user.telegram_id, text)


def _get_users_to_notify(setting_field: str) -> list:
    """Отримати користувачів з увімкненою нотифікацією."""
    from orders.models import CustomUser

    return CustomUser.objects.filter(
        telegram_id__isnull=False,
        **{f"notification_settings__{setting_field}": True}
    ).select_related("notification_settings")


def _should_delay_notification(user) -> bool:
    """Чи відкласти нотифікацію (18:00-08:00)."""
    # ... існуюча логіка ...
```

### 2.5 Що видалити

```
orders/
  application/          # ВИДАЛИТИ всю папку
    order_service.py
    notification_service.py
    ports.py
    exceptions.py
  adapters/             # ВИДАЛИТИ всю папку
    orders_repository.py
    notifications.py
    clock.py
```

Залишити:
```
orders/
  domain/               # ЗАЛИШИТИ — правила статусів
    order_statuses.py
    transitions.py
    policies.py         # можна інтегрувати в model
    status.py
  services.py           # НОВИЙ — прості функції
  notifications.py      # НОВИЙ — telegram logic
```

### 2.6 Оновити views

```python
# orders/views/orders.py

# Було:
from orders.application.order_service import OrderService
from orders.adapters.orders_repository import DjangoOrderRepository
from orders.adapters.notifications import DjangoNotificationSender
from orders.adapters.clock import DjangoClock

def orders_create(request):
    service = OrderService(
        repo=DjangoOrderRepository(),
        notifier=DjangoNotificationSender(),
        clock=DjangoClock(),
    )
    order = service.create_order(...)

# Стало:
from orders.services import create_order

def orders_create(request):
    order = create_order(
        model=form.cleaned_data["model"],
        color=form.cleaned_data["color"],
        # ...
        created_by=request.user,
        orders_url=request.build_absolute_uri(reverse("orders_active")),
    )
```

**PR:** `refactor/simplify-architecture`

---

## Етап 3: Міграція CustomUser (1-2 дні)

### 3.1 Проблема

`AUTH_USER_MODEL = "orders.CustomUser"` — змінювати після міграцій складно.

### 3.2 Варіанти

**Варіант A: Залишити як є** (рекомендовано)
- CustomUser залишається в `orders`
- NotificationSetting переносимо в `accounts`
- Мінімум ризику

**Варіант B: Повна міграція** (якщо хочете чистоту)
- Створити `users` app
- Складна data migration
- Ризик втрати даних

### 3.3 Рекомендований план (Варіант A)

```python
# accounts/models.py
from django.db import models
from django.conf import settings


class NotificationSetting(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_settings",
    )
    notify_order_created = models.BooleanField(default=True)
    notify_order_finished = models.BooleanField(default=True)
    notify_order_created_pause = models.BooleanField(default=True)
```

Міграція:
1. Створити модель в `accounts`
2. Data migration: скопіювати дані
3. Оновити FK/references
4. Видалити стару модель з `orders`

**PR:** `refactor/move-notification-settings`

---

## Етап 4: Типізація (1 день)

### 4.1 Додати mypy

```bash
# requirements-dev.txt
mypy==1.14.1
django-stubs==5.1.2
```

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.12"
plugins = ["mypy_django_plugin.main"]
strict = false  # почати з м'якого режиму
warn_unused_ignores = true
ignore_missing_imports = true

[tool.django-stubs]
django_settings_module = "config.settings.local"
```

### 4.2 Поступова типізація

```python
# orders/services.py
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from catalog.models import ProductModel, Color
    from orders.models import CustomUser, Order


def create_order(
    *,
    model: ProductModel,
    color: Color,
    embroidery: bool,
    urgent: bool,
    etsy: bool,
    comment: str | None,
    created_by: CustomUser,
    orders_url: str | None,
) -> Order:
    ...
```

### 4.3 CI перевірка

```yaml
# .github/workflows/ci.yml
- name: Type check
  run: mypy orders/ catalog/ accounts/ --ignore-missing-imports
```

**PR:** `chore/add-type-checking`

---

## Етап 5: Структура проекту (1 день)

### 5.1 Фінальна структура

```
pult/
├── src/                            # Backend код
│   ├── config/                     # Django settings
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── local.py
│   │   │   └── prod.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   │
│   ├── apps/                       # Django apps
│   │   ├── orders/
│   │   │   ├── domain/
│   │   │   ├── tests/
│   │   │   ├── views/
│   │   │   ├── templatetags/
│   │   │   ├── management/
│   │   │   ├── migrations/
│   │   │   ├── models.py
│   │   │   ├── services.py
│   │   │   ├── notifications.py
│   │   │   ├── forms.py
│   │   │   ├── admin.py
│   │   │   ├── urls.py
│   │   │   └── utils.py
│   │   │
│   │   ├── catalog/
│   │   │   ├── tests/
│   │   │   ├── migrations/
│   │   │   ├── models.py
│   │   │   ├── views.py
│   │   │   ├── forms.py
│   │   │   ├── admin.py
│   │   │   └── urls.py
│   │   │
│   │   └── accounts/
│   │       ├── tests/
│   │       ├── migrations/
│   │       ├── models.py           # NotificationSetting
│   │       ├── views.py
│   │       └── urls.py
│   │
│   └── manage.py
│
├── frontend/                       # UI assets
│   ├── templates/
│   │   ├── base.html
│   │   ├── partials/
│   │   ├── orders/
│   │   ├── catalog/
│   │   └── account/
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   └── assets/                     # Tailwind sources
│       └── tailwind/
│
├── infra/                          # Terraform
├── docs/
├── .github/
│
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.yml
└── makefile
```

**Корінь: 10 items** (замість 15+)

### 5.2 Кроки міграції

#### 5.2.1 Створити структуру папок

```bash
mkdir -p src/apps
mkdir -p frontend
```

#### 5.2.2 Перемістити файли

```bash
# Backend
mv config/ src/
mv orders/ src/apps/
mv catalog/ src/apps/
mv accounts/ src/apps/
mv manage.py src/

# Frontend
mv templates/ frontend/
mv static/ frontend/
mv assets/ frontend/
```

#### 5.2.3 Оновити Django settings

```python
# src/config/settings/base.py

from pathlib import Path

# BASE_DIR тепер вказує на src/
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Шлях до кореня проекту (для frontend/)
PROJECT_ROOT = BASE_DIR.parent

INSTALLED_APPS = [
    ...
    "apps.orders",
    "apps.catalog",
    "apps.accounts",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [PROJECT_ROOT / "frontend" / "templates"],
        ...
    },
]

STATICFILES_DIRS = [
    PROJECT_ROOT / "frontend" / "static",
]
```

#### 5.2.4 Оновити apps.py для кожного app

```python
# src/apps/orders/apps.py
class OrdersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.orders"
    label = "orders"  # ← Важливо! Зберігає назву таблиць
```

```python
# src/apps/catalog/apps.py
class CatalogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.catalog"
    label = "catalog"
```

```python
# src/apps/accounts/apps.py
class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"
```

#### 5.2.5 Оновити imports в коді

```python
# Було:
from orders.models import Order
from catalog.models import ProductModel

# Стало:
from apps.orders.models import Order
from apps.catalog.models import ProductModel
```

**Автоматизація:**
```bash
# В src/ директорії
find . -name "*.py" -exec sed -i '' 's/from orders\./from apps.orders./g' {} +
find . -name "*.py" -exec sed -i '' 's/from catalog\./from apps.catalog./g' {} +
find . -name "*.py" -exec sed -i '' 's/from accounts\./from apps.accounts./g' {} +
find . -name "*.py" -exec sed -i '' 's/import orders\./import apps.orders./g' {} +
```

#### 5.2.6 Оновити Dockerfile

```dockerfile
WORKDIR /app

# Копіюємо requirements в корінь
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо src/ в /app/src/
COPY src/ ./src/

# Копіюємо frontend/ в /app/frontend/
COPY frontend/ ./frontend/

# Встановлюємо PYTHONPATH
ENV PYTHONPATH=/app/src

# Команди використовують src/manage.py
CMD ["python", "src/manage.py", "runserver", "0.0.0.0:8000"]
```

#### 5.2.7 Оновити docker-compose.yml

```yaml
services:
  web:
    build: .
    volumes:
      - ./src:/app/src
      - ./frontend:/app/frontend
    environment:
      - PYTHONPATH=/app/src
      - DJANGO_SETTINGS_MODULE=config.settings.local
    command: python src/manage.py runserver 0.0.0.0:8000
```

#### 5.2.8 Оновити makefile

```makefile
MANAGE = python src/manage.py

.PHONY: dev test migrate

dev:
	$(MANAGE) runserver

test:
	cd src && python manage.py test

migrate:
	$(MANAGE) migrate

shell:
	$(MANAGE) shell
```

#### 5.2.9 Оновити CI workflow

```yaml
# .github/workflows/ci.yml
jobs:
  test:
    steps:
      - name: Run tests
        working-directory: src
        run: python manage.py test

      - name: Lint
        run: ruff check src/
```

#### 5.2.10 Оновити pyproject.toml

```toml
[tool.ruff]
src = ["src"]

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.local"
pythonpath = ["src"]

[tool.mypy]
mypy_path = "src"
```

#### 5.2.11 Оновити Tailwind config

```javascript
// frontend/assets/tailwind/tailwind.config.js (якщо є)
module.exports = {
  content: [
    "../templates/**/*.html",
    "../static/js/**/*.js",
  ],
  // ...
}
```

### 5.3 Чекліст

- [ ] Створити `src/` і `frontend/` директорії
- [ ] Перемістити Django код в `src/`
- [ ] Перемістити templates/static/assets в `frontend/`
- [ ] Оновити `BASE_DIR` в settings
- [ ] Оновити `TEMPLATES['DIRS']` і `STATICFILES_DIRS`
- [ ] Оновити `apps.py` (name + label)
- [ ] Масово замінити imports
- [ ] Оновити Dockerfile
- [ ] Оновити docker-compose.yml
- [ ] Оновити makefile
- [ ] Оновити CI workflow
- [ ] Оновити pyproject.toml (ruff, pytest, mypy paths)
- [ ] Оновити Tailwind config
- [ ] Запустити тести
- [ ] Перевірити collectstatic
- [ ] Перевірити локальний dev server
- [ ] Deploy на staging

**PR:** `refactor/project-structure`

---

## Порядок виконання

```
Етап 1 (тести) ──► Етап 2 (архітектура) ──► Етап 3 (models) ──► Етап 4 (типи) ──► Етап 5 (структура)
```

**Чому такий порядок:**
1. **Тести першими** — дають впевненість для рефакторингу
2. **Архітектура** — спрощуємо код поки imports прості
3. **Models** — переносимо NotificationSetting
4. **Типізація** — додаємо mypy
5. **Структура останньою** — масова зміна imports, краще робити коли код стабільний

## Чеклісти для PR

### Етап 1: pytest
- [ ] Додати pytest, pytest-django, factory-boy
- [ ] Створити структуру `tests/` папок
- [ ] Написати factories
- [ ] Мігрувати 5-10 тестів як proof of concept
- [ ] Мігрувати решту тестів
- [ ] Видалити старі `tests.py`
- [ ] CI працює

### Етап 2: архітектура
- [ ] Додати методи в Order model
- [ ] Створити `orders/services.py`
- [ ] Створити `orders/notifications.py`
- [ ] Оновити views
- [ ] Оновити тести
- [ ] Видалити `application/`, `adapters/`
- [ ] Всі тести проходять

### Етап 3: NotificationSetting
- [ ] Створити модель в accounts
- [ ] Data migration
- [ ] Оновити imports
- [ ] Видалити з orders
- [ ] Тести проходять

### Етап 4: типізація
- [ ] Додати mypy, django-stubs
- [ ] Налаштувати pyproject.toml
- [ ] Типізувати services.py
- [ ] Типізувати notifications.py
- [ ] Додати в CI

### Етап 5: структура проекту
- [ ] Створити `src/` і `frontend/` директорії
- [ ] Перемістити Django код в `src/`
- [ ] Перемістити templates/static/assets в `frontend/`
- [ ] Оновити `BASE_DIR` в settings
- [ ] Оновити `apps.py` (name + label)
- [ ] Масово замінити imports (`from orders.` → `from apps.orders.`)
- [ ] Оновити Dockerfile, docker-compose, makefile
- [ ] Оновити CI workflow
- [ ] Оновити pyproject.toml (paths для ruff, pytest, mypy)
- [ ] Запустити всі тести
- [ ] Перевірити collectstatic і dev server

---

## Оцінка часу

| Етап | Час | Пріоритет |
|------|-----|-----------|
| 1. pytest + factories | 1-2 дні | HIGH |
| 2. Спрощення архітектури | 2-3 дні | HIGH |
| 3. Move NotificationSetting | 0.5 дня | MEDIUM |
| 4. Типізація | 1 день | MEDIUM |
| 5. Структура проекту | 1 день | HIGH |

**Загалом: 6-8 днів** (не підряд, можна розбити на тижні)

---

## Фінальна структура (після всіх етапів)

```
pult/
├── src/                            # Backend
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── local.py
│   │   │   └── prod.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   │
│   ├── apps/
│   │   ├── orders/                 # Замовлення (core domain)
│   │   │   ├── domain/             # Правила статусів
│   │   │   ├── tests/              # pytest + factories
│   │   │   ├── views/
│   │   │   ├── models.py           # Order, CustomUser, OrderStatusHistory
│   │   │   ├── services.py         # create_order(), change_status()
│   │   │   └── notifications.py    # Telegram logic
│   │   │
│   │   ├── catalog/                # Довідники
│   │   │   ├── tests/
│   │   │   └── models.py           # ProductModel, Color
│   │   │
│   │   └── accounts/               # Авторизація
│   │       ├── tests/
│   │       └── models.py           # NotificationSetting
│   │
│   └── manage.py
│
├── frontend/                       # UI
│   ├── templates/
│   ├── static/
│   └── assets/
│
├── infra/                          # Terraform
├── docs/
├── .github/
│
├── pyproject.toml                  # ruff + mypy + pytest
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.yml
└── makefile
```

**Корінь: 10 items** — чисто і зрозуміло
