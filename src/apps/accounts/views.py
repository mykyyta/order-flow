from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.ui.themes import THEME_CHOICES, normalize_theme
from apps.user_settings.models import NotificationSetting


def auth_login(request):
    if request.user.is_authenticated:
        return redirect("index")

    if request.GET.get("logout"):
        messages.info(request, "До зустрічі! Ви вийшли з системи.")

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""

        if not username or not password:
            messages.error(request, "Вкажіть логін і пароль — і вперед.")
            return render(
                request,
                "account/login.html",
                {"username": username, "page_title": "Вхід", "page_title_center": True},
                status=400,
            )

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

            return redirect("index")
        messages.error(request, "Логін або пароль не збігаються.")
        return render(
            request,
            "account/login.html",
            {"username": username, "page_title": "Вхід", "page_title_center": True},
            status=401,
        )

    return render(
        request,
        "account/login.html",
        {"username": "", "page_title": "Вхід", "page_title_center": True},
    )


@require_POST
def auth_logout(request):
    logout(request)
    return redirect(reverse("auth_login") + "?logout=1")


@login_required
@transaction.atomic
def profile_view(request):
    user = request.user
    notif_settings, _created = NotificationSetting.objects.get_or_create(user=user)

    if request.method == "POST":
        new_username = (request.POST.get("username") or "").strip()
        raw_theme = request.POST.get("theme")
        if raw_theme is None:
            new_theme = user.theme
        else:
            new_theme = normalize_theme(raw_theme)
            if new_theme is None:
                messages.error(request, "Невідома тема.")
                return redirect("profile")

        if not new_username:
            messages.error(request, "Логін не може бути порожнім.")
            return redirect("profile")

        update_fields: list[str] = []
        if new_username != user.username:
            user_model = get_user_model()
            if (
                user_model.objects.filter(username__iexact=new_username)
                .exclude(pk=user.pk)
                .exists()
            ):
                messages.error(request, "Такий логін вже зайнятий.")
                return redirect("profile")
            user.username = new_username
            update_fields.append("username")

        if new_theme != user.theme:
            user.theme = new_theme
            update_fields.append("theme")

        if update_fields:
            user.save(update_fields=update_fields)

        notif_settings.notify_order_created = request.POST.get("notify_order_created") == "on"
        notif_settings.notify_order_finished = request.POST.get("notify_order_finished") == "on"
        notif_settings.notify_order_created_pause = (
            request.POST.get("notify_order_created_pause") == "on"
        )
        notif_settings.save()

        messages.success(request, "Готово! Налаштування збережено.")

        return redirect("profile")

    return render(
        request,
        "account/profile.html",
        {
            "page_title": "Профіль",
            "user": user,
            "notification_settings": notif_settings,
            "theme_choices": THEME_CHOICES,
        },
    )


@login_required
def change_password(request):
    if request.method == "POST":
        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if not current_password or not new_password or not confirm_password:
            messages.error(request, "Заповни всі поля.")
            return redirect("change_password")

        if new_password != confirm_password:
            messages.error(request, "Нові паролі не збігаються.")
            return redirect("change_password")

        if not request.user.check_password(current_password):
            messages.error(request, "Поточний пароль неправильний.")
            return redirect("change_password")

        try:
            validate_password(new_password, request.user)
        except ValidationError as exc:
            for error in exc.messages:
                messages.error(request, error)
            return redirect("change_password")

        request.user.set_password(new_password)
        request.user.save()

        update_session_auth_hash(request, request.user)

        messages.success(request, "Готово! Пароль змінено.")
        return redirect("profile")

    return render(request, "account/change_password.html", {"page_title": "Зміна пароля"})
