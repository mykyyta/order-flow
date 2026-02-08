# Конвенції назв (моделі, поля, БД) — Pult

Ціль: один раз домовитись про назви, щоб схема даних, код і запити залишались читабельними при рості
функціоналу.

## Загальні правила

- **Мова**: у коді/БД — англійська, `snake_case`. В UI — українська.
- **Дефолти Django**: не задаємо `db_table`/`db_column`, якщо нема інтеграції з чужою БД.
- **Без прихованих фільтрів**: не робимо менеджери “лише активні” для довідників, якщо на них є FK
  (щоб не ламати доступ до історичних записів).

## Моделі (Python)

- **Імена класів**: `PascalCase`, однина, доменні імена: `Material`, `Supplier`, `MaterialRequestLine`.
- **Уникаємо двозначних слів**: не називати FK як `model`/`data`/`settings`. Краще
  `product_model`, `payload`, `config` (за потреби).

## Поля (Django models) → колонки в БД

### Первинні ключі

- **PK**: лишаємо Django default `id`. Тип визначається `DEFAULT_AUTO_FIELD`.

### Зовнішні ключі (ForeignKey / OneToOne)

- **Назва поля в моделі**: без суфікса `_id`: `material`, `supplier`, `created_by`.
- **Колонка в БД**: Django створює `<field>_id` (`material_id`, `created_by_id`).
- **`related_name`**: явний, множина, доменний:
  - `Material.offers` (`related_name="offers"`)
  - `Supplier.material_offers` (або `offers`, якщо це не конфліктує з іншими звʼязками)

### Час і архів

Єдина конвенція таймстемпів:
- `created_at`
- `updated_at`
- `archived_at` — soft-delete/архів (активні: `archived_at IS NULL`)

Не використовуємо `is_archived` як основний механізм, щоб мати дату архівації і прості фільтри.

### Логічні (boolean)

- Префікс `is_` / `has_`: `is_preferred`, `has_telegram`.

### Кількість

- **Тільки `quantity`**, не `qty`.
- Якщо зʼявляться різні величини: `requested_quantity`, `ordered_quantity`, `received_quantity`.

### Статуси / choices

- Поле: `status`.
- Значення: короткі `snake_case` рядки: `new`, `ordered`, `received`, `canceled`.
- У моделях: `models.TextChoices` (або еквівалент), UI-лейбли — українською.

### “Текст про всяк випадок”

- `notes` — універсальне поле для уточнень/особливостей (не плодити `comment/description`, якщо
  семантика однакова).

## Індекси та обмеження

- Додаємо `db_index=True` там, де реально фільтруємо/сортуємо (часто це `archived_at`, `status`).
- Явно задаємо `name=` для `Index`/`UniqueConstraint`.
- Тримаємо імена короткими (PostgreSQL має ліміт довжини імен, орієнтир ~63 символи).

Рекомендований формат (приклади):
- Індекс: `<app>_<entity>_<field>_idx` → `materials_request_status_idx`
- Unique: `<app>_<entity>_<purpose>_uniq` → `materials_offer_preferred_uniq` (якщо треба)

## Приклади (materials)

`SupplierMaterialOffer` (пропозиція постачальника для матеріалу):
- поля в моделі: `material`, `supplier`, `title`, `sku`, `url`, `notes`, `is_preferred`, `archived_at`
- колонки в БД: `material_id`, `supplier_id`, `title`, `sku`, `url`, `notes`, `is_preferred`,
  `archived_at`

`MaterialRequestLine`:
- поля в моделі: `request`, `material`, `quantity`, `notes`, `chosen_offer`
- колонки в БД: `request_id`, `material_id`, `quantity`, `notes`, `chosen_offer_id`

## Винятки

Якщо вже є історичне поле з “неідеальною” назвою (наприклад, `Order.model`), не перейменовуємо його
просто “для краси” без потреби. Новий код робимо по конвенції, перейменування плануємо окремо разом з
міграціями та перевіркою UI/API.

