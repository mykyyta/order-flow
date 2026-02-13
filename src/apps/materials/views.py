from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, UpdateView
from django.db.models.functions import Lower

from apps.materials.forms import MaterialColorForm, MaterialForm
from apps.materials.models import Material, MaterialColor


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


class MaterialDetailView(LoginRequiredMixin, UpdateView):
    """Material detail page with inline name editing and colors list."""

    login_url = reverse_lazy("auth_login")
    model = Material
    form_class = MaterialForm
    template_name = "materials/material_detail.html"
    context_object_name = "material"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = self.object.name
        context["back_url"] = reverse_lazy("materials")
        context["back_label"] = "Матеріали"

        # Actions menu for material
        actions = []
        if self.object.archived_at:
            actions.append({
                "label": "Відновити",
                "url": reverse("material_unarchive", kwargs={"pk": self.object.pk}),
                "method": "post",
                "icon": "restore",
            })
        else:
            actions.append({
                "label": "В архів",
                "url": reverse("material_archive", kwargs={"pk": self.object.pk}),
                "method": "post",
                "icon": "archive",
            })
        context["actions"] = actions

        # Colors list
        context["colors"] = self.object.colors.filter(
            archived_at__isnull=True
        ).order_by(Lower("name"), "name", "code")
        context["colors_archive_url"] = reverse(
            "material_colors_archive",
            kwargs={"pk": self.object.pk},
        )

        return context

    def form_valid(self, form):
        messages.success(self.request, "Готово! Матеріал оновлено.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("material_detail", kwargs={"pk": self.object.pk})


@login_required(login_url=reverse_lazy("auth_login"))
def materials_archive(request):
    materials = Material.objects.filter(archived_at__isnull=False).order_by("name")
    return render(
        request,
        "materials/materials_archive.html",
        {
            "page_title": "Архів матеріалів",
            "items": materials,
            "back_url": reverse_lazy("materials"),
            "empty_message": "Архів порожній.",
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
@require_POST
def material_archive(request, pk: int):
    material = get_object_or_404(Material, pk=pk)
    if material.archived_at is None:
        material.archived_at = timezone.now()
        material.save(update_fields=["archived_at"])
        messages.success(request, "Готово! Матеріал відправлено в архів.")
    return redirect("material_detail", pk=pk)


@login_required(login_url=reverse_lazy("auth_login"))
@require_POST
def material_unarchive(request, pk: int):
    material = get_object_or_404(Material, pk=pk)
    if material.archived_at is not None:
        material.archived_at = None
        material.save(update_fields=["archived_at"])
        messages.success(request, "Готово! Матеріал відновлено з архіву.")
    return redirect("material_detail", pk=pk)


# Material Color views


class MaterialColorCreateView(LoginRequiredMixin, CreateView):
    """Drawer form for adding a new color to a material."""

    login_url = reverse_lazy("auth_login")
    model = MaterialColor
    form_class = MaterialColorForm
    template_name = "materials/color_drawer.html"

    def dispatch(self, request, *args, **kwargs):
        self.material = get_object_or_404(Material, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["drawer_title"] = "Новий колір"
        context["back_url"] = reverse("material_detail", kwargs={"pk": self.material.pk})
        context["material"] = self.material
        context["color"] = None
        return context

    def form_valid(self, form):
        form.instance.material = self.material
        messages.success(self.request, "Готово! Колір додано.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("material_detail", kwargs={"pk": self.material.pk})


class MaterialColorUpdateView(LoginRequiredMixin, UpdateView):
    """Drawer form for editing a material color."""

    login_url = reverse_lazy("auth_login")
    model = MaterialColor
    form_class = MaterialColorForm
    template_name = "materials/color_drawer.html"
    pk_url_kwarg = "color_pk"

    def dispatch(self, request, *args, **kwargs):
        self.material = get_object_or_404(Material, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return MaterialColor.objects.filter(material=self.material)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["drawer_title"] = "Редагувати колір"
        context["back_url"] = reverse("material_detail", kwargs={"pk": self.material.pk})
        context["material"] = self.material
        context["color"] = self.object
        return context

    def form_valid(self, form):
        messages.success(self.request, "Готово! Колір оновлено.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("material_detail", kwargs={"pk": self.material.pk})


@login_required(login_url=reverse_lazy("auth_login"))
@require_POST
def material_color_archive(request, pk: int, color_pk: int):
    material = get_object_or_404(Material, pk=pk)
    color = get_object_or_404(MaterialColor, pk=color_pk, material=material)
    if color.archived_at is None:
        color.archived_at = timezone.now()
        color.save(update_fields=["archived_at"])
        messages.success(request, "Готово! Колір відправлено в архів.")
    return redirect("material_detail", pk=pk)


@login_required(login_url=reverse_lazy("auth_login"))
def material_colors_archive(request, pk: int):
    material = get_object_or_404(Material, pk=pk)
    colors = material.colors.filter(archived_at__isnull=False).order_by(
        Lower("name"),
        "name",
        "code",
    )
    return render(
        request,
        "materials/colors_archive.html",
        {
            "page_title": f"Архів кольорів · {material.name}",
            "material": material,
            "items": colors,
            "back_url": reverse("material_detail", kwargs={"pk": material.pk}),
            "empty_message": "Архів порожній.",
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
@require_POST
def material_color_unarchive(request, pk: int, color_pk: int):
    material = get_object_or_404(Material, pk=pk)
    color = get_object_or_404(MaterialColor, pk=color_pk, material=material)
    if color.archived_at is not None:
        color.archived_at = None
        color.save(update_fields=["archived_at"])
        messages.success(request, "Готово! Колір відновлено з архіву.")
    return redirect("material_colors_archive", pk=pk)


# Supplier and Purchase Order views


@login_required(login_url=reverse_lazy("auth_login"))
def suppliers_list(request):
    """Placeholder view for suppliers list."""
    return render(
        request,
        "materials/suppliers.html",
        {"page_title": "Постачальники"},
    )


@login_required(login_url=reverse_lazy("auth_login"))
def purchases_list(request):
    """Placeholder view for purchase orders list."""
    return render(
        request,
        "materials/purchases.html",
        {"page_title": "Закупівлі"},
    )
