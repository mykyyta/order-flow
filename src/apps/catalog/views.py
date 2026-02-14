from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView
from django.views.decorators.http import require_POST
from django.utils import timezone

from .forms import (
    ColorForm,
    ProductCreateForm,
    ProductDetailForm,
    ProductMaterialForm,
)
from .models import BundleComponent, Color, Product, ProductMaterial


def _apply_product_material_role_change(
    *, product_id: int, product_material: ProductMaterial
) -> None:
    product = Product.objects.select_for_update().get(pk=product_id)

    if product_material.role == ProductMaterial.Role.PRIMARY:
        fields: list[str] = []
        if product.primary_material_id != product_material.material_id:
            product.primary_material_id = product_material.material_id
            fields.append("primary_material")
        if product.secondary_material_id == product_material.material_id:
            product.secondary_material_id = None
            fields.append("secondary_material")
        if fields:
            product.save(update_fields=fields)

    elif product_material.role == ProductMaterial.Role.SECONDARY:
        if product.secondary_material_id != product_material.material_id:
            product.secondary_material_id = product_material.material_id
            product.save(update_fields=["secondary_material"])

    else:
        fields = []
        if product.primary_material_id == product_material.material_id:
            product.primary_material_id = None
            fields.append("primary_material")
            if product.secondary_material_id is not None:
                product.secondary_material_id = None
                fields.append("secondary_material")
        elif product.secondary_material_id == product_material.material_id:
            product.secondary_material_id = None
            fields.append("secondary_material")
        if fields:
            product.save(update_fields=fields)

    # Normalize roles to match product primary/secondary (and enforce uniqueness).
    ProductDetailUpdateView._sync_product_material_roles(product=product)


class ProductListView(LoginRequiredMixin, ListView):
    login_url = reverse_lazy("auth_login")
    model = Product
    template_name = "catalog/products.html"
    context_object_name = "products"

    def get_queryset(self):
        return (
            Product.objects.filter(archived_at__isnull=True)
            .only("id", "name", "kind")
            .order_by("name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        products = list(context.get("products") or [])

        context["page_title"] = "Моделі"
        context["show_page_header"] = False
        context["product_add_url"] = reverse("product_add")

        context["standard_products"] = [p for p in products if p.kind == Product.Kind.STANDARD]
        context["bundle_products"] = [p for p in products if p.kind == Product.Kind.BUNDLE]
        context["component_products"] = [p for p in products if p.kind == Product.Kind.COMPONENT]
        return context


class ProductCreateView(LoginRequiredMixin, CreateView):
    login_url = reverse_lazy("auth_login")
    model = Product
    form_class = ProductCreateForm
    template_name = "catalog/product_create.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Додати модель"
        context["page_title_center"] = True
        context["back_url"] = reverse("products")
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Готово! Додано.")
        return response

    def get_success_url(self):
        return reverse("product_edit", kwargs={"pk": self.object.pk})


class ColorListCreateView(LoginRequiredMixin, ListView):
    login_url = reverse_lazy("auth_login")
    model = Color
    template_name = "catalog/colors.html"
    context_object_name = "colors"

    def get_queryset(self):
        return Color.objects.filter(archived_at__isnull=True).order_by(
            models.Case(
                models.When(status="in_stock", then=0),
                models.When(status="low_stock", then=1),
                models.When(status="out_of_stock", then=2),
                default=3,
                output_field=models.IntegerField(),
            ),
            "name",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Кольори"
        context["show_page_header"] = False
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
        context["unarchive_url"] = reverse_lazy("color_unarchive", kwargs={"pk": self.object.pk})
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
def products_archive(request):
    products = Product.objects.filter(archived_at__isnull=False).order_by("name")
    return render(
        request,
        "catalog/products_archive.html",
        {
            "page_title": "Архів моделей",
            "items": products,
            "back_url": reverse_lazy("products"),
            "empty_message": "Архів порожній.",
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def colors_archive(request):
    colors = Color.objects.filter(archived_at__isnull=False).order_by(
        models.Case(
            models.When(status="in_stock", then=0),
            models.When(status="low_stock", then=1),
            models.When(status="out_of_stock", then=2),
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


class ProductDetailUpdateView(LoginRequiredMixin, UpdateView):
    login_url = reverse_lazy("auth_login")
    model = Product
    form_class = ProductDetailForm
    template_name = "catalog/product_detail.html"
    context_object_name = "product"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = self.object.name
        context["back_url"] = reverse_lazy("products")
        context["back_label"] = "Моделі"

        actions = []
        if self.object.archived_at:
            actions.append(
                {
                    "label": "Відновити",
                    "url": reverse("product_unarchive", kwargs={"pk": self.object.pk}),
                    "method": "post",
                    "icon": "restore",
                }
            )
        else:
            actions.append(
                {
                    "label": "В архів",
                    "url": reverse("product_archive", kwargs={"pk": self.object.pk}),
                    "method": "post",
                    "icon": "archive",
                }
            )
        context["actions"] = actions

        context["field_groups"] = [
            {"title": "Основне", "fields": ["name", "kind", "allows_embroidery", "section"]},
        ]

        # Materials are not allowed for bundles, but we still show existing records (if any)
        # so they can be removed/cleaned up.
        context["product_materials"] = (
            ProductMaterial.objects.filter(product=self.object)
            .select_related("material")
            .order_by("sort_order", "id")
        )
        context["product_material_add_url"] = (
            None
            if self.object.kind == Product.Kind.BUNDLE
            else reverse("product_material_add", kwargs={"pk": self.object.pk})
        )

        context["bundle_components"] = (
            BundleComponent.objects.filter(bundle=self.object)
            .select_related("component")
            .order_by("-is_primary", "id")
            if self.object.kind == Product.Kind.BUNDLE
            else []
        )
        context["bundle_component_add_url"] = (
            reverse("bundle_component_add", kwargs={"pk": self.object.pk})
            if self.object.kind == Product.Kind.BUNDLE
            else None
        )
        return context

    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            self._sync_product_material_roles(product=self.object)
        messages.success(self.request, "Готово! Модель оновлено.")
        return response

    def get_success_url(self):
        return reverse("product_edit", kwargs={"pk": self.object.pk})

    @staticmethod
    def _sync_product_material_roles(*, product: Product) -> None:
        # Keep ProductMaterial in sync with primary/secondary picks, but never delete
        # user-added materials automatically.
        if product.primary_material_id:
            ProductMaterial.objects.filter(
                product=product, role=ProductMaterial.Role.PRIMARY
            ).exclude(material_id=product.primary_material_id).update(
                role=ProductMaterial.Role.OTHER
            )
            ProductMaterial.objects.update_or_create(
                product=product,
                material_id=product.primary_material_id,
                defaults={"role": ProductMaterial.Role.PRIMARY},
            )
        else:
            ProductMaterial.objects.filter(
                product=product, role=ProductMaterial.Role.PRIMARY
            ).update(role=ProductMaterial.Role.OTHER)

        if product.secondary_material_id:
            ProductMaterial.objects.filter(
                product=product, role=ProductMaterial.Role.SECONDARY
            ).exclude(material_id=product.secondary_material_id).update(
                role=ProductMaterial.Role.OTHER
            )
            ProductMaterial.objects.update_or_create(
                product=product,
                material_id=product.secondary_material_id,
                defaults={"role": ProductMaterial.Role.SECONDARY},
            )
        else:
            ProductMaterial.objects.filter(
                product=product, role=ProductMaterial.Role.SECONDARY
            ).update(role=ProductMaterial.Role.OTHER)


class ProductMaterialCreateView(LoginRequiredMixin, CreateView):
    login_url = reverse_lazy("auth_login")
    model = ProductMaterial
    form_class = ProductMaterialForm
    template_name = "catalog/product_material_drawer.html"

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(Product, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["product"] = self.product
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["drawer_title"] = "Новий матеріал"
        context["back_url"] = reverse("product_edit", kwargs={"pk": self.product.pk})
        context["product"] = self.product
        context["product_material"] = None
        return context

    def form_valid(self, form):
        with transaction.atomic():
            obj: ProductMaterial = form.save(commit=False)
            obj.product = self.product
            obj.sort_order = (
                ProductMaterial.objects.filter(product=self.product).aggregate(
                    max_order=models.Max("sort_order")
                )["max_order"]
                or 0
            ) + 1
            if obj.role in (ProductMaterial.Role.PRIMARY, ProductMaterial.Role.SECONDARY):
                ProductMaterial.objects.filter(product=self.product, role=obj.role).update(
                    role=ProductMaterial.Role.OTHER
                )
            obj.save()
            self.object = obj
            _apply_product_material_role_change(product_id=self.product.pk, product_material=obj)
        messages.success(self.request, "Готово! Матеріал додано.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("product_edit", kwargs={"pk": self.product.pk})


class ProductMaterialUpdateView(LoginRequiredMixin, UpdateView):
    login_url = reverse_lazy("auth_login")
    model = ProductMaterial
    form_class = ProductMaterialForm
    template_name = "catalog/product_material_drawer.html"
    pk_url_kwarg = "pm_pk"

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(Product, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return ProductMaterial.objects.filter(product=self.product).select_related("material")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["product"] = self.product
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["drawer_title"] = "Редагувати матеріал"
        context["back_url"] = reverse("product_edit", kwargs={"pk": self.product.pk})
        context["product"] = self.product
        context["product_material"] = self.object
        return context

    def form_valid(self, form):
        with transaction.atomic():
            obj: ProductMaterial = form.save(commit=False)
            if obj.role in (ProductMaterial.Role.PRIMARY, ProductMaterial.Role.SECONDARY):
                ProductMaterial.objects.filter(product=self.product, role=obj.role).exclude(
                    pk=obj.pk
                ).update(role=ProductMaterial.Role.OTHER)
            obj.save()
            self.object = obj
            _apply_product_material_role_change(product_id=self.product.pk, product_material=obj)
        messages.success(self.request, "Готово! Матеріал оновлено.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("product_edit", kwargs={"pk": self.product.pk})


class BundleComponentCreateView(LoginRequiredMixin, CreateView):
    login_url = reverse_lazy("auth_login")
    model = BundleComponent
    form_class = None  # set below to avoid circular import in type checking
    template_name = "catalog/bundle_component_drawer.html"

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(Product, pk=kwargs["pk"])
        if self.product.kind != Product.Kind.BUNDLE:
            messages.error(request, "Компоненти можна додавати лише для комплектів.")
            return redirect("product_edit", pk=self.product.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        from .forms import BundleComponentForm

        return BundleComponentForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["bundle"] = self.product
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["drawer_title"] = "Додати компонент"
        context["back_url"] = reverse("product_edit", kwargs={"pk": self.product.pk})
        context["product"] = self.product
        context["bundle_component"] = None
        return context

    def form_valid(self, form):
        from .forms import BundleComponentForm

        assert isinstance(form, BundleComponentForm)
        with transaction.atomic():
            obj: BundleComponent = form.save(commit=False)
            obj.bundle = self.product
            obj.save()
            if obj.is_primary:
                BundleComponent.objects.filter(bundle=self.product).exclude(pk=obj.pk).update(
                    is_primary=False
                )
            self.object = obj
        messages.success(self.request, "Готово! Компонент додано.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("product_edit", kwargs={"pk": self.product.pk})


class BundleComponentUpdateView(LoginRequiredMixin, UpdateView):
    login_url = reverse_lazy("auth_login")
    model = BundleComponent
    form_class = None  # set below
    template_name = "catalog/bundle_component_drawer.html"
    pk_url_kwarg = "bc_pk"

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(Product, pk=kwargs["pk"])
        if self.product.kind != Product.Kind.BUNDLE:
            messages.error(request, "Компоненти можна редагувати лише для комплектів.")
            return redirect("product_edit", pk=self.product.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        from .forms import BundleComponentForm

        return BundleComponentForm

    def get_queryset(self):
        return BundleComponent.objects.filter(bundle=self.product).select_related("component")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["bundle"] = self.product
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["drawer_title"] = "Редагувати компонент"
        context["back_url"] = reverse("product_edit", kwargs={"pk": self.product.pk})
        context["product"] = self.product
        context["bundle_component"] = self.object
        return context

    def form_valid(self, form):
        from .forms import BundleComponentForm

        assert isinstance(form, BundleComponentForm)
        with transaction.atomic():
            obj: BundleComponent = form.save()
            if obj.is_primary:
                BundleComponent.objects.filter(bundle=self.product).exclude(pk=obj.pk).update(
                    is_primary=False
                )
            self.object = obj
        messages.success(self.request, "Готово! Компонент оновлено.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("product_edit", kwargs={"pk": self.product.pk})


@login_required(login_url=reverse_lazy("auth_login"))
@require_POST
def bundle_component_delete(request, pk: int, bc_pk: int):
    product = get_object_or_404(Product, pk=pk)
    component = get_object_or_404(BundleComponent, pk=bc_pk, bundle=product)
    component.delete()
    messages.success(request, "Готово! Компонент видалено з комплекту.")
    return redirect("product_edit", pk=pk)


@login_required(login_url=reverse_lazy("auth_login"))
@require_POST
def product_archive(request, pk: int):
    product = get_object_or_404(Product, pk=pk)
    if product.archived_at is None:
        product.archived_at = timezone.now()
        product.save(update_fields=["archived_at"])
        messages.success(request, "Готово! Модель відправлено в архів.")
    return redirect("product_edit", pk=pk)


@login_required(login_url=reverse_lazy("auth_login"))
@require_POST
def product_unarchive(request, pk: int):
    product = get_object_or_404(Product, pk=pk)
    if product.archived_at is not None:
        product.archived_at = None
        product.save(update_fields=["archived_at"])
        messages.success(request, "Готово! Модель відновлено з архіву.")
    return redirect("product_edit", pk=pk)


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


@login_required(login_url=reverse_lazy("auth_login"))
@require_POST
def product_material_delete(request, pk: int, pm_pk: int):
    product = get_object_or_404(Product, pk=pk)
    pm = get_object_or_404(ProductMaterial, pk=pm_pk, product=product)

    # Prevent deleting the effective primary/secondary. User must demote first.
    if pm.role in (ProductMaterial.Role.PRIMARY, ProductMaterial.Role.SECONDARY):
        messages.error(
            request,
            "Не можна видалити основний/другорядний матеріал. Спочатку зміни роль на 'Інший'.",
        )
        return redirect("product_material_edit", pk=pk, pm_pk=pm_pk)
    if pm.material_id in {product.primary_material_id, product.secondary_material_id}:
        messages.error(
            request,
            "Не можна видалити матеріал, який встановлено як основний/другорядний. "
            "Спочатку зміни статус.",
        )
        return redirect("product_material_edit", pk=pk, pm_pk=pm_pk)

    pm.delete()
    messages.success(request, "Готово! Матеріал видалено з моделі.")
    return redirect("product_edit", pk=pk)
