# Компоненти та коли їх використовувати

Короткий довідник: який клас або partial взяти, щоб нова сторінка/форма виглядала так само, як решта застосунку. Деталі стилів — у `assets/tailwind/input.css`.

---

## Layout

| Що | Коли використовувати |
|----|----------------------|
| **Контент за замовчуванням** | Base вже дає `.main-content` (max-width 672px, по центру). Нічого додавати не треба. |
| **Центрована сторінка** (вхід, нове замовлення) | У view передати `page_title_center=True`. Base дасть `.main-centered` і внутрішній `max-w-2xl`. |
| **Сторінка з однією формою в картці** | Розширюй **`base_form_page.html`** замість `base.html`. Перевизнач блоки `form_content` (форма) і при потребі `form_page_footer` (наприклад посилання «Назад»). Приклад: створення замовлення, редагування замовлення, зміна пароля. |
| **Вужча колонка для форми вручну** | Якщо не підходить base_form_page (наприклад кілька карток): `div.mx-auto.max-w-xl` → `div.card` → `div.form-card-body`. Приклад: профіль. |

---

## Картки та секції

| Клас / partial | Коли |
|----------------|------|
| **`.card`** | Білий блок з тінню і рамкою. Всі контентні блоки (список замовлень, деталі, форма) всередині card. |
| **`.form-card-body`** | Внутрішній падінг картки для форм. Завжди разом з `.card`: `<div class="card"><div class="form-card-body">...</div></div>`. |
| **`partials/card_section_header.html`** | Заголовок секції в картці + опційно кнопка «Підправити». Параметри: `title`, `edit_url` (опційно). |

---

## Форми

| Клас | Де використовувати |
|------|--------------------|
| **`.form-label`** | Лейбл для поля (block, вище поля). |
| **`.form-input`** | Текстове поле, число. |
| **`.form-select`** | Звичайний select. Для кастомного dropdown — `.form-select-wrap` + trigger/dropdown (див. input.css). |
| **`.form-textarea`** | Багаторядкове поле. |
| **`.form-checkbox`** | Чекбокс. У рядку з текстом: `<label class="flex items-center gap-2 cursor-pointer">{{ field }}<span class="text-sm font-medium text-slate-700">Текст</span></label>`. |
| **`.form-error`** | Під полем після помилки валідації: `<p class="form-error">{{ form.field.errors.0 }}</p>`. |

Чекбокси в один ряд: обгортка `div.flex.flex-wrap.items-center.gap-x-6.gap-y-2`, кожен пункт — **`{% include "partials/form_checkbox_option.html" with field=form.field_name label="Текст" %}`**. Помилки для кількох полів — один `form-error` після блоку (наприклад `form.etsy.errors|default:form.embroidery.errors|default:...`).

---

## Кнопки та посилання

| Клас | Коли |
|------|------|
| **`.btn-primary`** | Головна дія: відправити форму, створити, зберегти. |
| **`.btn-secondary`** | Другорядна дія: скасувати, назад, фільтр. |
| **`.link-back`** | Текстовий лінк «Назад» (наприклад з деталей замовлення). |
| **`.link-muted`** | Тихі посилання (наприклад допоміжні). |

---

## Повідомлення та стани

| Що | Коли |
|----|------|
| **`{% include "partials/messages.html" %}`** | На початку контенту кожної сторінки (Django messages). |
| **`{% include "partials/empty_state.html" with message="Текст" %}`** | Порожній список або «нічого не знайдено». Стиль задає клас `.empty-state` (картка з центрованим текстом). |
| **`{% include "partials/modal_confirm.html" with id="..." title="..." confirm_label="..." cancel_label="..." %}`** | Діалог підтвердження. Текст повідомлення задається з JS у елемент з id `{{ id }}-message`. |

---

## Списки та таблиці

| Що | Коли |
|----|------|
| **`partials/order_row.html`** | Рядок замовлення в списку (з чекбоксом і статусом). |
| **`{% status_indicator status display_label %}`** | Індикатор статусу (текст + крапка/іконка). Для списків: `muted=1`. |
| **`partials/pagination.html`** | Пагінація. Передати: `page_obj`, опційно `query_string`, опційно `aria_label`. |

**Таблиця:** обгортка `div.card` → `div.overflow-x-auto` → `<table class="data-table">`. Заголовки в `thead`/`th` і клітинки в `tbody`/`td` отримують стилі з компонента. Для приглушеного тексту в клітинці додай `class="text-slate-500"` або `text-slate-700` на `td`. Рядки мають hover по замовчуванню.

---

## Детал-сторінка (опис об'єкта)

- Картка з **`card_section_header`** (title, edit_url).
- Тіло: **`.detail-card-body`** → блоки **`.detail-group`** → рядки **`.detail-row`** з **`.detail-dt`** (назва поля) і **`.detail-dd`** (значення) або **`.detail-hero`** (головне значення, наприклад модель · колір).
- Заголовок групи: **`.detail-group-title`** (наприклад «Замовлення», «Дати»).

---

## Чеклісти для нових сторінок

### Нова сторінка з однією формою в картці
- [ ] Шаблон: **`{% extends "base_form_page.html" %}`**. Перевизначити `{% block form_content %}` (форма) і при потребі `{% block form_page_footer %}` (наприклад link-back).
- [ ] View: передати `page_title`; для центрованого екрану — `page_title_center=True`.
- [ ] Поля: `form-label` + `form-input`/`form-select`/`form-textarea`/`form-checkbox` + під полем `form-error` при помилках.
- [ ] Кнопки: `btn-primary` (submit), `btn-secondary` (скасувати/назад).

### Нова сторінка-список
- [ ] `messages` → фільтр/пошук (якщо є) → одна `card` з заголовком (`card_section_header`) або без.
- [ ] Тіло: таблиця або цикл по partial (наприклад `order_row`).
- [ ] Порожній список: `{% include "partials/empty_state.html" with message="..." %}`.
- [ ] Якщо є пагінація: `{% include "partials/pagination.html" %}`.

### Нова детал-сторінка
- [ ] `messages` → одна або кілька `card` з `card_section_header` (title, опційно edit_url).
- [ ] Контент: `detail-card-body` → `detail-group` → `detail-row` з `detail-dt` / `detail-dd` (або `detail-hero`).
- [ ] Назад: посилання з класом `link-back`.

### Новий пункт меню
- [ ] Додати один запис у список `NAV_ITEMS` у `orders/templatetags/order_ui.py` (url_name, label, active_on — кортеж url_name, для яких пункт вважається активним).
- [ ] Переконатися, що view передає потрібний `page_title`. Шаблони не змінювати — desktop і mobile беруть пункти з одного списку.

### Новий статус (замовлення)
- [ ] Додати визначення в `orders/domain/order_statuses.py` (код, label, icon, indicator_class, text_class, badge_class).
- [ ] У шаблонах нічого не міняти — використовувати `status_indicator` / бейдж як раніше.
