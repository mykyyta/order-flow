from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
import json

# Головна сторінка
def custom_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('auth_login')
        return view_func(request, *args, **kwargs)
    return wrapper

@custom_login_required
def index(request):
    return render(request, 'index.html')


# Аутентифікація

def auth_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not username or not password:
            return JsonResponse({'message': 'Username and password are required'}, status=400)

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')  # Перенаправлення після входу
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

# Заглушки для замовлень

@custom_login_required
def order_list(request):
    return JsonResponse({'message': 'Список замовлень (заглушка)'})

@custom_login_required
def order_create(request):
    return JsonResponse({'message': 'Створення замовлення (заглушка)'})

@custom_login_required
def order_detail(request, order_id):
    return JsonResponse({'message': f'Деталі замовлення {order_id} (заглушка)'})

@custom_login_required
def order_update(request, order_id):
    return JsonResponse({'message': f'Оновлення замовлення {order_id} (заглушка)'})

@custom_login_required
def order_history(request, order_id):
    return JsonResponse({'message': f'Історія змін статусу замовлення {order_id} (заглушка)'})

# Заглушки для моделей виробів

@custom_login_required
def model_list(request):
    return JsonResponse({'message': 'Список моделей (заглушка)'})

@custom_login_required
def model_detail(request, model_id):
    return JsonResponse({'message': f'Деталі моделі {model_id} (заглушка)'})

# Заглушки для кольорів

@custom_login_required
def color_list(request):
    return JsonResponse({'message': 'Список кольорів (заглушка)'})

@custom_login_required
def color_detail(request, color_id):
    return JsonResponse({'message': f'Деталі кольору {color_id} (заглушка)'})
