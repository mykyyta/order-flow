from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, UpdateView

from .forms import ColorForm, ProductModelForm
from .models import Color, ProductModel


class ProductModelListCreateView(LoginRequiredMixin, View):
    login_url = reverse_lazy("auth_login")
    template_name = "catalog/product_models.html"

    def get(self, request, *args, **kwargs):
        product_models = ProductModel.objects.order_by("name")
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
        product_models = ProductModel.objects.order_by("name")
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
        return Color.objects.order_by(
            models.Case(
                models.When(availability_status="in_stock", then=0),
                models.When(availability_status="low_stock", then=1),
                models.When(availability_status="out_of_stock", then=2),
                default=3,
                output_field=models.IntegerField(),
            ),
            "name",
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
        context["color"] = self.object
        return context

    def form_valid(self, form):
        messages.success(self.request, "Готово! Колір оновлено.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("colors")
