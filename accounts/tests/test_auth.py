"""Auth and security flow tests."""

import os
from unittest.mock import patch

import pytest
from django.urls import reverse

from .conftest import UserFactory


@pytest.mark.django_db
def test_login_invalid_credentials_renders_form_error(client):
    UserFactory(username="operator")
    response = client.post(
        reverse("auth_login"),
        {"username": "operator", "password": "wrong"},
    )
    assert response.status_code == 401
    assert "Логін або пароль не збігаються." in response.content.decode()


@pytest.mark.django_db
def test_change_password_uses_django_password_validation(client):
    user = UserFactory(username="operator")
    user.set_password("ValidPass123!")
    user.save()
    client.force_login(user)
    response = client.post(
        reverse("change_password"),
        {
            "current_password": "ValidPass123!",
            "new_password": "123",
            "confirm_password": "123",
        },
        follow=True,
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password("ValidPass123!")


@pytest.mark.django_db
def test_logout_requires_post(client):
    user = UserFactory()
    client.force_login(user)
    get_response = client.get(reverse("auth_logout"))
    assert get_response.status_code == 405
    post_response = client.post(reverse("auth_logout"), follow=True)
    assert post_response.status_code == 200
    assert "_auth_user_id" not in client.session


@patch.dict(os.environ, {"DELAYED_NOTIFICATIONS_TOKEN": "secret-token"}, clear=False)
@pytest.mark.django_db
def test_delayed_notifications_token_allowed_only_in_header(client):
    response_with_query = client.post(
        f"{reverse('send_delayed_notifications')}?token=secret-token",
    )
    assert response_with_query.status_code == 403
    response_with_header = client.post(
        reverse("send_delayed_notifications"),
        HTTP_X_INTERNAL_TOKEN="secret-token",
    )
    assert response_with_header.status_code == 200
