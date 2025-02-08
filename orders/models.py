import uuid
from django.db import models
from django.contrib.auth.models import User

class ProductModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class Color(models.Model):
    AVAILABILITY_CHOICES = [
        ('in_stock', 'В наявності'),
        ('low_stock', 'Закінчується'),
        ('out_of_stock', 'Немає'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    code = models.IntegerField(unique=True)
    availability_status = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='in_stock')

    def __str__(self):
        return f"{self.name} (Код: {self.code}, {self.get_availability_status_display()})"

class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model = models.ForeignKey(ProductModel, on_delete=models.CASCADE)
    color = models.ForeignKey(Color, on_delete=models.CASCADE)
    embroidery = models.BooleanField(default=False)
    comment = models.TextField(blank=True, null=True)
    urgent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_status(self):
        latest_status = self.history.order_by('-changed_at').first()
        return latest_status.new_status if latest_status else "Немає статусу"

    def __str__(self):
        return f"{self.model.name} ({self.color.name}) - {self.get_status()}"

class OrderStatusHistory(models.Model):
    STATUS_CHOICES = [
        ('new', 'Нове'),
        ('embroidery', 'На вишивці'),
        ('almost_finished', 'Майже готове'),
        ('finished', 'Готове'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="history")
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    new_status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order.id} → {self.new_status} ({self.changed_at})"
