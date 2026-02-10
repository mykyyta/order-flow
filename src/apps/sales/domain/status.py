from apps.sales.models import SalesOrder, SalesOrderLine

STATUS_NEW = SalesOrder.Status.NEW
STATUS_PROCESSING = SalesOrder.Status.PROCESSING
STATUS_PRODUCTION = SalesOrder.Status.PRODUCTION
STATUS_READY = SalesOrder.Status.READY
STATUS_SHIPPED = SalesOrder.Status.SHIPPED
STATUS_COMPLETED = SalesOrder.Status.COMPLETED
STATUS_CANCELLED = SalesOrder.Status.CANCELLED

PRODUCTION_STATUS_PENDING = SalesOrderLine.ProductionStatus.PENDING
PRODUCTION_STATUS_IN_PROGRESS = SalesOrderLine.ProductionStatus.IN_PROGRESS
PRODUCTION_STATUS_DONE = SalesOrderLine.ProductionStatus.DONE

PRODUCTION_MODE_AUTO = SalesOrderLine.ProductionMode.AUTO
PRODUCTION_MODE_MANUAL = SalesOrderLine.ProductionMode.MANUAL
PRODUCTION_MODE_FORCE = SalesOrderLine.ProductionMode.FORCE
