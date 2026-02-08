# Implementation Roadmap

Порядок дій для UI-рефакторингу OrderFlow.
Базується на: [docs/design/](design/) (design_components.md, style_decisions.md).

## Phase 1: Інфраструктура

**Ціль:** Tailwind працює, base template мігрований, фундамент готовий.

1. Встановити Tailwind standalone CLI (`bin/tailwindcss`, додати в `.gitignore`).
2. Створити `tailwind.config.js` — content: `./templates/**/*.html`, custom theme (палітра, system fonts).
3. Створити `assets/tailwind/input.css` з Tailwind directives.
4. Додати `STATICFILES_DIRS = [BASE_DIR / "static"]` в `settings/base.py`.
5. Додати Makefile targets: `tw-watch` (dev), `tw-build` (prod minified).
6. Мігрувати `base.html` — layout, навігація на Tailwind. Bootstrap CDN лишається тимчасово.
7. Оновити `order_ui.py` — status badge і alert класи → Tailwind.
8. Оновити `forms.py` — widget attrs → Tailwind класи.

**Рішення:**
- `static/css/app.css` (generated) — committed to git. Tailwind CLI не потрібен у Docker/CI.
- Bootstrap і Tailwind співіснують до Phase 4.
- ruff і pre-commit вже працюють (Makefile: `lint`, `format`). Додати `.pre-commit-config.yaml` для автоматизації.

**Commit:** 1-2 коміти.

## Phase 2: Шаблони замовлень

**Ціль:** основні робочі екрани на Tailwind, responsive table працює.

Кожен шаблон мігрується повністю за один коміт:
template path + URL name + view name + Tailwind стилі + JS extraction.

1. `current_orders_list` → `orders_active`
   - Template: `templates/orders/active.html`
   - URL name: `current_orders_list` → `orders_active`
   - View: `current_orders_list()` → `orders_active()` (тільки list; bulk update — окремий view `orders_bulk_status()`)
   - Responsive table: `<table>` на md+, stacked rows на mobile.
   - JS → `static/js/orders_active.js`.
   - Створити partials: `status_badge.html`, `order_row.html`.
2. `order_detail` → `order_detail`
   - Template: `templates/orders/detail.html`
   - URL name: без змін.
3. `finished_orders_list` → `orders_completed`
   - Template: `templates/orders/completed.html`
   - URL name: `finished_orders_list` → `orders_completed`
   - View: `finished_orders_list()` → `orders_completed()`
   - Створити partial: `empty_state.html`.
4. `order_create` → `orders_create`
   - Template: `templates/orders/create.html`
   - URL name: `order_create` → `orders_create`
   - View: `order_create()` → `orders_create()`
   - JS → `static/js/orders_create.js`.

**Commit:** 1 коміт на шаблон. Кожен коміт оновлює urls.py, views.py, template, tests.

## Phase 3: Решта шаблонів

Той самий підхід: template path + URL name + view name + Tailwind за один коміт.

Account:
5. `login` → `auth_login` (без змін URL name)
   - Template: `templates/account/login.html`
6. `profile` → `profile` (без змін)
   - Template: `templates/account/profile.html`
   - JS → `static/js/profile.js`.
7. `change_password` → `change_password` (без змін)
   - Template: `templates/account/change_password.html`
8. Налаштування сповіщень — об'єднано з профілем (`profile`)

Catalog:
9. `model_list` → `product_models`
   - Template: `templates/catalog/product_models.html`
   - URL name: `model_list` → `product_models`
10. `color_list` → `colors`
    - Template: `templates/catalog/colors.html`
    - URL name: `color_list` → `colors`
11. `color_detail_update` → `color_edit`
    - Template: `templates/catalog/color_edit.html`
    - URL name: `color_detail_update` → `color_edit`

**Commit:** по домену (account — 1 коміт, catalog — 1 коміт).

## Phase 4: Cleanup

1. Видалити Bootstrap CDN з `base.html`.
2. Видалити старі template файли з кореня `templates/`.
3. Прибрати `index` view (redirect) — замінити на `orders_active` як default.
4. Оновити tests — фінальна перевірка template paths, URL names.

**Commit:** 1 коміт.

## Phase 5: Верифікація

1. Всі екрани: mobile (360-430px) без горизонтального скролу.
2. Accessibility: tap-targets 44px, focus states, contrast WCAG AA.
3. Жодних inline `<script>` і `style=""` в шаблонах.
4. Жодних Bootstrap-класів у коді.
5. Токени стилю тільки з `tailwind.config.js`, хардкодів кольорів немає.

## Правила виконання

- Один коміт = повна міграція одного шаблону (template path + URL name + view name + Tailwind + JS).
- Кожен коміт: перевірка на mobile + desktop.
- Після кожного коміту: `make test` проходить, додаток працює.
- Bootstrap і Tailwind співіснують до Phase 4 — очікувано.
