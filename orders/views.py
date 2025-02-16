from django.contrib import messages
from django.contrib.auth.models import Group
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, UpdateView
from .models import ProductModel, Color, Order
from .forms import ProductModelForm, ColorForm, OrderStatusUpdateForm
from orders.forms import OrderForm
from orders.models import OrderStatusHistory
from django.urls import reverse_lazy
from django.db import models
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

@custom_login_required
def auth_user(request):
    return JsonResponse({'username': request.user.username})

def auth_logout(request):
    logout(request)
    return JsonResponse({'message': 'Logout successful'}, status=200)

@custom_login_required
def current_orders_list(request):
    if request.method == "POST":
        # Форма для зміни статусу
        form = OrderStatusUpdateForm(request.POST)
        if form.is_valid():
            selected_orders = form.cleaned_data['orders']
            new_status = form.cleaned_data['new_status']

            if selected_orders:  # Перевіряємо, чи є вибрані замовлення
                # Створення запису в історії зміни статусу для кожного замовлення
                for order in selected_orders:
                    OrderStatusHistory.objects.create(
                        order=order,
                        new_status=new_status,
                        changed_by=request.user
                    )

                    # Update the 'finished_at' field if status is 'finished'
                    if new_status.lower() == "finished":
                        order.finished_at = timezone.now()
                        order.save()
                        manager_telegram_ids = get_telegram_ids_for_group(Group.objects.get(name="Manager"))
                        if manager_telegram_ids:
                            message = (
                                f"Замовлення завершено: {order.model.name}, {order.color.name}."
                            )
                            for telegram_id in manager_telegram_ids:
                                send_tg_message(telegram_id, message)

                messages.success(request, "Статус оновлено для вибраних замовлень.")
            else:
                messages.warning(request, "Не вибрано жодного замовлення для оновлення статусу.")
            return redirect("current_orders_list")
        else:
            messages.error(request, "Виникла помилка. Спробуйте ще раз.")


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
    paginator = Paginator(orders, 20)  # 20 замовлень на сторінку

    # Отримуємо номер сторінки із параметрів URL
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)  # Поточна сторінка

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

            telegram_ids = get_telegram_ids_for_group(Group.objects.get(name="Master"))

            if telegram_ids:
                order_details = generate_order_details(order)
                message = (
                    f"+ {order_details}"
                    f"\n{request.build_absolute_uri(reverse_lazy('current_orders_list'))}\n"
                )
                for telegram_id in telegram_ids:
                    send_tg_message(telegram_id, message)

        return redirect('current_orders_list')

    form = OrderForm()
    return render(request, 'order_create.html', {'form': form})

@custom_login_required
def order_detail(request, order_id):
    # Fetch the order or return 404 if it doesn't exist
    order = get_object_or_404(Order, id=order_id)

    # Fetch the status history of the order
    statuses = OrderStatusHistory.objects.filter(order=order).order_by('-changed_at')

    # Prepare the response data
    order_data = {
        'id': order.id,
        'model': order.model.name,
        'color': order.color.name,
        'embroidery': order.embroidery,
        'comment': order.comment,
        'urgent': order.urgent,
        'etsy': order.etsy,
        'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S') if order.created_at else None,
        'finished_at': order.finished_at.strftime('%Y-%m-%d %H:%M:%S') if order.finished_at else None,
        'current_status': order.get_status_display(),
        'status_history': [
            {
                'id': status.id,
                'new_status': status.new_status,
                'new_status_display': dict(OrderStatusHistory.STATUS_CHOICES).get(status.new_status, 'Unknown'),
                'changed_by': status.changed_by.username if status.changed_by else 'Unknown',
                'changed_at': status.changed_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
            for status in statuses
        ]
    }

    return render(request, 'order_detail.html', {'order': order_data})



class ProductModelListCreateView(View):
    template_name = 'model_list_create.html'

    def get(self, request, *args, **kwargs):
        # Cписок об'єктів — логіка ListView
        models = ProductModel.objects.all()
        form = ProductModelForm()
        return render(request, self.template_name, {'models': models, 'form': form})

    def post(self, request, *args, **kwargs):
        # Форма для створення нового об'єкта — логіка CreateView
        form = ProductModelForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(reverse_lazy('model_list'))  # Перенаправлення після створення
        # Якщо форма невалідна, знову відображаємо список і форму з помилками
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
            return redirect('color_list')  # Перенаправлення після додавання
        return self.get(request, *args, **kwargs)  # Повернення на ту ж сторінку, якщо помилка

class ColorDetailUpdateView(UpdateView):
    model = Color
    template_name = 'color_detail_update.html'
    fields = ['name', 'code', 'availability_status']  # Поля, які можна редагувати
    context_object_name = 'color'

    def get_context_data(self, **kwargs):
        # Додаємо контекст з поточними даними об’єкта
        context = super().get_context_data(**kwargs)
        context['color'] = self.object
        return context

    def get_success_url(self):
        # Використовуємо цей метод, щоб перенаправити користувача на ту ж сторінку після оновлення
        return reverse_lazy('color_detail_update', kwargs={'pk': self.object.pk})


