from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, UpdateView
from django.views.decorators.http import require_POST
from django.utils import timezone

from .forms import ColorForm, ProductModelForm
from .models import Color, ProductModel


class ProductModelListCreateView(LoginRequiredMixin, View):
    login_url = reverse_lazy("auth_login")
    template_name = "catalog/product_models.html"

    def get(self, request, *args, **kwargs):
        product_models = ProductModel.objects.filter(archived_at__isnull=True).order_by("name")
        form = ProductModelForm()
        return render(
            request,
            self.template_name,
            {"page_title": "Моделі", "models": product_models, "form": form},
        )

    def post(self, request, *args, **kwargs):
        form = ProductModelForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(reverse_lazy("product_models"))
        product_models = ProductModel.objects.filter(archived_at__isnull=True).order_by("name")
        return render(
            request,
            self.template_name,
            {"page_title": "Моделі", "models": product_models, "form": form},
        )


class ColorListCreateView(LoginRequiredMixin, ListView):
    login_url = reverse_lazy("auth_login")
    model = Color
    template_name = "catalog/colors.html"
    context_object_name = "colors"

    def get_queryset(self):
        return (
            Color.objects.filter(archived_at__isnull=True)
            .order_by(
                models.Case(
                    models.When(availability_status="in_stock", then=0),
                    models.When(availability_status="low_stock", then=1),
                    models.When(availability_status="out_of_stock", then=2),
                    default=3,
                    output_field=models.IntegerField(),
                ),
                "name",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Кольори"
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
        context["page_title"] = "Підправити колір"
        context["object"] = self.object
        context["form_id"] = "color-edit-form"
        context["cancel_url"] = reverse_lazy("colors")
        context["archive_url"] = reverse_lazy("color_archive", kwargs={"pk": self.object.pk})
        context["unarchive_url"] = reverse_lazy(
            "color_unarchive", kwargs={"pk": self.object.pk}
        )
        context["back_url"] = reverse_lazy("colors")
        context["back_label"] = "Назад до кольорів"
        context["archived_message"] = "Цей колір в архіві."
        return context

    def form_valid(self, form):
        messages.success(self.request, "Готово! Колір оновлено.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("colors")


@login_required(login_url=reverse_lazy("auth_login"))
def product_models_archive(request):
    product_models = ProductModel.objects.filter(archived_at__isnull=False).order_by("name")
    return render(
        request,
        "catalog/product_models_archive.html",
        {
            "page_title": "Архів моделей",
            "items": product_models,
            "back_url": reverse_lazy("product_models"),
            "empty_message": "Архів порожній.",
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def colors_archive(request):
    colors = Color.objects.filter(archived_at__isnull=False).order_by(
        models.Case(
            models.When(availability_status="in_stock", then=0),
            models.When(availability_status="low_stock", then=1),
            models.When(availability_status="out_of_stock", then=2),
            default=3,
            output_field=models.IntegerField(),
        ),
        "name",
    )
    return render(
        request,
        "catalog/colors_archive.html",
        {
            "page_title": "Архів кольорів",
            "items": colors,
            "back_url": reverse_lazy("colors"),
            "empty_message": "Архів порожній.",
        },
    )


class ProductModelDetailUpdateView(LoginRequiredMixin, UpdateView):
    login_url = reverse_lazy("auth_login")
    model = ProductModel
    form_class = ProductModelForm
    template_name = "catalog/product_model_edit.html"
    context_object_name = "product_model"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Підправити модель"
        context["object"] = self.object
        context["form_id"] = "product-model-edit-form"
        context["cancel_url"] = reverse_lazy("product_models")
        context["archive_url"] = reverse_lazy(
            "product_model_archive", kwargs={"pk": self.object.pk}
        )
        context["unarchive_url"] = reverse_lazy(
            "product_model_unarchive", kwargs={"pk": self.object.pk}
        )
        context["back_url"] = reverse_lazy("product_models")
        context["back_label"] = "Назад до моделей"
        context["archived_message"] = "Ця модель в архіві."
        return context

    def form_valid(self, form):
        messages.success(self.request, "Готово! Модель оновлено.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("product_models")


@login_required(login_url=reverse_lazy("auth_login"))
@require_POST
def product_model_archive(request, pk: int):
    product_model = get_object_or_404(ProductModel, pk=pk)
    if product_model.archived_at is None:
        product_model.archived_at = timezone.now()
        product_model.save(update_fields=["archived_at"])
        messages.success(request, "Готово! Модель відправлено в архів.")
    return redirect("product_model_edit", pk=pk)


@login_required(login_url=reverse_lazy("auth_login"))
@require_POST
def product_model_unarchive(request, pk: int):
    product_model = get_object_or_404(ProductModel, pk=pk)
    if product_model.archived_at is not None:
        product_model.archived_at = None
        product_model.save(update_fields=["archived_at"])
        messages.success(request, "Готово! Модель відновлено з архіву.")
    return redirect("product_model_edit", pk=pk)


@login_required(login_url=reverse_lazy("auth_login"))
@require_POST
def color_archive(request, pk: int):
    color = get_object_or_404(Color, pk=pk)
    if color.archived_at is None:
        color.archived_at = timezone.now()
        color.save(update_fields=["archived_at"])
        messages.success(request, "Готово! Колір відправлено в архів.")
    return redirect("color_edit", pk=pk)


@login_required(login_url=reverse_lazy("auth_login"))
@require_POST
def color_unarchive(request, pk: int):
    color = get_object_or_404(Color, pk=pk)
    if color.archived_at is not None:
        color.archived_at = None
        color.save(update_fields=["archived_at"])
        messages.success(request, "Готово! Колір відновлено з архіву.")
    return redirect("color_edit", pk=pk)
