# Style Decisions

Принципи стилю та неймінгу для рефакторингу OrderFlow.
Це target state — не опис поточного коду.

## 1) Неймінг

- `snake_case` для Python, URL names, template filenames.
- Імена предметні, відображають бізнес-сенс.
- Без технічних суфіксів (`list_create`, `detail_update`).
- Без нечітких імен: не `settings` (якщо не Django settings), не `models` (якщо список продуктів), не `data` (якщо зміст конкретний).

Target URL names (поточне → target):
- `current_orders_list` → `orders_active`
- `finished_orders_list` → `orders_completed`
- `order_create` → `orders_create`
- `order_detail` — без змін
- `model_list` → `product_models`
- `color_list` → `colors`
- `color_detail_update` → `color_edit`

## 2) Views

- FBV за замовчуванням.
- CBV — тільки коли Django generic view покриває логіку без суттєвих overrides.
- Один view = одна відповідальність (не змішувати list + bulk update в одній функції).

## 3) Шаблони

- Групуємо за доменом: `templates/orders/`, `templates/catalog/`, `templates/account/`.
- Один template = одна сторінка/екран.
- Назва шаблону відображає бізнес-сенс, а не тип Django view.

## 4) CSS / JS

- Tailwind CSS (standalone CLI, без Node).
- Жодної робочої логіки в inline `<script>`.
- Жодних постійних стилів в inline `style=""`.
- Tailwind input: `assets/tailwind/input.css`. Output: `static/css/app.css`.
- Сторінковий JS: `static/js/<page_name>.js`.
- Кольори, шрифти, кастомні токени — в `tailwind.config.js`.
- Template tags повертають Tailwind utility-класи, а не Bootstrap-специфічні (`bg-success`).

## 5) Мова

- У коді: англійська.
- В UI: українська.
- Один термін = одне значення в усьому проєкті.

## 6) Code style

- Форматтер: `ruff format`.
- Лінтер: `ruff check`.
- Enforcement: pre-commit hooks.
