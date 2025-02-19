from django.db import models
from django.contrib.auth.models import User, AbstractUser

from OrderFlow import settings


class CustomUser(AbstractUser):
    telegram_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        verbose_name="Telegram ID"
    )

    def __str__(self):
        return self.username


class ProductModel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"{self.name}"

class Color(models.Model):
    AVAILABILITY_CHOICES = [
        ('in_stock', 'В наявності'),
        ('low_stock', 'Закінчується'),
        ('out_of_stock', 'Немає'),
    ]

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    code = models.IntegerField(unique=True)
    availability_status = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='in_stock')

    def __str__(self):
        return f"{self.name}"

class Order(models.Model):
    id = models.AutoField(primary_key=True)
    model = models.ForeignKey(ProductModel, on_delete=models.CASCADE)
    color = models.ForeignKey(Color, on_delete=models.CASCADE)
    embroidery = models.BooleanField(default=False)
    comment = models.TextField(blank=True, null=True)
    urgent = models.BooleanField(default=False)
    etsy = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(blank=True, null=True)


    def get_status(self):
        latest_status = self.history.order_by('-changed_at').first()
        return latest_status.new_status if latest_status else "Немає статусу"

    def get_status_display(self):
        current_status = self.get_status()
        for value, label in OrderStatusHistory.STATUS_CHOICES:
            if current_status == value:
                return label
        return "Невідомий статус"


    def __str__(self):
        return f"{self.model.name} ({self.color.name}) - {self.get_status()}"

class OrderStatusHistory(models.Model):
    STATUS_CHOICES = [
        ('new', 'Нове'),
        ('embroidery', 'На вишивці'),
        ('almost_finished', 'Майже готове'),
        ('finished', 'Готове'),
    ]

    id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="history")
    changed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    new_status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order.id} → {self.new_status} ({self.changed_at})"

class NotificationSetting(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_settings'
    )
    notify_order_created = models.BooleanField(default=True)
    notify_order_finished = models.BooleanField(default=True)
