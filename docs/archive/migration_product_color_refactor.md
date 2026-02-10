# Міграція: Product/Color -> Material + MaterialColor

## Ціль

Перейти з legacy-моделі `catalog.Color` (один універсальний колір) на модель:

- `materials.Material`
- `materials.MaterialColor`
- `catalog.ProductModel.primary_material`
- `catalog.ProductModel.secondary_material` (optional)
- primary/secondary material colors в замовленнях, виробництві та складі
- `BundlePreset` для фіксованих бандл-комбінацій

Legacy `catalog.Color` зберігається тимчасово для сумісності.

## Уже зроблено в коді

1. Додано нові моделі і поля:
- `materials.MaterialColor`
- `materials.ProductMaterial` (BOM-норми на одиницю продукту з `unit`)
- `catalog.ProductModel.primary_material/secondary_material`
- `catalog.BundlePreset`, `catalog.BundlePresetComponent`
- `customer_orders` primary/secondary material color поля
- `orders.Order` primary/secondary material color поля
- `inventory.StockRecord` ключ по material colors (паралельно з legacy color)

3. Додано сервіс розрахунку потреби матеріалів:
- `apps.materials.services.calculate_material_requirements_for_customer_order_line`
- працює для звичайних товарів і бандлів (через `BundleComponent`)

2. У сервісах ввімкнено fallback:
- якщо є `MaterialColor` -> використовуємо новий шлях
- якщо немає -> працює legacy `Color`

## План міграції даних

### Фаза 1. Підготовка довідників (ручна/напівавтомат)

1. Створити/уточнити `Material`:
- `Felt`
- `Leather smooth`
- інші фактичні матеріали

2. Створити `MaterialColor` для кожного матеріалу окремо.

3. Для кожного `ProductModel` проставити:
- `primary_material` (обов'язково)
- `secondary_material` (де треба, зазвичай для шкіряного елемента)

### Фаза 2. Backfill історичних даних

Backfill робити батчами в транзакціях (id-range), порядок:

1. `customer_orders.CustomerOrderLine`
- якщо `primary_material_color` порожній і є legacy `color`, заповнити `primary_material_color`
  через мапу `(product.primary_material, legacy_color.name/code) -> MaterialColor`.

2. `customer_orders.CustomerOrderLineComponent`
- аналогічно: переносимо `color` -> `primary_material_color` за матеріалом компонента.

3. `orders.Order`
- якщо `primary_material_color` порожній і є `color`, перенести в `primary_material_color`.

4. `inventory.StockRecord`
- для рядків з legacy `color` заповнити `primary_material_color`.

5. Валідаційний звіт:
- кількість рядків без зіставлення;
- колізії (один legacy color -> кілька MaterialColor);
- продукти без `primary_material`.

### Фаза 3. Режим dual-write

Після backfill тимчасово тримати dual-write:

1. Нові записи створюються через `MaterialColor`.
2. Legacy `Color` читається лише як fallback для старих рядків.
3. Нові бізнес-процеси (особливо wholesale) вводити тільки через нові поля.

### Фаза 4. Cutover

1. Заборонити створення нових записів без `primary_material_color`.
2. Прибрати використання `color` з сервісів читання/розрахунків.
3. Додати NOT NULL там, де дані вже повні (`primary_material`, `primary_material_color`).

### Фаза 5. Cleanup

1. Видалити legacy-поля `color` з доменних моделей (поетапно).
2. Видалити `BundleColorMapping` після повного переходу на `BundlePreset`.
3. Спрощення коду: прибрати fallback-гілки.

## Контрольні критерії готовності

1. 100% `ProductModel` мають `primary_material`.
2. 100% активних `Order`/`CustomerOrderLine` мають `primary_material_color`.
3. Нові записи в production створюються без звернення до legacy `Color`.
4. Склад і планування виробництва рахуються по `MaterialColor`.
