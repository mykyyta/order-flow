"""Profile view tests."""

import pytest
from accounts.models import NotificationSetting
from django.urls import reverse

from .conftest import UserFactory


@pytest.mark.django_db
def test_profile_rejects_duplicate_username(client):
    UserFactory(username="taken_name")
    user = UserFactory(username="operator")
    client.force_login(user)
    response = client.post(
        reverse("profile"),
        {"username": "taken_name"},
        follow=True,
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.username == "operator"
    assert "Такий логін вже зайнятий." in response.content.decode()


@pytest.mark.django_db
def test_profile_rejects_blank_username(client):
    user = UserFactory()
    client.force_login(user)
    response = client.post(
        reverse("profile"),
        {"username": "   "},
        follow=True,
    )
    assert response.status_code == 200
    assert "не може бути порожнім" in response.content.decode()


@pytest.mark.django_db
def test_profile_creates_notification_settings_for_existing_user(client):
    user = UserFactory()
    NotificationSetting.objects.filter(user=user).delete()
    client.force_login(user)
    response = client.get(reverse("profile"))
    assert response.status_code == 200
    assert NotificationSetting.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_profile_saves_notification_settings(client):
    user = UserFactory()
    client.force_login(user)
    response = client.post(
        reverse("profile"),
        {
            "username": user.username,
            "notify_order_created": "on",
            "notify_order_created_pause": "on",
            "notify_order_finished": "on",
        },
        follow=True,
    )
    assert response.status_code == 200
    assert "Готово! Налаштування збережено." in response.content.decode()
