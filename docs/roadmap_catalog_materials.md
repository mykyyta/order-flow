# План: довідники (моделі/кольори) + матеріали (каркас)

Ціль: зробити простий, але розширюваний каркас довідників і матеріалів, щоб далі без болю додавати поля,
типи/параметри, замовлення матеріалів та інші фічі.

Принципи (під проєкт Pult):
- Не видаляємо довідникові записи, тільки архівуємо.
- Архів ≠ “сховати через manager”: не ламаємо існуючі FK (особливо в `orders`).
- Мінімум полів на старті, але структура така, щоб додати деталі без міграційних “вибухів”.
- Кожен етап можна робити окремим PR.

Конвенції імен (фіксуємо один раз):
- У моделях/БД: `snake_case`, англійською.
- FK поля в моделях: `material`, `supplier`, `created_by` (без `_id`), у БД буде `*_id`.
- Таймстемпи: `created_at`, `updated_at`, `archived_at` (архів через `archived_at`, не `is_archived`).
- Кількість: тільки `quantity` (не `qty`).
- Статуси/choices: поле `status`, значення — `snake_case` рядки.

---

## Етап 0: Підготовка (1 PR)

Визначення:
- **Активні** записи: `archived_at IS NULL`
- **Архів**: `archived_at IS NOT NULL`

Технічні домовленості:
- Поле архіву: `archived_at = DateTimeField(null=True, blank=True, db_index=True)`
- У списках/формах фільтруємо явно: `...filter(archived_at__isnull=True)`.
- Ніде не змінюємо `objects` на “тільки активні”, щоб не поламати `Order.model` / `Order.color`.

---

## Етап 1: Довідники `catalog` — картки + архів (1–2 PR)

### 1.1 ProductModel
Зміни:
- Додати `archived_at`.
- Додати сторінку-картку `ProductModel` (detail/edit) + кнопки:
  - “В архів” (POST)
  - “Відновити” (POST)
- Список “Моделі”:
  - показує активні
  - опційно перемикач “Показати архів”

UI:
- Сторінка картки аналогічна `catalog/color_edit.html` (card + форма + actions).

Тести:
- `orders` створення замовлення не показує архівні моделі.
- `orders` редагування замовлення лишає поточну модель у dropdown навіть якщо вона архівна.

### 1.2 Color
Зміни:
- Додати `archived_at`.
- На сторінці кольору додати “В архів/Відновити”.
- Список “Кольори”:
  - показує активні
  - опційно перемикач “Показати архів”

Тести:
- `OrderForm` для створення показує лише активні кольори з `availability_status in_stock/low_stock`.
- `order_edit` лишає поточний колір у dropdown, навіть якщо `out_of_stock` або архівний.

Нотатка:
- `availability_status` і архів — різні речі: “нема” ≠ “архів”.

---

## Етап 2: Новий app `materials` — довідник матеріалів (1 PR)

### 2.1 Моделі (мінімум)
- `Material`:
  - `name` (унікально серед активних — partial unique constraint)
  - `unit` (CharField choices: 'pcs'/'m'/'kg'/'l'/'m2' тощо)
  - `notes` (optional)
  - `archived_at`
  - `created_at`/`updated_at`

Constraint для унікальності активних:
```python
class Meta:
    constraints = [
        UniqueConstraint(
            fields=['name'],
            condition=Q(archived_at__isnull=True),
            name='unique_active_material_name'
        )
    ]
```

### 2.2 UI (мінімум)
- `/materials/` — список + створення (як `catalog/colors.html` / `product_models.html`).
- `/materials/<id>/` — картка material (edit + archive/unarchive).

### 2.3 Навігація
- Додати пункт меню “Матеріали”.

Тести:
- Усі сторінки `materials` вимагають логін.
- Архівні матеріали не показуються в активному списку.

---

## Етап 3: Постачальники + пропозиції (offers) для матеріалів (1–2 PR)

Вимога: у одного постачальника може бути **декілька** пропозицій на один матеріал.

### 3.1 Моделі (мінімум)
- `Supplier`:
  - `name`
  - `notes` (optional)
  - `archived_at`
  - `created_at`/`updated_at`
- `SupplierMaterialOffer`:
  - `material = FK(Material)`
  - `supplier = FK(Supplier)`
  - `title` (optional; як називається у постачальника)
  - `sku` (optional)
  - `price = DecimalField(max_digits=10, decimal_places=2, null=True)` — nullable для "ціна за запитом"
  - `url` (optional)
  - `notes` (optional)
  - `archived_at`
  - `created_at`/`updated_at`

Обмеження:
- НЕ робимо `UniqueConstraint(material, supplier)`, бо allow multiple offers.
- Якщо треба прибрати дублікати — робимо це на рівні UI/валідації пізніше.

### 3.2 UI: додати постачальника до матеріалу “без ручного створення item”
На картці матеріалу:
- Секція “Пропозиції постачальників” (табличка/список).
- Форма “Додати пропозицію”:
  - вибір `Supplier`
  - (опційно) `title/sku/url` можна лишати порожніми
  - submit створює `SupplierMaterialOffer` автоматично.

Тести:
- POST “додати пропозицію” створює `SupplierMaterialOffer` і редіректить назад на картку material.
- Архів “offer” прибирає її з активного списку пропозицій матеріалу.

---

## Етап 4: Запити/замовлення матеріалів (workflow) (2–3 PR)

Ціль: працівник робить запит, менеджер бачить і обробляє.

### 4.1 Моделі (мінімум)
- `MaterialRequest`:
  - `created_by = FK(CustomUser)`
  - `status` (new/ordered/received/canceled) — простий enum через choices
  - `notes` (optional)
  - `created_at`/`updated_at`
- `MaterialRequestLine`:
  - `request = FK(MaterialRequest)`
  - `material = FK(Material)`
  - `quantity = DecimalField(max_digits=10, decimal_places=3)`
  - `notes` (optional)
  - `chosen_offer = FK(SupplierMaterialOffer, null=True, blank=True)` (optional)

Транзакції:
- Створення запиту + ліній — `@transaction.atomic` (multi-record).

### 4.2 UI (мінімум)
- Працівник:
  - “Створити запит” (1 запит, 1+ позицій)
  - “Мої запити” (список)
- Менеджер:
  - “Черга запитів” (new/ordered)
  - на деталях може вибрати `offer` для лінії (або лишити порожнім) і поставити статус

Доступ:
- Старт: менеджер = `is_staff`.
- Пізніше: група/role, якщо треба.

Тести:
- Працівник може створити `MaterialRequest`.
- Не-менеджер не може міняти статус “manager actions”.

---

## Майбутнє: “обʼєднання” матеріалів і продуктів (не зараз)

Рекомендований шлях без злиття таблиць:
- Додати BOM таблицю `ProductMaterial`:
  - `product_model = FK(ProductModel)`
  - `material = FK(Material)`
  - `quantity = DecimalField(max_digits=10, decimal_places=3)`
  - `notes` (optional)
  - `archived_at`
  - `created_at`/`updated_at`
- Це дає “продукт складається з матеріалів”, не ламаючи існуючу модель даних.

---

## Визначення Done (для кожного етапу)
- Міграції застосовуються, тести проходять (`make test`, `make lint`).
- У UI є:
  - список активних
  - картка
  - архів/відновлення
- Немає місць, де архівні довідники “зникають” і ламають перегляд старих замовлень.
