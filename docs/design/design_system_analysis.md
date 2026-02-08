# Аналіз дизайн-системи та шаблонів OrderFlow

Погляд на шаблони та CSS з точки зору стабільності, гнучкості та швидкості розробки. Мета — система, яка дозволяє додавати фічі без затримок на прийняття рішень.

---

## 1. Що вже добре (best practices на місці)

### 1.1 Один джерело правди для стилів
- **`assets/tailwind/input.css`** — єдине місце для компонентів (`.form-*`, `.card`, `.btn-*`, `.detail-*`, `.modal-*`). Немає розкиданих інлайн-стилів у шаблонах.
- **`@theme`** — базові токени (кольори, шрифт) в одному блоці.
- **Статуси** — визначені в домені (`order_statuses.py`), UI-мапа в template tag; новий статус = одна зміна в коді, нуль змін у шаблонах.

### 1.2 Переиспользуемые блоки
- **Partials** — `card_section_header`, `empty_state`, `messages`, `modal_confirm`, `order_row`, `status_indicator`, `pagination` дають консистентний вигляд і один пункт зміни.
- **Template tags** — `status_indicator`, `message_alert_class` приховують складні умови та класи; шаблон лише викликає тег.

### 1.3 Форми та доступність
- Єдина система форм: `form-label`, `form-input`, `form-error`, `form-checkbox`, `form-select-*`, `form-textarea`. Новий інпут = додати клас з документації.
- Мінімальний tap-target (наприклад `min-h-10`, `min-h-[44px]` де потрібно), `sr-only`, `aria-current`, `aria-hidden` використовуються коректно.
- Focus states є у кнопок і полів (`focus:ring-2`, `focus:ring-teal-500`).

### 1.4 Layout
- Чітке розділення: бар (`max-w-5xl`), контент (`.main-content` = `max-w-2xl`), центровані сторінки (`.main-centered` + внутрішній `max-w-2xl`). Ширина не «роз'їжджається».
- Контейнери через класи, а не хардкод px у шаблонах.

### 1.5 Документація
- `style_refactor_principles.md` і `style_decisions.md` задають напрямок (стек, кольори, неймінг, партиали). Це вже основа для «не думати кожен раз».

---

## 2. Проблеми та ризики (де можна втрачати час або ламати консистентність)

### 2.1 Дублювання навігації в base.html
- Один і той самий набір лінків з дуже довгими умовами повторюється **двічі**: desktop (рядок 56–70) і mobile (85–98).
- Ризик: додав новий пункт меню — забув оновити друге місце; різні класи (наприклад `block` тільки в mobile) — легко роз'їхатися.
- **Рекомендація:** винести один пункт навігації в partial або template tag (параметри: `url_name`, `label`, `url`). У `base.html` — два цикли (desktop / mobile) по одному списку даних. Умова `current_url == url_name` і класи active/default в одному місці.

### 2.2 Різні способи обгортання форм
- **Профіль, пароль, create, order_edit:** `mx-auto max-w-xl` + `card` + `form-card-body` + форма.
- **catalog/colors:** форма всередині `card form-card-body` без зовнішнього `max-w-xl` (контент уже в `.main-content`).
- **color_edit:** `mx-auto max-w-xl` + форма без card (лише в change_password додали card).
- Наслідок: для кожної нової форми виникає питання — чи потрібна картка, чи потрібен max-w-xl, чи це вже дасть base. Легко отримати візуальну непослідовність.

### 2.3 Кольори primary/accent не через змінні
- У `@theme` є `--color-primary`, `--color-accent`, але в шаблонах і навігації використовуються конкретні класи (`text-teal-600`, `bg-teal-50`, `text-teal-700`).
- Кнопки вже опираються на `--color-teal-600` у компоненті. Якщо колись захочеш змінити primary — доведеться шукати по всьому проєкту.
- **Рекомендація:** поступово переходити на використання змінних у компонентах (наприклад `var(--color-primary)`), а в `@theme` мапінг на конкретний колір. Тоді зміна теми = зміна одного блоку.

### 2.4 Таблиці без спільного паттерну
- Стилі таблиць (header: `bg-slate-50/80`, `text-xs uppercase tracking-wider text-slate-400`, клітинки: `px-4 py-2`, `divide-y`) повторюються в `orders/detail.html`, `orders/completed.html`, в `orders/active.html` — картка з іншим header, але схожа ідея.
- Немає класів типу `.data-table`, `.data-table-header`, `.data-table-cell`. Кожна нова таблиця — копіювання або пригадування, що саме ставити.

### 2.5 Паттерн чекбоксів у формах
- У `create.html` і `order_edit.html` однаковий блок: три чекбокси (Etsy, Вишивка, Терміново) з `flex flex-wrap gap-x-6 gap-y-2`, `label` з `gap-2`, `text-sm font-medium text-slate-700`. При додаванні четвертого опціону або новій формі з такими ж опціями — знову копіювання.

### 2.6 Empty state і пагінація
- `empty_state.html` — це картка з кастомним падінгом (`px-6 py-12`) і текстом. Якщо з'явиться ще один «порожній стан» з іншим текстом — можна використати partial, але сам стиль «великий падінг по центру» не винесений у клас типу `.card-empty` або `.empty-state`.
- У `pagination.html` стиль disabled-кнопки (стрілки) заданий інлайн-класами; якщо такий же вигляд потрібен ще десь — краще клас `.btn-disabled` або розширення `.btn-secondary:disabled`.

### 2.7 Немає явного «каталогу компонентів»
- Є опис принципів, але немає короткого довідника: «форма сторінки = цей wrapper», «таблиця = ці класи», «кнопка назад = link-back». Розробник щоразу згадує з існуючих шаблонів або питає себе.

---

## 3. Рекомендації: практики та рефактори

### 3.1 Швидкі (низький поріг)
1. **Додати один документ «Компоненти та коли їх використовувати»** (див. [design_components.md](design_components.md)):
   - Секції: Layout (main-content, main-centered, page-narrow), Cards (card, form-card-body), Forms (form-label, form-input, form-error, form-checkbox), Buttons (btn-primary, btn-secondary), Links (link-back, link-muted), Alerts, Modal, Tables, Empty state, Pagination.
   - Для кожної — один приклад використання та «коли брати саме це». Це знімає 80% питань при новій фічі.

2. **Чекліст для нової сторінки/форми** — в [design_components.md](design_components.md).

3. **Залишити в base.html один коментар** над `<main>`: посилання на design_components.md.

### 3.2 Середні (рефактори на 1–2 години)
4. **Єдиний partial для пункту навігації** — ✅ Зроблено: `partials/nav_item.html` + тег `get_nav_items` (список `NAV_ITEMS` у `order_ui.py`). Desktop і mobile рендерять з одного списку.
5. **Паттерн «форма-сторінка»** — ✅ Зроблено: `base_form_page.html` (extends base), блоки `form_content` і `form_page_footer`. create, order_edit, change_password переходять на нього.
6. **Класи для таблиць** — `.data-table`, `.data-table-header`, `.data-table-cell` в input.css.

### 3.3 Довгострокові (якщо буде час)
7. **Primary/accent через CSS-змінні.**
8. **Партіал для рядка чекбоксів (опційно).**
9. **Empty state як компонент** — клас `.empty-state` / `.card-empty`.

---

## 4. Чекліст «Нова фіча без зупинок»

Див. [design_components.md](design_components.md) — секція «Чеклісти для нових сторінок».

---

## 5. Підсумок

| Що є | Що варто додати |
|------|------------------|
| Єдина точка правди для компонентів (input.css) | Документ «компоненти + коли використовувати» |
| Partials і template tags для статусів/повідомлень | Один partial для пункту навігації (прибрати дублювання) |
| Консистентні форми та кнопки | Єдиний паттерн обгортки форми (form page wrapper) |
| Layout main-content / main-centered | Класи для таблиць (.data-table) |
| Принципи в style_refactor / style_decisions | Чекліст для нової сторінки/форми та посилання з README |
