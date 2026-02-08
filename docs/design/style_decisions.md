# Style Decisions

Принципи стилю та неймінгу для рефакторингу Pult.
Це target state — не опис поточного коду.

## 1) Неймінг

- `snake_case` для Python, URL names, template filenames.
- Імена предметні, відображають бізнес-сенс.
- Без технічних суфіксів (`list_create`, `detail_update`).
- Без нечітких імен: не `settings` (якщо не Django settings), не `models` (якщо список продуктів), не `data` (якщо зміст конкретний).

Приклад URL names: `orders_active`, `orders_completed`, `orders_create`, `order_detail`, `product_models`, `colors`, `color_edit`.

## 2) Views

- FBV за замовчуванням.
- CBV — тільки коли Django generic view покриває логіку без суттєвих overrides.
- Один view = одна відповідальність (не змішувати list + bulk update в одній функції).

## 3) Шаблони

- Групуємо за доменом: `templates/orders/`, `templates/catalog/`, `templates/account/`.
- Один template = одна сторінка/екран.
- Назва шаблону відображає бізнес-сенс, а не тип Django view.

## 4) CSS / JS

- Tailwind CSS (v4, standalone CLI).
- Input: `assets/tailwind/input.css`. Output: `static/css/app.css`. Токени (кольори, відступи, тіні) — у блоці `@theme` в input.css.
- Сторінковий JS: `static/js/<page_name>.js`.
- Без постійних стилів у `style=""` і без робочої логіки в inline `<script>`.
- Template tags повертають Tailwind-класи (наприклад з `order_statuses`).

## 5) Мова

- У коді: англійська.
- В UI: українська.
- Один термін = одне значення в усьому проєкті.

## 6) Code style

- Форматтер: `ruff format`.
- Лінтер: `ruff check`.
- Enforcement: pre-commit hooks.
