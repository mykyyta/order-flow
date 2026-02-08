import os
import secrets

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from orders.adapters.clock import DjangoClock
from orders.adapters.notifications import DjangoNotificationSender
from orders.adapters.orders_repository import DjangoOrderRepository
from orders.application.notification_service import DelayedNotificationService


def _validate_internal_token(request):
    expected = os.getenv("DELAYED_NOTIFICATIONS_TOKEN")
    if not expected:
        return False, "token not configured"

    provided = request.headers.get("X-Internal-Token")
    if not provided:
        return False, "token missing"

    if not secrets.compare_digest(provided, expected):
        return False, "invalid token"

    return True, None


def _get_delayed_notification_service() -> DelayedNotificationService:
    return DelayedNotificationService(
        repo=DjangoOrderRepository(),
        notifier=DjangoNotificationSender(),
        clock=DjangoClock(),
    )


@csrf_exempt
def send_delayed_notifications(request):
    if request.method != "POST":
        return JsonResponse({"error": "invalid method"}, status=405)

    is_valid, error = _validate_internal_token(request)
    if not is_valid:
        status = 500 if error == "token not configured" else 403
        return JsonResponse({"error": error}, status=status)

    service = _get_delayed_notification_service()
    status = service.send_delayed_notifications()
    return JsonResponse({"status": status})
