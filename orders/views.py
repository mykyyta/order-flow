import os
import secrets
from functools import wraps

from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import models, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.timezone import localtime
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import ListView, UpdateView

from orders.adapters.clock import DjangoClock
from orders.adapters.notifications import DjangoNotificationSender
from orders.adapters.orders_repository import DjangoOrderRepository
from orders.application.exceptions import InvalidStatusTransition
from orders.application.notification_service import DelayedNotificationService
from orders.application.order_service import OrderService
from orders.domain.status import STATUS_FINISHED
from orders.domain.transitions import get_allowed_transitions
from orders.forms import OrderForm
from orders.models import NotificationSetting, OrderStatusHistory

from .forms import ColorForm, OrderStatusUpdateForm, ProductModelForm
from .models import Color, Order, ProductModel, STATUS_CHOICES

STATUS_LABELS = dict(STATUS_CHOICES)
CURRENT_STATUS_OPTIONS = tuple(
    (value, label)
    for value, label in STATUS_CHOICES
    if value != STATUS_FINISHED
)
TRANSITION_MAP = {
    status: sorted(get_allowed_transitions(status))
    for status, _label in STATUS_CHOICES
}


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


def _get_order_service() -> OrderService:
    return OrderService(
        repo=DjangoOrderRepository(),
        notifier=DjangoNotificationSender(),
        clock=DjangoClock(),
    )


def _get_delayed_notification_service() -> DelayedNotificationService:
    return DelayedNotificationService(
        repo=DjangoOrderRepository(),
        notifier=DjangoNotificationSender(),
        clock=DjangoClock(),
    )


def _filtered_current_orders_queryset(*, status_filter: str):
    queryset = (
        Order.objects.select_related("model", "color")
        .exclude(current_status=STATUS_FINISHED)
        .order_by("-created_at", "-id")
    )

    status_values = {value for value, _ in CURRENT_STATUS_OPTIONS}
    if status_filter in status_values:
        queryset = queryset.filter(current_status=status_filter)
        return queryset, status_filter
    return queryset, ""



def custom_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('auth_login')
        return view_func(request, *args, **kwargs)
    return wrapper

def auth_login(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''

        if not username or not password:
            messages.error(request, "Вкажіть ім'я користувача і пароль.")
            return render(request, "account/login.html", {"username": username}, status=400)

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

            return redirect('index')
        messages.error(request, 'Невірні облікові дані.')
        return render(request, "account/login.html", {"username": username}, status=401)

    return render(request, "account/login.html", {"username": ""})


@require_POST
def auth_logout(request):
    logout(request)
    return redirect('auth_login')

@custom_login_required
def orders_active(request):
    status_filter = (request.GET.get("status") or "").strip()
    orders_queryset, status_filter = _filtered_current_orders_queryset(
        status_filter=status_filter,
    )

    form = OrderStatusUpdateForm()
    form.fields["orders"].queryset = orders_queryset
    paginator = Paginator(orders_queryset, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    query_params = request.GET.copy()
    query_params.pop("page", None)
    query_string = query_params.urlencode()

    return render(
        request,
        "orders/active.html",
        {
            "form": form,
            "orders": page_obj.object_list,
            "page_obj": page_obj,
            "status_filter": status_filter,
            "status_options": CURRENT_STATUS_OPTIONS,
            "query_string": query_string,
            "transition_map": TRANSITION_MAP,
        },
    )


@custom_login_required
@require_POST
def orders_bulk_status(request):
    status_filter = (request.GET.get("status") or "").strip()
    orders_queryset, status_filter = _filtered_current_orders_queryset(
        status_filter=status_filter,
    )

    form = OrderStatusUpdateForm(request.POST)
    form.fields["orders"].queryset = orders_queryset
    if not form.is_valid():
        messages.error(request, "Виникла помилка. Зробіть ще одну спробу.")
        url = reverse("orders_active")
        if request.GET:
            url += "?" + request.GET.urlencode()
        return redirect(url)

    selected_orders = form.cleaned_data["orders"]
    new_status = form.cleaned_data["new_status"]

    if not selected_orders:
        messages.warning(request, "Не вибрано жодного замовлення для оновлення статусу.")
        url = reverse("orders_active")
        if request.GET:
            url += "?" + request.GET.urlencode()
        return redirect(url)

    service = _get_order_service()
    with transaction.atomic():
        try:
            service.change_status(
                orders=selected_orders,
                new_status=new_status,
                changed_by=request.user,
            )
        except InvalidStatusTransition as exc:
            current_label = STATUS_LABELS.get(exc.current_status, exc.current_status)
            next_label = STATUS_LABELS.get(exc.next_status, exc.next_status)
            messages.error(
                request,
                f"Недопустимий перехід статусу: {current_label} → {next_label}.",
            )
            url = reverse("orders_active")
            if request.GET:
                url += "?" + request.GET.urlencode()
            return redirect(url)

    messages.success(request, "Статус оновлено для вибраних замовлень.")
    url = reverse("orders_active")
    if request.GET:
        url += "?" + request.GET.urlencode()
    return redirect(url)


@custom_login_required
def orders_completed(request):
    search_query = (request.GET.get("q") or "").strip()
    orders = (
        Order.objects.select_related("model", "color")
        .filter(current_status=STATUS_FINISHED)
        .order_by('-finished_at')
    )
    if search_query:
        search_filters = (
            Q(model__name__icontains=search_query)
            | Q(color__name__icontains=search_query)
            | Q(comment__icontains=search_query)
        )
        if search_query.isdigit():
            search_filters |= Q(id=int(search_query))
        orders = orders.filter(search_filters)

    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    query_params = request.GET.copy()
    query_params.pop("page", None)
    query_string = query_params.urlencode()

    return render(
        request,
        "orders/completed.html",
        {
            "page_obj": page_obj,
            "search_query": search_query,
            "query_string": query_string,
        },
    )


@custom_login_required
def orders_create(request):
    if request.method == "POST":
        form = OrderForm(request.POST)
        if form.is_valid():
            service = _get_order_service()
            orders_url = request.build_absolute_uri(reverse_lazy("orders_active"))
            service.create_order(
                model=form.cleaned_data["model"],
                color=form.cleaned_data["color"],
                etsy=form.cleaned_data["etsy"],
                embroidery=form.cleaned_data["embroidery"],
                urgent=form.cleaned_data["urgent"],
                comment=form.cleaned_data.get("comment"),
                created_by=request.user,
                orders_url=orders_url,
            )
            return redirect("orders_active")
        return render(request, "orders/create.html", {"form": form})

    form = OrderForm()
    return render(request, "orders/create.html", {"form": form})

@custom_login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    statuses = OrderStatusHistory.objects.filter(order=order).order_by('-changed_at')

    order_data = {
        'id': order.id,
        'model': order.model.name,
        'color': order.color.name,
        'embroidery': order.embroidery,
        'comment': order.comment,
        'urgent': order.urgent,
        'etsy': order.etsy,
        'created_at': localtime(order.created_at) if order.created_at else None,
        'finished_at': localtime(order.finished_at) if order.finished_at else None,
        'current_status_code': order.current_status,
        'current_status_display': order.get_current_status_display(),
        'status_history': [
            {
                'id': status.id,
                'new_status': status.new_status,
                'new_status_display': dict(OrderStatusHistory.STATUS_CHOICES).get(status.new_status, 'Unknown'),
                'changed_by': status.changed_by.username if status.changed_by else 'Unknown',
                'changed_at': localtime(status.changed_at) if status.changed_at else None,
            }
            for status in statuses
        ]
    }

    return render(request, "orders/detail.html", {"order": order_data})



class ProductModelListCreateView(LoginRequiredMixin, View):
    login_url = reverse_lazy("auth_login")
    template_name = "catalog/product_models.html"

    def get(self, request, *args, **kwargs):
        models = ProductModel.objects.all()
        form = ProductModelForm()
        return render(request, self.template_name, {"models": models, "form": form})

    def post(self, request, *args, **kwargs):
        form = ProductModelForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(reverse_lazy("product_models"))
        models = ProductModel.objects.all()
        return render(request, self.template_name, {"models": models, "form": form})



class ColorListCreateView(LoginRequiredMixin, ListView):
    login_url = reverse_lazy("auth_login")
    model = Color
    template_name = "catalog/colors.html"
    context_object_name = "colors"

    def get_queryset(self):
        return Color.objects.order_by(
            models.Case(
                models.When(availability_status="out_of_stock", then=2),
                models.When(availability_status="low_stock", then=1),
                models.When(availability_status="in_stock", then=0),
                default=3,
                output_field=models.IntegerField(),
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["color_form"] = ColorForm()
        return context

    def post(self, request, *args, **kwargs):
        form = ColorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("colors")
        return self.get(request, *args, **kwargs)

class ColorDetailUpdateView(LoginRequiredMixin, UpdateView):
    login_url = reverse_lazy("auth_login")
    model = Color
    form_class = ColorForm
    template_name = "catalog/color_edit.html"
    context_object_name = "color"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["color"] = self.object
        return context

    def get_success_url(self):
        return reverse_lazy("color_edit", kwargs={"pk": self.object.pk})

@custom_login_required
def profile_view(request):
    user = request.user

    if request.method == 'POST':
        new_username = (request.POST.get('username') or '').strip()

        if not new_username:
            messages.error(request, "Ім'я користувача не може бути порожнім.")
            return redirect('profile')

        if new_username == user.username:
            messages.info(request, 'Змін не виявлено.')
            return redirect('profile')

        user_model = get_user_model()
        if user_model.objects.filter(username__iexact=new_username).exclude(pk=user.pk).exists():
            messages.error(request, "Користувач з таким ім'ям вже існує.")
            return redirect('profile')

        user.username = new_username
        user.save(update_fields=['username'])
        messages.success(request, 'Ім’я користувача оновлено.')

        return redirect('profile')

    return render(request, "account/profile.html", {"user": user})

@custom_login_required
def notification_settings(request):
    settings, _created = NotificationSetting.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        settings.notify_order_created = request.POST.get('notify_order_created') == 'on'
        settings.notify_order_finished = request.POST.get('notify_order_finished') == 'on'
        settings.notify_order_created_pause = request.POST.get('notify_order_created_pause') == 'on'
        settings.save()
        messages.success(request, 'Налаштування сповіщень оновлено.')

        return redirect('notification_settings')

    return render(request, "account/notification_settings.html", {"settings": settings})


@custom_login_required
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not current_password or not new_password or not confirm_password:
            messages.error(request, 'Будь ласка, заповніть всі поля.')
            return redirect('change_password')

        if new_password != confirm_password:
            messages.error(request, 'Нові паролі не співпадають.')
            return redirect('change_password')

        if not request.user.check_password(current_password):
            messages.error(request, 'Поточний пароль невірний.')
            return redirect('change_password')

        try:
            validate_password(new_password, request.user)
        except ValidationError as exc:
            for error in exc.messages:
                messages.error(request, error)
            return redirect('change_password')

        request.user.set_password(new_password)
        request.user.save()

        update_session_auth_hash(request, request.user)

        messages.success(request, 'Пароль успішно змінено.')
        return redirect('profile')

    return render(request, "account/change_password.html")


@csrf_exempt
def send_delayed_notifications(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'invalid method'}, status=405)

    is_valid, error = _validate_internal_token(request)
    if not is_valid:
        status = 500 if error == "token not configured" else 403
        return JsonResponse({'error': error}, status=status)

    service = _get_delayed_notification_service()
    status = service.send_delayed_notifications()
    return JsonResponse({'status': status})
