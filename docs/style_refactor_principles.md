# Style Refactor Principles

Принципи UI-рефакторингу OrderFlow.
Це target state — не опис поточного коду.

## 1) Стек

- Tailwind CSS (standalone CLI, без Node).
- System font stack: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`.
- Іконки: Lucide (CDN або static copy).
- Bootstrap видаляється повністю після міграції всіх шаблонів.

## 2) Layout

- Desktop (md+): таблиця — щільна, сканабельна, всі колонки видимі.
- Mobile (<md): рядок таблиці стає stacked блоком (CSS-only через Tailwind responsive, без дублювання HTML).
- Один головний сценарій на екран. Другорядні дії — у контекстне меню або окремий екран.

## 3) Типографіка

- System font stack (нуль зовнішніх запитів, миттєвий рендер).
- Мінімум тексту в робочих списках: `text-sm` (14px).
- Одна шкала розмірів — Tailwind default scale (`text-xs` / `text-sm` / `text-base` / `text-lg`).

## 4) Кольори

Визначаються в `tailwind.config.js` як custom theme:
- Primary: `teal-700` (`#0F766E`)
- Accent: `amber-400` (`#F59E0B`)
- Background: `slate-50` (`#F8FAFC`)
- Surface: `white`
- Text: `slate-900` (`#0F172A`)

## 5) Статуси

Єдиний словник кольорів — один статус = один стиль у всьому проєкті.
Визначається в template tag, повертає готові Tailwind-класи:

| Статус | Badge classes |
|---|---|
| `new` | `bg-emerald-100 text-emerald-700` |
| `embroidery` | `bg-amber-100 text-amber-800` |
| `almost_finished` | `bg-blue-100 text-blue-700` |
| `finished` | `bg-slate-100 text-slate-600` |
| `on_hold` | `bg-red-100 text-red-700` |

## 6) Доступність

- Tap-target: мінімум 44x44 px для кнопок і інтерактивних елементів.
- Видимий focus state (`focus:ring-2 focus:ring-offset-2`).
- Стани loading / empty / error — завжди явні, з текстом і іконкою.
- Контраст: WCAG AA мінімум.

## 7) Django partials

Повторювані UI-блоки виносимо в `templates/partials/`:
- `status_badge.html` — бейдж статусу
- `order_row.html` — рядок таблиці замовлень (responsive)
- `empty_state.html` — стан "нічого не знайдено"
- `messages.html` — вже існує

## 8) Міграція з Bootstrap

1. Додати Tailwind CLI і `tailwind.config.js`.
2. Створити `static/css/input.css` з Tailwind directives.
3. Мігрувати шаблони по одному: `base.html` → `orders_active` → `orders_completed` → `order_detail` → решта.
4. Оновити `forms.py` — замінити Bootstrap widget classes на Tailwind.
5. Оновити template tags — замінити Bootstrap badge/alert класи на Tailwind.
6. Видалити Bootstrap CDN з `base.html`.

## 9) Definition of Done

1. Bootstrap повністю видалений.
2. На мобільному (360-430px) замовлення читаються без горизонтального скролу.
3. Основні дії доступні в 1-2 тапи.
4. Токени стилю в `tailwind.config.js`, хардкодів кольорів у шаблонах немає.
5. Візуальна консистентність на екранах: active, completed, detail.
6. Немає регресій у доступності (tap-target, контраст, focus, стани).
