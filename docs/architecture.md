# Архітектура

Система управління замовленнями для виробничого бренду.

## Стек

- Python 3.12, Django 5, PostgreSQL
- Django templates + Tailwind CSS
- Cloud Run (GCP), Terraform


## Bounded Contexts

```
┌─────────────────────────────────────────────────────────────────┐
│                        fulfillment                              │
│                    (orchestration only)                         │
└───────────┬─────────────────┬─────────────────┬────────────────┘
            │                 │                 │
     ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
     │    sales    │   │  production │   │  inventory  │
     │ SalesOrder  │   │ Production  │   │ ProductStock│
     │ Customer    │   │ Order       │   │ WIPStock    │
     └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
            │                 │                 │
     ┌──────▼─────────────────▼─────────────────▼──────┐
     │                    catalog                       │
     │          Product, Variant, Color, Bundle         │
     └─────────────────────────────────────────────────┘

     ┌───────────────┐        ┌───────────────┐
     │   materials   │        │  warehouses   │
     │ Material, BOM │        │   Warehouse   │
     │ Supplier, PO  │        └───────────────┘
     │ MaterialStock │
     └───────────────┘
```


## Apps та їх відповідальність

| App | Моделі | Сервіси |
|-----|--------|---------|
| `catalog` | Product, Variant, Color, Bundle*, BOM | resolve_or_create_variant |
| `sales` | Customer, SalesOrder, SalesOrderLine | create_sales_order |
| `production` | ProductionOrder, StatusHistory | create_production_order, change_status |
| `inventory` | ProductStock, WIPStock, transfers | get/add/remove stock |
| `materials` | Material, MaterialColor, Supplier, PO*, MaterialStock | receive_goods, transfer |
| `warehouses` | Warehouse | get_default_warehouse |
| `fulfillment` | — (no models) | orchestrate cross-context flows |
| `accounts` | User | — |


## Шари архітектури

```
┌─────────────────────────────────────┐
│           Views / Forms             │  ← HTTP layer
├─────────────────────────────────────┤
│            Services                 │  ← Business logic
├─────────────────────────────────────┤
│       Domain (policies, status)     │  ← Rules, transitions
├─────────────────────────────────────┤
│             Models                  │  ← Data access
└─────────────────────────────────────┘
```

### Правила шарів

- **Views**: тільки HTTP, делегують у services
- **Services**: @transaction.atomic, один public entrypoint на use case
- **Domain**: чисті функції (statuses, transitions, policies)
- **Models**: data + validation, без бізнес-логіки


## Потоки даних

### Продаж → Виробництво → Склад

```
SalesOrder
    │
    ▼ create_production_orders_for_sales_order()
ProductionOrder (status: new)
    │
    ▼ change_production_order_status(done)
ProductStock (+1)
    │
    ▼ sync_sales_order_line_production()
SalesOrderLine.production_status = done
```

### Закупівля → Матеріали

```
PurchaseOrder
    │
    ▼ receive_purchase_order_line()
GoodsReceipt
    │
    ▼
MaterialStock (+quantity)
```


## Ключові моделі

### catalog

```python
Product           # Продукт (раніше ProductModel)
  ├─ name, price, currency, cost_price
  ├─ is_bundle
  └─ primary_material, secondary_material

Variant           # Конкретна конфігурація продукту
  ├─ product (FK)
  ├─ color (FK) або primary/secondary_material_color
  └─ sku

Bundle*           # Набори (BundleComponent, BundlePreset, etc.)
BOM               # Bill of Materials (раніше ProductMaterial)
```

### sales

```python
Customer          # Клієнт
  └─ name, phone, email, instagram, notes

SalesOrder        # Замовлення клієнта
  ├─ source (site/etsy/wholesale)
  ├─ status, payment_status, payment_method
  └─ customer (FK), customer_info

SalesOrderLine    # Рядок замовлення
  ├─ product, variant
  ├─ quantity, production_mode
  └─ production_status
```

### production

```python
ProductionOrder   # Виробниче замовлення
  ├─ product, variant
  ├─ status (new → doing → done)
  ├─ is_embroidery, is_urgent, is_etsy
  └─ sales_order_line (FK)

ProductionOrderStatusHistory  # Історія змін статусу
```

### inventory

```python
ProductStock      # Залишки готової продукції (раніше StockRecord)
  ├─ warehouse, variant
  └─ quantity

ProductStockMovement  # Рухи по складу
  ├─ reason (PRODUCTION_IN, SALE_OUT, TRANSFER_*, etc.)
  └─ quantity_change

WIPStockRecord    # Work In Progress
WIPStockMovement

ProductStockTransfer*  # Переміщення між складами
```

### materials

```python
Material, MaterialColor
Supplier
PurchaseOrder, PurchaseOrderLine
GoodsReceipt, GoodsReceiptLine
MaterialStock, MaterialStockMovement
MaterialStockTransfer*
```


## Fulfillment Orchestration

`fulfillment` — app без моделей, який координує cross-context операції:

```python
# Основні orchestration functions
create_sales_order_orchestrated()
create_production_orders_for_sales_order()
complete_production_order()
receive_purchase_order_line_orchestrated()
transfer_finished_stock_orchestrated()
transfer_material_stock_orchestrated()
scrap_wip()
```

Використовувати при операціях, що зачіпають кілька bounded contexts.


## Domain Types

Для type safety використовуються NewType aliases:

```python
from apps.inventory.domain import VariantId, WarehouseId, Quantity

def get_stock_quantity(
    *,
    warehouse_id: WarehouseId,
    variant_id: VariantId,
) -> int: ...
```


## Структура директорій

```
src/
├── config/
│   └── settings/          # base.py, local.py, prod.py, test.py
├── apps/
│   ├── accounts/          # User, auth
│   ├── catalog/           # Product, Variant, Color, Bundle
│   ├── fulfillment/       # Orchestration services
│   ├── inventory/         # ProductStock, WIPStock
│   ├── materials/         # Material, Supplier, PO, MaterialStock
│   ├── production/        # ProductionOrder
│   ├── sales/             # Customer, SalesOrder
│   ├── ui/                # Shared UI components
│   ├── user_settings/     # User preferences
│   └── warehouses/        # Warehouse
frontend/
├── templates/             # Django templates
├── static/                # Compiled CSS, JS
└── assets/                # Tailwind sources
infra/                     # Terraform (Cloud Run, secrets)
docs/                      # Documentation
```


## CI/CD

| Workflow | Trigger | Action |
|----------|---------|--------|
| `test.yml` | PR | pytest + ruff |
| `deploy.yml` | push main | build → migrate → deploy |
| `infra.yml` | changes in infra/ | terraform apply |


## Див. також

- [Конвенції розробки](conventions.md)
- [DevOps Runbook](devops/runbook.md)
- [Infrastructure Overview](devops/infrastructure_overview.md)
