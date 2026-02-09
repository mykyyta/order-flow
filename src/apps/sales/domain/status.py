from apps.customer_orders.models import CustomerOrder, CustomerOrderLine

STATUS_NEW = CustomerOrder.Status.NEW
STATUS_PROCESSING = CustomerOrder.Status.PROCESSING
STATUS_PRODUCTION = CustomerOrder.Status.PRODUCTION
STATUS_READY = CustomerOrder.Status.READY
STATUS_SHIPPED = CustomerOrder.Status.SHIPPED
STATUS_COMPLETED = CustomerOrder.Status.COMPLETED
STATUS_CANCELLED = CustomerOrder.Status.CANCELLED

PRODUCTION_STATUS_PENDING = CustomerOrderLine.ProductionStatus.PENDING
PRODUCTION_STATUS_IN_PROGRESS = CustomerOrderLine.ProductionStatus.IN_PROGRESS
PRODUCTION_STATUS_DONE = CustomerOrderLine.ProductionStatus.DONE
