"""Profile view tests."""

import pytest
from django.urls import reverse

from apps.accounts.models import NotificationSetting
from apps.orders.themes import DEFAULT_THEME

from .conftest import UserFactory

AUTH_BACKEND = "django.contrib.auth.backends.ModelBackend"


@pytest.mark.django_db(transaction=True)
def test_profile_rejects_duplicate_username(client):
    UserFactory(username="taken_name")
    user = UserFactory(username="operator")
    client.force_login(user, backend=AUTH_BACKEND)
    response = client.post(
        reverse("profile"),
        {"username": "taken_name"},
        follow=True,
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.username == "operator"
    assert "Такий логін вже зайнятий." in response.content.decode()


@pytest.mark.django_db(transaction=True)
def test_profile_rejects_blank_username(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    response = client.post(
        reverse("profile"),
        {"username": "   "},
        follow=True,
    )
    assert response.status_code == 200
    assert "не може бути порожнім" in response.content.decode()


@pytest.mark.django_db(transaction=True)
def test_profile_creates_notification_settings_for_existing_user(client):
    user = UserFactory()
    NotificationSetting.objects.filter(user=user).delete()
    client.force_login(user, backend=AUTH_BACKEND)
    response = client.get(reverse("profile"))
    assert response.status_code == 200
    assert NotificationSetting.objects.filter(user=user).exists()


@pytest.mark.django_db(transaction=True)
def test_profile_saves_notification_settings(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
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


@pytest.mark.django_db(transaction=True)
def test_profile_saves_theme(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    response = client.post(
        reverse("profile"),
        {"username": user.username, "theme": "lumen_night"},
        follow=True,
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.theme == "lumen_night"


@pytest.mark.django_db(transaction=True)
def test_profile_rejects_unknown_theme(client):
    user = UserFactory()
    user.theme = DEFAULT_THEME
    user.save(update_fields=["theme"])
    client.force_login(user, backend=AUTH_BACKEND)
    response = client.post(
        reverse("profile"),
        {"username": user.username, "theme": "not_a_theme"},
        follow=True,
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.theme == DEFAULT_THEME
    assert "Невідома тема." in response.content.decode()


@pytest.mark.django_db(transaction=True)
def test_profile_theme_preview_param_overrides_active_theme(client):
    user = UserFactory()
    user.theme = "lumen_warm"
    user.save(update_fields=["theme"])
    client.force_login(user, backend=AUTH_BACKEND)
    response = client.get(reverse("profile") + "?theme=lumen_night")
    assert response.status_code == 200
    assert 'data-theme="lumen_night"' in response.content.decode()


@pytest.mark.django_db(transaction=True)
def test_profile_theme_preview_default_clears_data_theme(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    response = client.get(reverse("profile") + "?theme=default")
    assert response.status_code == 200
    assert "data-theme=" not in response.content.decode()
