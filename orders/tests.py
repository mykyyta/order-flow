from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
from typing import Optional
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from orders.adapters.notifications import DjangoNotificationSender
from orders.application.exceptions import InvalidStatusTransition
from orders.application.notification_service import DelayedNotificationService
from orders.application.order_service import OrderService
from orders.adapters.orders_repository import DjangoOrderRepository
from orders.domain.status import (
    STATUS_DOING,
    STATUS_EMBROIDERY,
    STATUS_FINISHED,
    STATUS_NEW,
    STATUS_ON_HOLD,
)
from orders.models import (
    Color,
    CustomUser,
    DelayedNotificationLog,
    NotificationSetting,
    Order,
    OrderStatusHistory,
    ProductModel,
)
from orders.templatetags.order_ui import message_alert_class


@dataclass(eq=False)
class FakeOrder:
    created_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    current_status: Optional[str] = None


class FakeClock:
    def __init__(self, now_value: datetime) -> None:
        self._now = now_value

    def now(self) -> datetime:
        return self._now


class FakeRepo:
    def __init__(self) -> None:
        self.latest_status = {}
        self.add_status_calls = 0
        self.set_finished_calls = 0
        self.orders = []

    def create_order(
        self,
        *,
        model,
        color,
        embroidery: bool,
        urgent: bool,
        etsy: bool,
        comment: Optional[str],
    ):
        order = FakeOrder()
        self.orders.append(order)
        self.latest_status[order] = None
        return order

    def add_status(self, *, order, new_status: str, changed_by) -> None:
        self.latest_status[order] = new_status
        self.add_status_calls += 1

    def get_latest_status(self, *, order) -> Optional[str]:
        return self.latest_status.get(order)

    def set_finished_at(self, *, order, finished_at: Optional[datetime]) -> None:
        order.finished_at = finished_at
        self.set_finished_calls += 1

    def set_current_status(self, *, order, current_status: str) -> None:
        order.current_status = current_status

    def list_orders_created_between(self, *, start: datetime, end: datetime):
        return [
            order for order in self.orders
            if order.created_at is not None and start <= order.created_at < end
        ]


class FakeNotifier:
    def __init__(self) -> None:
        self.created = []
        self.finished = []
        self.delayed_sent = []
        self.delayed_result = True

    def order_created(self, *, order, orders_url: Optional[str]) -> None:
        self.created.append((order, orders_url))

    def order_finished(self, *, order) -> None:
        self.finished.append(order)

    def orders_created_delayed(self, *, orders) -> bool:
        self.delayed_sent.append(list(orders))
        return self.delayed_result


class OrderServiceTests(SimpleTestCase):
    def setUp(self) -> None:
        self.fixed_now = datetime(2026, 1, 1, 9, 0, tzinfo=dt_timezone.utc)
        self.clock = FakeClock(self.fixed_now)
        self.repo = FakeRepo()
        self.notifier = FakeNotifier()
        self.service = OrderService(
            repo=self.repo,
            notifier=self.notifier,
            clock=self.clock,
        )

    def test_create_order_sets_status_and_notifies(self):
        order = self.service.create_order(
            model="model",
            color="color",
            embroidery=False,
            urgent=False,
            etsy=False,
            comment=None,
            created_by="user",
            orders_url="http://example/orders",
        )

        self.assertEqual(self.repo.latest_status[order], STATUS_NEW)
        self.assertEqual(order.current_status, STATUS_NEW)
        self.assertEqual(len(self.notifier.created), 1)

    def test_change_status_finishes_order(self):
        order = self.repo.create_order(
            model="model",
            color="color",
            embroidery=False,
            urgent=False,
            etsy=False,
            comment=None,
        )

        self.service.change_status(
            orders=[order],
            new_status=STATUS_FINISHED,
            changed_by="user",
        )

        self.assertEqual(self.repo.latest_status[order], STATUS_FINISHED)
        self.assertEqual(order.current_status, STATUS_FINISHED)
        self.assertEqual(order.finished_at, self.fixed_now)
        self.assertEqual(len(self.notifier.finished), 1)

    def test_change_status_same_status_normalizes_finished_at(self):
        order = self.repo.create_order(
            model="model",
            color="color",
            embroidery=False,
            urgent=False,
            etsy=False,
            comment=None,
        )
        self.repo.latest_status[order] = STATUS_FINISHED

        self.service.change_status(
            orders=[order],
            new_status=STATUS_FINISHED,
            changed_by="user",
        )

        self.assertEqual(self.repo.add_status_calls, 0)
        self.assertEqual(order.current_status, STATUS_FINISHED)
        self.assertEqual(order.finished_at, self.fixed_now)
        self.assertEqual(len(self.notifier.finished), 0)

    def test_change_status_unfinishes_order(self):
        order = self.repo.create_order(
            model="model",
            color="color",
            embroidery=False,
            urgent=False,
            etsy=False,
            comment=None,
        )
        order.finished_at = self.fixed_now
        self.repo.latest_status[order] = STATUS_NEW
        order.current_status = STATUS_NEW

        self.service.change_status(
            orders=[order],
            new_status=STATUS_DOING,
            changed_by="user",
        )

        self.assertIsNone(order.finished_at)

    def test_change_status_rejects_return_to_new(self):
        order = self.repo.create_order(
            model="model",
            color="color",
            embroidery=False,
            urgent=False,
            etsy=False,
            comment=None,
        )
        self.repo.latest_status[order] = STATUS_EMBROIDERY
        order.current_status = STATUS_EMBROIDERY

        with self.assertRaises(InvalidStatusTransition):
            self.service.change_status(
                orders=[order],
                new_status=STATUS_NEW,
                changed_by="user",
            )

    def test_change_status_rejects_invalid_status(self):
        order = self.repo.create_order(
            model="model",
            color="color",
            embroidery=False,
            urgent=False,
            etsy=False,
            comment=None,
        )

        with self.assertRaises(ValueError):
            self.service.change_status(
                orders=[order],
                new_status="invalid_status",
                changed_by="user",
            )

    def test_change_status_rejects_invalid_transition(self):
        order = self.repo.create_order(
            model="model",
            color="color",
            embroidery=False,
            urgent=False,
            etsy=False,
            comment=None,
        )
        self.repo.latest_status[order] = STATUS_FINISHED

        with self.assertRaises(InvalidStatusTransition):
            self.service.change_status(
                orders=[order],
                new_status=STATUS_EMBROIDERY,
                changed_by="user",
            )


class DelayedNotificationServiceTests(SimpleTestCase):
    def setUp(self) -> None:
        self.fixed_now = datetime(2026, 1, 1, 9, 0, tzinfo=dt_timezone.utc)
        self.clock = FakeClock(self.fixed_now)
        self.repo = FakeRepo()
        self.notifier = FakeNotifier()
        self.service = DelayedNotificationService(
            repo=self.repo,
            notifier=self.notifier,
            clock=self.clock,
        )

    def test_no_orders_to_notify(self):
        status = self.service.send_delayed_notifications()
        self.assertEqual(status, "no orders to notify")

    def test_no_users_to_notify(self):
        order = FakeOrder(created_at=self.fixed_now.replace(hour=7))
        self.repo.orders.append(order)
        self.notifier.delayed_result = False

        status = self.service.send_delayed_notifications()
        self.assertEqual(status, "no users to notify")

    def test_delayed_notifications_sent(self):
        order = FakeOrder(created_at=self.fixed_now.replace(hour=7))
        self.repo.orders.append(order)

        status = self.service.send_delayed_notifications()
        self.assertEqual(status, "delayed notifications sent")


class OrderServiceIntegrationTests(TestCase):
    def setUp(self) -> None:
        self.fixed_now = datetime(2026, 1, 1, 9, 0, tzinfo=dt_timezone.utc)
        self.clock = FakeClock(self.fixed_now)
        self.repo = DjangoOrderRepository()
        self.notifier = FakeNotifier()
        self.service = OrderService(
            repo=self.repo,
            notifier=self.notifier,
            clock=self.clock,
        )
        self.user = CustomUser.objects.create_user(username="user", password="pass")
        self.model = ProductModel.objects.create(name="Model A")
        self.color = Color.objects.create(name="Red", code=1, availability_status="in_stock")

    def test_create_order_persists_history(self):
        order = self.service.create_order(
            model=self.model,
            color=self.color,
            embroidery=False,
            urgent=False,
            etsy=False,
            comment=None,
            created_by=self.user,
            orders_url=None,
        )

        self.assertEqual(OrderStatusHistory.objects.filter(order=order).count(), 1)
        self.assertEqual(
            OrderStatusHistory.objects.filter(order=order).first().new_status,
            STATUS_NEW,
        )
        order.refresh_from_db()
        self.assertEqual(order.current_status, STATUS_NEW)

    def test_change_status_updates_finished_at(self):
        order = self.service.create_order(
            model=self.model,
            color=self.color,
            embroidery=False,
            urgent=False,
            etsy=False,
            comment=None,
            created_by=self.user,
            orders_url=None,
        )

        self.service.change_status(
            orders=[order],
            new_status=STATUS_FINISHED,
            changed_by=self.user,
        )

        order.refresh_from_db()
        self.assertEqual(order.finished_at, self.fixed_now)
        self.assertEqual(order.current_status, STATUS_FINISHED)


class AccessControlTests(TestCase):
    def setUp(self) -> None:
        self.user = CustomUser.objects.create_user(username="viewer", password="pass12345")
        self.model = ProductModel.objects.create(name="Model B")
        self.color = Color.objects.create(name="Blue", code=2, availability_status="in_stock")

    def test_models_and_colors_views_require_authentication(self):
        self.assertEqual(self.client.get(reverse("product_models")).status_code, 302)
        self.assertEqual(self.client.get(reverse("colors")).status_code, 302)
        self.assertEqual(
            self.client.get(reverse("color_edit", kwargs={"pk": self.color.pk})).status_code,
            302,
        )


class ColorEditFlowTests(TestCase):
    def setUp(self) -> None:
        self.user = CustomUser.objects.create_user(username="color_editor", password="pass12345")
        self.color = Color.objects.create(name="Ivory", code=101, availability_status="in_stock")
        self.client.force_login(self.user)

    def test_color_edit_redirects_to_colors_list(self):
        response = self.client.post(
            reverse("color_edit", kwargs={"pk": self.color.pk}),
            data={
                "name": "ivory",
                "code": 101,
                "availability_status": "low_stock",
            },
        )

        self.assertRedirects(response, reverse("colors"))
        self.color.refresh_from_db()
        self.assertEqual(self.color.availability_status, "low_stock")


class AuthAndSecurityFlowTests(TestCase):
    def setUp(self) -> None:
        self.user = CustomUser.objects.create_user(username="operator", password="ValidPass123!")

    def test_login_invalid_credentials_renders_form_error(self):
        response = self.client.post(
            reverse("auth_login"),
            {"username": "operator", "password": "wrong"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertContains(response, "Невірні облікові дані.", status_code=401)

    def test_change_password_uses_django_password_validation(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("change_password"),
            {
                "current_password": "ValidPass123!",
                "new_password": "123",
                "confirm_password": "123",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("ValidPass123!"))

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        get_response = self.client.get(reverse("auth_logout"))
        self.assertEqual(get_response.status_code, 405)

        post_response = self.client.post(reverse("auth_logout"), follow=True)
        self.assertEqual(post_response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    @patch.dict(os.environ, {"DELAYED_NOTIFICATIONS_TOKEN": "secret-token"}, clear=False)
    def test_delayed_notifications_token_allowed_only_in_header(self):
        response_with_query = self.client.post(
            f"{reverse('send_delayed_notifications')}?token=secret-token",
        )
        self.assertEqual(response_with_query.status_code, 403)

        response_with_header = self.client.post(
            reverse("send_delayed_notifications"),
            HTTP_X_INTERNAL_TOKEN="secret-token",
        )
        self.assertEqual(response_with_header.status_code, 200)

    def test_profile_rejects_duplicate_username(self):
        CustomUser.objects.create_user(username="taken_name", password="pass12345")
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("profile"),
            {"username": "taken_name"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "operator")
        self.assertContains(response, "Користувач з таким")

    def test_profile_rejects_blank_username(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("profile"),
            {"username": "   "},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "не може бути порожнім")

    def test_notification_settings_get_or_create_for_existing_user(self):
        NotificationSetting.objects.filter(user=self.user).delete()
        self.client.force_login(self.user)

        response = self.client.get(reverse("notification_settings"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(NotificationSetting.objects.filter(user=self.user).exists())

    def test_notification_settings_post_shows_success_message(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("notification_settings"),
            {
                "notify_order_created": "on",
                "notify_order_created_pause": "on",
                "notify_order_finished": "on",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Налаштування сповіщень оновлено.")


class DelayedNotificationsAdapterTests(TestCase):
    def setUp(self) -> None:
        self.user = CustomUser.objects.create_user(
            username="notify_user",
            password="ValidPass123!",
            telegram_id="12345",
        )
        self.model = ProductModel.objects.create(name="Model C")
        self.color = Color.objects.create(name="Green", code=3, availability_status="in_stock")
        self.order = Order.objects.create(model=self.model, color=self.color)
        self.sender = DjangoNotificationSender()

    @patch("orders.adapters.notifications.send_tg_message", return_value=True)
    def test_orders_created_delayed_is_idempotent_per_user_and_order(self, mocked_send):
        self.assertTrue(self.sender.orders_created_delayed(orders=[self.order]))
        self.assertTrue(self.sender.orders_created_delayed(orders=[self.order]))

        self.assertEqual(mocked_send.call_count, 1)
        self.assertEqual(
            DelayedNotificationLog.objects.filter(user=self.user, order=self.order).count(),
            1,
        )


class OrderModelStatusTests(TestCase):
    def test_get_status_uses_current_status(self):
        model = ProductModel.objects.create(name="Model D")
        color = Color.objects.create(name="Black", code=4, availability_status="in_stock")
        order = Order.objects.create(model=model, color=color, current_status=STATUS_NEW)
        OrderStatusHistory.objects.create(order=order, changed_by=None, new_status=STATUS_FINISHED)

        self.assertEqual(order.get_status(), STATUS_NEW)


class OrderUiTemplateFilterTests(SimpleTestCase):
    def test_message_alert_class_mapping(self):
        self.assertEqual(message_alert_class("error"), "alert alert-error")
        self.assertEqual(message_alert_class("success"), "alert alert-success")
        self.assertEqual(message_alert_class("warning extra"), "alert alert-warning")
        self.assertEqual(message_alert_class("unknown"), "alert alert-info")


class CurrentOrdersViewTests(TestCase):
    def setUp(self) -> None:
        self.user = CustomUser.objects.create_user(username="planner", password="pass12345")
        self.client.force_login(self.user)

    def test_transition_map_present_in_page(self):
        response = self.client.get(reverse("orders_active"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "transition-map-data")
        self.assertContains(response, "bulk-status-form")
        self.assertContains(response, "clear-selection-btn")


class CurrentOrdersFilteringTests(TestCase):
    def setUp(self) -> None:
        self.user = CustomUser.objects.create_user(username="planner2", password="pass12345")
        self.client.force_login(self.user)
        self.model = ProductModel.objects.create(name="Model E")
        self.color = Color.objects.create(name="White", code=5, availability_status="in_stock")

    def test_current_orders_list_is_paginated_and_excludes_finished(self):
        for _ in range(51):
            Order.objects.create(
                model=self.model,
                color=self.color,
                current_status=STATUS_NEW,
            )
        Order.objects.create(
            model=self.model,
            color=self.color,
            current_status=STATUS_FINISHED,
        )

        response = self.client.get(reverse("orders_active"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 51)
        self.assertEqual(len(response.context["orders"]), 50)
        self.assertTrue(response.context["page_obj"].has_next())

        second_page = self.client.get(reverse("orders_active"), {"page": 2})
        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(len(second_page.context["orders"]), 1)
        self.assertFalse(second_page.context["page_obj"].has_next())

    def test_current_orders_supports_status_filter(self):
        target = Order.objects.create(
            model=self.model,
            color=self.color,
            comment="vip batch",
            current_status=STATUS_ON_HOLD,
        )
        Order.objects.create(
            model=self.model,
            color=self.color,
            comment="regular batch",
            current_status=STATUS_NEW,
        )

        response = self.client.get(
            reverse("orders_active"),
            {"status": STATUS_ON_HOLD},
        )
        self.assertEqual(response.status_code, 200)
        orders = list(response.context["orders"])
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].id, target.id)


class FinishedOrdersSearchTests(TestCase):
    def setUp(self) -> None:
        self.user = CustomUser.objects.create_user(username="history_user", password="pass12345")
        self.client.force_login(self.user)
        self.model = ProductModel.objects.create(name="Model History")
        self.color = Color.objects.create(name="Navy", code=7, availability_status="in_stock")

    def test_finished_orders_search_filters_across_all_finished(self):
        target = Order.objects.create(
            model=self.model,
            color=self.color,
            comment="special archive order",
            current_status=STATUS_FINISHED,
        )
        Order.objects.create(
            model=self.model,
            color=self.color,
            comment="other archive order",
            current_status=STATUS_FINISHED,
        )
        Order.objects.create(
            model=self.model,
            color=self.color,
            comment="special archive order",
            current_status=STATUS_NEW,
        )

        response = self.client.get(reverse("orders_completed"), {"q": "special"})
        self.assertEqual(response.status_code, 200)
        orders = list(response.context["page_obj"].object_list)
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].id, target.id)

    def test_finished_orders_search_preserves_query_params_for_pagination(self):
        for _ in range(21):
            Order.objects.create(
                model=self.model,
                color=self.color,
                comment="archive",
                current_status=STATUS_FINISHED,
            )

        response = self.client.get(reverse("orders_completed"), {"q": "archive"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 21)
        self.assertEqual(len(response.context["page_obj"].object_list), 20)
        self.assertContains(response, "?page=2&q=archive")

        second_page = self.client.get(reverse("orders_completed"), {"q": "archive", "page": 2})
        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(len(second_page.context["page_obj"].object_list), 1)


class OrderDetailViewTests(TestCase):
    def setUp(self) -> None:
        self.user = CustomUser.objects.create_user(username="detail_user", password="pass12345")
        self.client.force_login(self.user)
        self.model = ProductModel.objects.create(name="Model F")
        self.color = Color.objects.create(name="Cyan", code=6, availability_status="in_stock")

    def test_order_detail_renders_status_indicator(self):
        order = Order.objects.create(
            model=self.model,
            color=self.color,
            current_status=STATUS_ON_HOLD,
        )

        response = self.client.get(reverse("order_detail", kwargs={"order_id": order.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "text-rose-500")
        self.assertContains(response, order.get_current_status_display())


class HealthcheckCommandTests(TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_healthcheck_requires_tokens_when_flag_enabled(self):
        with self.assertRaises(CommandError):
            call_command("healthcheck_app", "--require-telegram-token")
