from django.contrib import messages
from django.contrib.auth.models import Group
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.utils import timezone
from django.utils.timezone import localtime, now
from django.views import View
from django.views.generic import ListView, UpdateView
from .models import ProductModel, Color, Order, NotificationSetting
from .forms import ProductModelForm, ColorForm, OrderStatusUpdateForm
from orders.forms import OrderForm
from orders.models import OrderStatusHistory
from django.urls import reverse_lazy
from django.db import models, transaction
from .utils import send_tg_message, get_telegram_ids_for_group, generate_order_details



def custom_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('auth_login')
        return view_func(request, *args, **kwargs)
    return wrapper

@custom_login_required
def index(request):
    return redirect('current_orders_list')

def auth_login(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not username or not password:
            return JsonResponse({'message': 'Username and password are required'}, status=400)

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

            return redirect('index')
        else:
            return JsonResponse({'message': 'Invalid credentials'}, status=401)

    else:
        return render(request, 'login.html')


def auth_logout(request):
    logout(request)
    return redirect('auth_login')

@custom_login_required
def current_orders_list(request):
    if request.method == "POST":
        form = OrderStatusUpdateForm(request.POST)
        if form.is_valid():
            selected_orders = form.cleaned_data['orders']
            new_status = form.cleaned_data['new_status']

            if selected_orders:
                with transaction.atomic():
                    for order in selected_orders:
                        latest_status_history = (
                            OrderStatusHistory.objects.filter(order=order)
                            .order_by('-id')
                            .first()
                        )
                        if latest_status_history and latest_status_history.new_status == new_status: continue


                        OrderStatusHistory.objects.create(
                            order=order,
                            new_status=new_status,
                            changed_by=request.user
                        )

                        if new_status.lower() == "finished":
                            order.finished_at = timezone.now()
                            order.save()
                            users_to_notify = NotificationSetting.objects.filter(
                                notify_order_finished=True).select_related('user')

                            for setting in users_to_notify:
                                user = setting.user
                                if user.telegram_id:
                                    message = f"Замовлення завершено: {order.model.name}, {order.color.name}."
                                    send_tg_message(user.telegram_id, message)

                messages.success(request, "Статус оновлено для вибраних замовлень.")
            else:
                messages.warning(request, "Не вибрано жодного замовлення для оновлення статусу.")
            return redirect("current_orders_list")
        else:
            messages.error(request, "Виникла помилка. Зробіть ще одну спробу.")


    orders_queryset = Order.objects.filter(finished_at__isnull=True)
    form = OrderStatusUpdateForm()
    form.fields['orders'].queryset = orders_queryset


    return render(request,
                  "current_orders_list.html",
                    {
                        "form": form,
                        "orders": orders_queryset,
                             }
                )


@custom_login_required
def finished_orders_list(request):
    orders = Order.objects.filter(finished_at__isnull=False).order_by('-finished_at')  # Фільтруємо завершені
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'finished_orders_list.html', {'page_obj': page_obj})


@custom_login_required
def order_create(request):
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save()
            OrderStatusHistory.objects.create(
                order=order,
                changed_by=request.user,
                new_status='new'
            )

            users_to_notify = NotificationSetting.objects.filter(
                notify_order_created=True,
                user__telegram_id__isnull=False
            ).select_related('user')

            if users_to_notify:
                order_details = generate_order_details(order)
                message = (
                    f"+ {order_details}"
                    f"\n{request.build_absolute_uri(reverse_lazy('current_orders_list'))}\n"
                )

                for setting in users_to_notify:

                    if setting.notify_order_created_pause:
                        current_time = localtime(now())
                        current_hour = current_time.hour
                        WORKING_HOURS_START = 8
                        WORKING_HOURS_END = 18
                        if current_hour < WORKING_HOURS_START or current_hour >= WORKING_HOURS_END:
                            continue
                    send_tg_message(setting.user.telegram_id, message)

        return redirect('current_orders_list')

    form = OrderForm()
    return render(request, 'order_create.html', {'form': form})

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
        'current_status': order.get_status_display(),
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

    return render(request, 'order_detail.html', {'order': order_data})



class ProductModelListCreateView(View):
    template_name = 'model_list_create.html'

    def get(self, request, *args, **kwargs):
        models = ProductModel.objects.all()
        form = ProductModelForm()
        return render(request, self.template_name, {'models': models, 'form': form})

    def post(self, request, *args, **kwargs):
        form = ProductModelForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(reverse_lazy('model_list'))
        models = ProductModel.objects.all()
        return render(request, self.template_name, {'models': models, 'form': form})



class ColorListCreateView(ListView):
    model = Color
    template_name = 'color_list_create.html'
    context_object_name = 'colors'

    def get_queryset(self):
        return Color.objects.order_by(
            models.Case(
                models.When(availability_status='out_of_stock', then=2),
                models.When(availability_status='low_stock', then=1),
                models.When(availability_status='in_stock', then=0),
                default=3,
                output_field=models.IntegerField()
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['color_form'] = ColorForm()
        return context

    def post(self, request, *args, **kwargs):
        form = ColorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('color_list')
        return self.get(request, *args, **kwargs)

class ColorDetailUpdateView(UpdateView):
    model = Color
    form_class = ColorForm
    template_name = 'color_detail_update.html'
    context_object_name = 'color'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['color'] = self.object
        return context

    def get_success_url(self):
        return reverse_lazy('color_detail_update', kwargs={'pk': self.object.pk})

@custom_login_required
def profile_view(request):
    user = request.user

    if request.method == 'POST':
        new_username = request.POST.get('username')

        if new_username:
            user.username = new_username
            user.save()
            messages.success(request, 'Ім’я користувача оновлено.')

        return redirect('profile')

    return render(request, 'profile.html', {'user': user})

@custom_login_required
def notification_settings(request):
    settings = request.user.notification_settings

    if request.method == 'POST':
        settings.notify_order_created = request.POST.get('notify_order_created') == 'on'
        settings.notify_order_finished = request.POST.get('notify_order_finished') == 'on'
        settings.notify_order_created_pause = request.POST.get('notify_order_created_pause') == 'on'
        settings.save()

        return redirect('notification_settings')

    return render(request, 'notification_settings.html', {'settings': settings})


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

        request.user.set_password(new_password)
        request.user.save()

        update_session_auth_hash(request, request.user)

        messages.success(request, 'Пароль успішно змінено.')
        return redirect('profile')

    return render(request, 'change_password.html')

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import localtime, now, timedelta, make_aware, datetime
from orders.models import Order, NotificationSetting
from orders.utils import send_tg_message, generate_order_details

@csrf_exempt
def send_delayed_notifications(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'invalid method'}, status=405)

    current_time = localtime(now())
    today = current_time.date()

    yesterday_18 = make_aware(datetime.combine(today - timedelta(days=1), datetime.min.time().replace(hour=18)))

    today_08 = make_aware(datetime.combine(today, datetime.min.time().replace(hour=8)))

    # Замовлення, створені після 18:00 до 08:00
    orders_to_notify = Order.objects.filter(
        created_at__gte=yesterday_18,
        created_at__lt=today_08
    )

    if not orders_to_notify.exists():
        return JsonResponse({'status': 'no orders to notify'})

    # Беремо користувачів, які хочуть отримувати відкладені сповіщення
    users_to_notify = NotificationSetting.objects.filter(
        notify_order_created=True,
        notify_order_created_pause=True,
        user__telegram_id__isnull=False
    ).select_related('user')

    if not users_to_notify.exists():
        return JsonResponse({'status': 'no users to notify'})

    # Групуємо замовлення для кожного користувача
    for setting in users_to_notify:
        user_orders = []
        for order in orders_to_notify:
            order_details = generate_order_details(order)
            user_orders.append(f"+ {order_details}")

        if user_orders:
            message = "\n".join(user_orders)
            send_tg_message(setting.user.telegram_id, message)

    return JsonResponse({'status': 'delayed notifications sent'})




