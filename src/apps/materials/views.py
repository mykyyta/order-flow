from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import UpdateView

from apps.materials.forms import MaterialForm
from apps.materials.models import Material


class MaterialListCreateView(LoginRequiredMixin, View):
    login_url = reverse_lazy("auth_login")
    template_name = "materials/materials.html"

    def get(self, request, *args, **kwargs):
        materials = Material.objects.filter(archived_at__isnull=True).order_by("name")
        form = MaterialForm()
        return render(
            request,
            self.template_name,
            {"page_title": "Матеріали", "materials": materials, "form": form},
        )

    def post(self, request, *args, **kwargs):
        form = MaterialForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(reverse_lazy("materials"))
        materials = Material.objects.filter(archived_at__isnull=True).order_by("name")
        return render(
            request,
            self.template_name,
            {"page_title": "Матеріали", "materials": materials, "form": form},
        )


class MaterialDetailUpdateView(LoginRequiredMixin, UpdateView):
    login_url = reverse_lazy("auth_login")
    model = Material
    form_class = MaterialForm
    template_name = "materials/material_edit.html"
    context_object_name = "material"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Підправити матеріал"
        context["material"] = self.object
        return context

    def form_valid(self, form):
        messages.success(self.request, "Готово! Матеріал оновлено.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("materials")


@login_required(login_url=reverse_lazy("auth_login"))
@require_POST
def material_archive(request, pk: int):
    material = get_object_or_404(Material, pk=pk)
    if material.archived_at is None:
        material.archived_at = timezone.now()
        material.save(update_fields=["archived_at"])
        messages.success(request, "Готово! Матеріал відправлено в архів.")
    return redirect("materials")


@login_required(login_url=reverse_lazy("auth_login"))
@require_POST
def material_unarchive(request, pk: int):
    material = get_object_or_404(Material, pk=pk)
    if material.archived_at is not None:
        material.archived_at = None
        material.save(update_fields=["archived_at"])
        messages.success(request, "Готово! Матеріал відновлено з архіву.")
    return redirect("materials")

