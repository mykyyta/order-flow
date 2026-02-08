import os
import secrets

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from apps.orders.notifications import send_delayed_order_created_notifications


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


@csrf_exempt
def send_delayed_notifications(request):
    if request.method != "POST":
        return JsonResponse({"error": "invalid method"}, status=405)

    is_valid, error = _validate_internal_token(request)
    if not is_valid:
        status = 500 if error == "token not configured" else 403
        return JsonResponse({"error": error}, status=status)

    status = send_delayed_order_created_notifications()
    return JsonResponse({"status": status})
