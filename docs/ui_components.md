# UI Components Reference

Довідник по компонентах та шаблонах для швидкої розробки сторінок.

## Зміст

1. [Принципи](#принципи)
2. [Базові шаблони сторінок](#базові-шаблони-сторінок)
3. [Компоненти (Partials)](#компоненти-partials)
4. [CSS класи](#css-класи)
5. [Alpine.js](#alpinejs)
6. [Приклади сторінок](#приклади-сторінок)

---

## Принципи

### Mobile-first
- Базові стилі для мобільних
- `sm:`, `md:`, `lg:` для десктопу
- Touch targets мінімум 40px (min-h-10)

### Структура шаблонів
```
base.html                    # Головний layout (nav, main)
├── base_form_page.html      # Форми (centered, max-w-xl)
│   ├── base_edit_page.html  # Редагування з archive/unarchive
├── base_list_page.html      # Списки з фільтрами
├── base_detail_page.html    # Перегляд об'єкта
└── base_archive_page.html   # Архівні списки
```

### Іменування
- Шаблони: `app_name/action.html` (e.g., `materials/list.html`)
- Partials: `partials/component_name.html`
- CSS класи: `component-element` (e.g., `form-input`, `action-menu-item`)

---

## Базові шаблони сторінок

### base_list_page.html

Сторінка списку з фільтрами та пагінацією.

**Блоки:**
| Блок | Призначення |
|------|-------------|
| `page_title_text` | Заголовок сторінки |
| `page_header_actions` | Кнопки в хедері (+ Додати) |
| `filters` | Панель фільтрів |
| `list_header` | Заголовок таблиці/списку |
| `list_content` | Основний контент |
| `list_footer` | Пагінація, bulk actions |

**Приклад:**
```django
{% extends "base_list_page.html" %}

{% block page_title_text %}Матеріали{% endblock %}

{% block page_header_actions %}
<a href="{% url 'materials:create' %}" class="btn-primary">+ Додати</a>
{% endblock %}

{% block filters %}
{% include "partials/filter_bar.html" with search=True search_value=q clear_url="." %}
{% endblock %}

{% block list_header %}
<div class="hidden sm:grid sm:grid-cols-4 gap-4 px-4 py-2 bg-slate-50/80 border-b">
    <div class="text-xs font-medium uppercase text-slate-400">Назва</div>
    <div class="text-xs font-medium uppercase text-slate-400">Тип</div>
    <div class="text-xs font-medium uppercase text-slate-400">Кольорів</div>
    <div></div>
</div>
{% endblock %}

{% block list_content %}
{% for item in items %}
<div class="grid grid-cols-1 sm:grid-cols-4 gap-2 px-4 py-3 border-b border-slate-100 hover:bg-slate-50/80">
    <div class="font-medium text-slate-900">{{ item.name }}</div>
    <div class="text-sm text-slate-600">{{ item.type }}</div>
    <div class="text-sm text-slate-600">{{ item.colors_count }}</div>
    <div class="flex justify-end">
        {% include "partials/action_menu.html" with items=item.actions icon_only=True %}
    </div>
</div>
{% empty %}
{% include "partials/empty_state.html" with message="Матеріалів немає." %}
{% endfor %}
{% endblock %}

{% block list_footer %}
{% include "partials/pagination.html" %}
{% endblock %}
```

---

### base_detail_page.html

Сторінка перегляду одного об'єкта.

**Контекст:**
| Змінна | Тип | Опис |
|--------|-----|------|
| `back_url` | str | URL для кнопки "Назад" |
| `back_label` | str | Текст кнопки (default: "Назад") |

**Блоки:**
| Блок | Призначення |
|------|-------------|
| `page_title_text` | Заголовок |
| `page_header_actions` | Кнопки (Редагувати, Дії) |
| `detail_layout` | CSS класи для layout (default: 2/3 + 1/3) |
| `detail_content` | Основний контент (2/3) |
| `detail_sidebar` | Сайдбар (1/3) |
| `detail_footer` | Футер |

**Приклад:**
```django
{% extends "base_detail_page.html" %}

{% block page_title_text %}{{ object.name }}{% endblock %}

{% block page_header_actions %}
<a href="{% url 'edit' object.id %}" class="btn-secondary">Редагувати</a>
{% endblock %}

{% block detail_content %}
<div class="card p-4 space-y-2">
    {% include "partials/detail_field.html" with label="Назва" value=object.name %}
    {% include "partials/detail_field.html" with label="Статус" value=object.status badge=True badge_variant="success" %}
    {% include "partials/detail_field.html" with label="Опис" value=object.description multiline=True %}
</div>
{% endblock %}

{% block detail_sidebar %}
{% include "partials/stats_card.html" with label="Замовлень" value=object.orders_count icon="clipboard" %}
{% endblock %}
```

---

### base_form_page.html

Centered форма в картці.

**Блоки:**
| Блок | Призначення |
|------|-------------|
| `form_content` | Вміст форми |
| `form_page_footer` | Посилання під формою |

**Приклад:**
```django
{% extends "base_form_page.html" %}

{% block form_content %}
<form method="post" class="space-y-4">
    {% csrf_token %}
    {% include "partials/form_field.html" with field=form.name label="Назва" %}
    {% include "partials/form_field.html" with field=form.description label="Опис" %}
    <button type="submit" class="btn-primary w-full">Зберегти</button>
</form>
{% endblock %}

{% block form_page_footer %}
<p class="mt-4 text-center">
    <a href="{% url 'list' %}" class="link-back">← До списку</a>
</p>
{% endblock %}
```

---

## Компоненти (Partials)

### filter_bar.html

Панель фільтрів з пошуком.

**Параметри:**
| Параметр | Тип | Default | Опис |
|----------|-----|---------|------|
| `search` | bool | False | Показати поле пошуку |
| `search_name` | str | "q" | Ім'я параметра пошуку |
| `search_value` | str | "" | Поточне значення пошуку |
| `search_placeholder` | str | "Пошук..." | Placeholder |
| `filters` | Form | None | Django форма з фільтрами |
| `clear_url` | str | None | URL для очистки фільтрів |
| `action_url` | str | "" | Form action URL |

**Приклад:**
```django
{% include "partials/filter_bar.html" with
    search=True
    search_value=request.GET.q
    clear_url="{% url 'list' %}"
%}
```

**З dropdown фільтрами:**
```django
{% include "partials/filter_bar.html" with search=True %}
{% block extra_filters %}
<select name="status" class="form-select w-auto">
    <option value="">Всі статуси</option>
    <option value="active">Активні</option>
    <option value="archived">В архіві</option>
</select>
{% endblock %}
{% endinclude %}
```

---

### action_menu.html

Dropdown меню з діями (Alpine.js).

**Параметри:**
| Параметр | Тип | Default | Опис |
|----------|-----|---------|------|
| `items` | list | [] | Список дій |
| `label` | str | "Дії" | Текст кнопки |
| `icon_only` | bool | False | Тільки іконка |
| `align` | str | "right" | Вирівнювання ("left"/"right") |

**Структура items:**
```python
actions = [
    {"label": "Редагувати", "url": "/edit/", "icon": "edit"},
    {"label": "Копіювати", "url": "/copy/", "icon": "copy"},
    {"divider": True},
    {"label": "В архів", "url": "/archive/", "method": "post", "icon": "archive"},
    {"label": "Видалити", "url": "/delete/", "icon": "trash", "danger": True, "confirm": "Видалити?"},
]
```

**Доступні іконки:** `edit`, `trash`, `archive`, `restore`, `eye`, `copy`, `download`, `external`, `plus`, `check`

**Приклад:**
```django
{# Кнопка з текстом #}
{% include "partials/action_menu.html" with items=actions label="Дії" %}

{# Тільки іконка (для таблиць) #}
{% include "partials/action_menu.html" with items=actions icon_only=True %}

{# Вирівнювання вліво #}
{% include "partials/action_menu.html" with items=actions align="left" %}
```

---

### badge.html

Універсальний badge/tag.

**Параметри:**
| Параметр | Тип | Default | Опис |
|----------|-----|---------|------|
| `label` | str | required | Текст |
| `variant` | str | "default" | Колір |
| `size` | str | "md" | Розмір ("sm"/"md") |
| `pill` | bool | False | Округлий |
| `dot` | bool | False | З кольоровою крапкою |
| `icon` | str | None | Іконка ("external"/"check"/"clock") |

**Варіанти кольорів:**
| Variant | Колір |
|---------|-------|
| `default` | Сірий |
| `primary` | Teal (brand) |
| `success` | Зелений |
| `warning` | Жовтий |
| `danger` | Червоний |
| `info` | Синій |
| `muted` | Світло-сірий |

**Приклади:**
```django
{% include "partials/badge.html" with label="Нове" variant="success" %}
{% include "partials/badge.html" with label="Архів" variant="muted" size="sm" %}
{% include "partials/badge.html" with label="В роботі" variant="info" dot=True %}
{% include "partials/badge.html" with label="Etsy" variant="warning" icon="external" %}
```

---

### stats_card.html

Картка статистики.

**Параметри:**
| Параметр | Тип | Default | Опис |
|----------|-----|---------|------|
| `label` | str | required | Назва метрики |
| `value` | str | required | Значення |
| `sublabel` | str | None | Додатковий текст |
| `icon` | str | None | Іконка |
| `trend` | str | None | Тренд ("+5", "-2%") |
| `trend_up` | bool | None | Позитивний тренд (зелений) |
| `href` | str | None | URL для клікабельної картки |
| `variant` | str | "default" | Колір іконки |

**Доступні іконки:** `clipboard`, `check`, `clock`, `cube`/`inventory`, `truck`, `users`, `currency`/`money`, `alert`/`warning`, `scissors`/`cutting`

**Приклади:**
```django
{% include "partials/stats_card.html" with label="В роботі" value="12" icon="clipboard" %}
{% include "partials/stats_card.html" with label="Готово" value="45" trend="+5" trend_up=True icon="check" variant="success" %}
{% include "partials/stats_card.html" with label="Проблеми" value="3" icon="alert" variant="danger" href="/issues/" %}
```

**Dashboard grid:**
```django
<div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
    {% include "partials/stats_card.html" with label="Замовлень" value=orders_count icon="clipboard" %}
    {% include "partials/stats_card.html" with label="В роботі" value=in_progress icon="clock" %}
    {% include "partials/stats_card.html" with label="Готово" value=completed icon="check" variant="success" %}
    {% include "partials/stats_card.html" with label="WIP" value=wip_count icon="scissors" variant="warning" %}
</div>
```

---

### tabs.html

Горизонтальні таби.

**Параметри:**
| Параметр | Тип | Default | Опис |
|----------|-----|---------|------|
| `tabs` | list | required | Список табів |
| `active` | str | None | ID активного табу |
| `variant` | str | "underline" | Стиль ("underline"/"pills") |

**Структура tabs:**
```python
tabs = [
    {"id": "active", "label": "Активні", "url": "/list/", "count": 12},
    {"id": "archive", "label": "Архів", "url": "/archive/", "badge": "3"},
]
```

**Приклад:**
```django
{% include "partials/tabs.html" with tabs=tab_items active="active" %}
{% include "partials/tabs.html" with tabs=tab_items active=current_tab variant="pills" %}
```

---

### detail_field.html

Поле key-value для сторінок деталей.

**Параметри:**
| Параметр | Тип | Default | Опис |
|----------|-----|---------|------|
| `label` | str | required | Назва поля |
| `value` | any | required | Значення |
| `badge` | bool | False | Показати як badge |
| `badge_variant` | str | "default" | Колір badge |
| `multiline` | bool | False | Дозволити перенос |
| `muted` | bool | False | Приглушений колір |
| `href` | str | None | URL для посилання |
| `empty_text` | str | "—" | Текст якщо пусто |

**Приклади:**
```django
{% include "partials/detail_field.html" with label="Назва" value=object.name %}
{% include "partials/detail_field.html" with label="Статус" value="Активний" badge=True badge_variant="success" %}
{% include "partials/detail_field.html" with label="Клієнт" value=object.customer.name href=object.customer.get_absolute_url %}
{% include "partials/detail_field.html" with label="Опис" value=object.description multiline=True %}
{% include "partials/detail_field.html" with label="Створено" value=object.created_at muted=True %}
```

---

### section_card.html

Картка з заголовком та опціональними діями.

**Параметри:**
| Параметр | Тип | Default | Опис |
|----------|-----|---------|------|
| `title` | str | None | Заголовок |
| `subtitle` | str | None | Підзаголовок |
| `action_url` | str | None | URL дії |
| `action_label` | str | "Додати" | Текст дії |
| `padding` | bool | True | Padding на контенті |
| `divided` | bool | True | Роздільник під хедером |

**Блоки:**
- `card_header_actions` — додаткові дії в хедері
- `card_content` — основний контент
- `card_footer` — футер

**Приклад:**
```django
{% include "partials/section_card.html" with title="Матеріали" action_url="/add/" action_label="Додати" %}
{% block card_content %}
<ul class="divide-y divide-slate-100">
    {% for item in materials %}
    <li class="py-2">{{ item.name }}</li>
    {% endfor %}
</ul>
{% endblock %}
{% endinclude %}
```

---

### Інші partials

| Partial | Опис |
|---------|------|
| `form_field.html` | Поле форми з label та errors |
| `form_checkbox_option.html` | Checkbox з label |
| `empty_state.html` | Пусте повідомлення |
| `pagination.html` | Пагінація |
| `messages.html` | Django messages |
| `modal_confirm.html` | Модальне вікно підтвердження |
| `status_indicator.html` | Індикатор статусу |

---

## CSS класи

### Кнопки

| Клас | Опис |
|------|------|
| `btn-primary` | Основна кнопка (teal, gradient) |
| `btn-secondary` | Вторинна кнопка (white, border) |

```html
<button class="btn-primary">Зберегти</button>
<a href="#" class="btn-secondary">Скасувати</a>
```

### Форми

| Клас | Опис |
|------|------|
| `form-label` | Label поля |
| `form-input` | Text input |
| `form-select` | Select dropdown |
| `form-textarea` | Textarea |
| `form-checkbox` | Checkbox |
| `form-error` | Повідомлення помилки |

### Layout

| Клас | Опис |
|------|------|
| `card` | Картка (border, shadow, rounded) |
| `form-card-body` | Padding для форми в картці |

### Посилання

| Клас | Опис |
|------|------|
| `link-back` | Посилання "назад" (teal) |
| `link-muted` | Приглушене посилання |

### Alerts

| Клас | Опис |
|------|------|
| `alert` | Базовий alert |
| `alert-success` | Зелений |
| `alert-warning` | Жовтий |
| `alert-error` | Червоний |
| `alert-info` | Синій |

---

## Alpine.js

Alpine.js підключено в `base.html`. Використовуй для інтерактивності.

### Приклади

**Toggle:**
```html
<div x-data="{ open: false }">
    <button @click="open = !open">Toggle</button>
    <div x-show="open">Content</div>
</div>
```

**Dropdown:**
```html
<div x-data="{ open: false }" @click.away="open = false">
    <button @click="open = !open">Menu</button>
    <div x-show="open" x-transition x-cloak>
        <a href="#">Item 1</a>
        <a href="#">Item 2</a>
    </div>
</div>
```

**Conditional class:**
```html
<div :class="{ 'bg-teal-100': selected }">...</div>
```

**Важливо:** Додай `x-cloak` на елементи які повинні бути приховані до ініціалізації Alpine.

---

## Приклади сторінок

Повні приклади в `frontend/templates/examples/`:

| Файл | Опис |
|------|------|
| `list_page_example.html` | Список з таблицею |
| `detail_page_example.html` | Сторінка деталей |
| `dashboard_example.html` | Dashboard |

---

## Швидкий старт

### Новий список

1. Створи `app/templates/app/list.html`
2. Extend `base_list_page.html`
3. Додай блоки: `page_header_actions`, `filters`, `list_content`
4. Використай `filter_bar.html`, `action_menu.html`, `badge.html`

### Нова сторінка деталей

1. Створи `app/templates/app/detail.html`
2. Extend `base_detail_page.html`
3. Додай блоки: `detail_content`, `detail_sidebar`
4. Використай `detail_field.html`, `section_card.html`, `stats_card.html`

### Нова форма

1. Створи `app/templates/app/create.html`
2. Extend `base_form_page.html`
3. Додай блок `form_content` з формою
4. Використай `form_field.html` для полів

---

## Build CSS

Після змін в `input.css`:

```bash
make tw-build      # Одноразова збірка
make tw-watch      # Watch mode
```
