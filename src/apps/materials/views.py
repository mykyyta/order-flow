from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView, UpdateView
from django.db.models.functions import Lower
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from apps.materials.forms import (
    MaterialColorForm,
    MaterialForm,
    PurchaseAddFromOfferForm,
    PurchaseOrderFilterForm,
    PurchaseOrderStartForm,
    PurchaseOrderLineForm,
    PurchaseOrderLineReceiveForm,
    PurchaseOrderStatusForm,
    PurchaseRequestForm,
    PurchaseRequestLineForm,
    PurchaseRequestLineOrderForm,
    SupplierForm,
    SupplierMaterialOfferForm,
    SupplierMaterialOfferStartForm,
)
from apps.materials.models import (
    Material,
    MaterialColor,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseRequest,
    PurchaseRequestLine,
    Supplier,
    SupplierMaterialOffer,
)
from apps.materials.services import receive_purchase_order_line
from apps.warehouses.services import get_default_warehouse


class MaterialListView(LoginRequiredMixin, ListView):
    login_url = reverse_lazy("auth_login")
    model = Material
    template_name = "materials/materials.html"
    context_object_name = "materials"

    def get_queryset(self):
        return Material.objects.filter(archived_at__isnull=True).only("id", "name").order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Матеріали"
        context["show_page_header"] = False
        context["material_add_url"] = reverse("material_add")
        return context


class MaterialCreateView(LoginRequiredMixin, CreateView):
    login_url = reverse_lazy("auth_login")
    model = Material
    form_class = MaterialForm
    template_name = "materials/material_create.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Додати матеріал"
        context["page_title_center"] = True
        context["back_url"] = reverse("materials")
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Готово! Додано.")
        return response

    def get_success_url(self):
        return reverse("material_detail", kwargs={"pk": self.object.pk})


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
            actions.append(
                {
                    "label": "Відновити",
                    "url": reverse("material_unarchive", kwargs={"pk": self.object.pk}),
                    "method": "post",
                    "icon": "restore",
                }
            )
        else:
            actions.append(
                {
                    "label": "В архів",
                    "url": reverse("material_archive", kwargs={"pk": self.object.pk}),
                    "method": "post",
                    "icon": "archive",
                }
            )
        context["actions"] = actions

        # Colors list
        context["colors"] = self.object.colors.filter(archived_at__isnull=True).order_by(
            Lower("name"), "name", "code"
        )
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
    search_query = (request.GET.get("q") or "").strip()
    queryset = Supplier.objects.filter(archived_at__isnull=True).order_by(Lower("name"), "name")
    if search_query:
        queryset = queryset.filter(name__icontains=search_query)

    paginator = Paginator(queryset, 50)
    page_obj = paginator.get_page(request.GET.get("page"))

    active_offers_count = SupplierMaterialOffer.objects.filter(archived_at__isnull=True).count()
    tabs = [
        {"id": "suppliers", "label": "Постачальники", "url": reverse("suppliers")},
        {"id": "offers", "label": "Офери", "url": reverse("supplier_offers"), "count": active_offers_count},
    ]

    return render(
        request,
        "materials/suppliers.html",
        {
            "page_title": "Постачальники",
            "show_page_header": False,
            "tabs": tabs,
            "active_tab": "suppliers",
            "page_obj": page_obj,
            "search_query": search_query,
            "supplier_add_url": reverse("supplier_add"),
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def supplier_offers_list(request):
    search_query = (request.GET.get("q") or "").strip()
    queryset = (
        SupplierMaterialOffer.objects.filter(archived_at__isnull=True)
        .select_related("supplier", "material", "material_color")
        .order_by(Lower("supplier__name"), "supplier__name", Lower("material__name"), "material__name", "-created_at")
    )
    if search_query:
        queryset = queryset.filter(
            Q(supplier__name__icontains=search_query)
            | Q(material__name__icontains=search_query)
            | Q(title__icontains=search_query)
            | Q(sku__icontains=search_query)
        )

    paginator = Paginator(queryset, 50)
    page_obj = paginator.get_page(request.GET.get("page"))

    active_offers_count = SupplierMaterialOffer.objects.filter(archived_at__isnull=True).count()
    tabs = [
        {"id": "suppliers", "label": "Постачальники", "url": reverse("suppliers")},
        {"id": "offers", "label": "Офери", "url": reverse("supplier_offers"), "count": active_offers_count},
    ]

    return render(
        request,
        "materials/supplier_offers.html",
        {
            "page_title": "Офери",
            "show_page_header": False,
            "tabs": tabs,
            "active_tab": "offers",
            "page_obj": page_obj,
            "search_query": search_query,
            "offer_add_url": reverse("supplier_offer_start"),
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def supplier_detail(request, pk: int):
    supplier = get_object_or_404(Supplier.objects.filter(archived_at__isnull=True), pk=pk)
    offers = list(
        supplier.offers.filter(archived_at__isnull=True)
        .select_related("material", "material_color")
        .order_by(Lower("material__name"), "material__name", "-created_at")
    )
    return render(
        request,
        "materials/supplier_detail.html",
        {
            "page_title": supplier.name,
            "page_title_center": True,
            "back_url": reverse("suppliers"),
            "supplier": supplier,
            "offers": offers,
            "purchase_create_url": reverse("supplier_purchase_create", kwargs={"pk": supplier.pk}),
            "offer_add_url": _append_query_params(
                reverse("supplier_offer_start"),
                {"supplier": str(supplier.pk), "next": reverse("supplier_detail", kwargs={"pk": supplier.pk})},
            ),
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
@require_POST
def supplier_purchase_create(request, pk: int):
    supplier = get_object_or_404(Supplier.objects.filter(archived_at__isnull=True), pk=pk)
    purchase_order = PurchaseOrder.objects.create(
        supplier=supplier,
        status=PurchaseOrder.Status.DRAFT,
        created_by=request.user,
    )
    messages.success(request, "Готово! Замовлення створено.")
    return redirect("purchase_add_lines", pk=purchase_order.pk)

def _safe_next_url(request: HttpRequest, raw_next_url: str | None, *, fallback: str) -> str:
    if not raw_next_url:
        return fallback
    if not url_has_allowed_host_and_scheme(
        raw_next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return fallback
    return raw_next_url


def _append_query_params(url: str, params: dict[str, str]) -> str:
    split = urlsplit(url)
    query = dict(parse_qsl(split.query, keep_blank_values=True))
    query.update(params)
    return urlunsplit((split.scheme, split.netloc, split.path, urlencode(query), split.fragment))


@login_required(login_url=reverse_lazy("auth_login"))
def supplier_add(request):
    raw_next_url = (request.GET.get("next") or "").strip()
    next_url = _safe_next_url(request, raw_next_url, fallback=reverse("suppliers"))

    if request.method == "POST":
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier: Supplier = form.save()
            messages.success(request, "Готово! Постачальника додано.")

            if next_url == reverse("purchase_add"):
                return redirect(_append_query_params(next_url, {"supplier": str(supplier.pk)}))

            return redirect(next_url)
    else:
        form = SupplierForm()

    return render(
        request,
        "materials/supplier_create.html",
        {
            "page_title": "Новий постачальник",
            "page_title_center": True,
            "back_url": next_url,
            "back_label": "Назад",
            "form": form,
            "submit_label": "Додати",
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def purchases_list(request):
    filter_form = PurchaseOrderFilterForm(request.GET or None)
    status = (request.GET.get("status") or "").strip()
    search_query = (request.GET.get("q") or "").strip()

    queryset = PurchaseOrder.objects.select_related("supplier").order_by("-created_at")
    if status:
        queryset = queryset.filter(status=status)
    if search_query:
        search_filters = (
            Q(supplier__name__icontains=search_query)
            | Q(external_ref__icontains=search_query)
            | Q(tracking_number__icontains=search_query)
            | Q(notes__icontains=search_query)
        )
        if search_query.isdigit():
            search_filters |= Q(id=int(search_query))
        queryset = queryset.filter(search_filters)

    paginator = Paginator(queryset, 50)
    page_obj = paginator.get_page(request.GET.get("page"))

    open_requests_count = PurchaseRequest.objects.filter(
        status__in=[PurchaseRequest.Status.OPEN, PurchaseRequest.Status.IN_PROGRESS]
    ).count()

    tabs = [
        {"id": "orders", "label": "Замовлення", "url": reverse("purchases")},
        {"id": "requests", "label": "Заявки", "url": reverse("purchase_requests"), "count": open_requests_count},
    ]

    return render(
        request,
        "materials/purchases.html",
        {
            "page_title": "Закупівлі",
            "show_page_header": False,
            "tabs": tabs,
            "active_tab": "orders",
            "page_obj": page_obj,
            "filter_form": filter_form,
            "search_query": search_query,
            "status": status,
            "purchase_start_material_url": reverse("purchase_start_material"),
            "clear_url": reverse("purchases"),
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def purchase_start_material(request):
    search_query = (request.GET.get("q") or "").strip()
    queryset = Material.objects.filter(archived_at__isnull=True).order_by(Lower("name"), "name")
    if search_query:
        queryset = queryset.filter(name__icontains=search_query)

    paginator = Paginator(queryset, 50)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "materials/purchase_start_material.html",
        {
            "page_title": "Замовити матеріал",
            "show_page_header": False,
            "back_url": reverse("purchases"),
            "back_label": "Закупівлі",
            "page_obj": page_obj,
            "search_query": search_query,
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def purchase_start_material_offers(request, material_pk: int):
    material = get_object_or_404(Material, pk=material_pk, archived_at__isnull=True)
    offers = list(
        SupplierMaterialOffer.objects.filter(material=material, archived_at__isnull=True)
        .select_related("supplier", "material_color")
        .order_by(Lower("supplier__name"), "supplier__name", "id")
    )

    return render(
        request,
        "materials/purchase_start_material_offers.html",
        {
            "page_title": "Варіанти постачальників",
            "back_url": reverse("purchase_start_material"),
            "back_label": "Матеріали",
            "material": material,
            "offers": offers,
            "offer_add_url": reverse("supplier_offer_add", kwargs={"material_pk": material.pk}),
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def supplier_offer_add(request, material_pk: int):
    material = get_object_or_404(Material, pk=material_pk, archived_at__isnull=True)
    supplier_id = None
    if request.GET.get("supplier") and str(request.GET.get("supplier")).isdigit():
        supplier_id = int(request.GET.get("supplier"))
    if request.method == "POST":
        form = SupplierMaterialOfferForm(request.POST, material=material)
        if form.is_valid():
            offer: SupplierMaterialOffer = form.save(commit=False)
            offer.material = material
            offer.unit = material.stock_unit
            offer.save()
            messages.success(request, "Готово! Офер додано.")
            next_url = (request.GET.get("next") or request.POST.get("next") or "").strip()
            safe_next = _safe_next_url(
                request,
                next_url,
                fallback=reverse("purchase_start_material_offers", kwargs={"material_pk": material.pk}),
            )
            return redirect(safe_next)
    else:
        initial = {}
        if supplier_id and Supplier.objects.filter(pk=supplier_id, archived_at__isnull=True).exists():
            initial["supplier"] = supplier_id
        form = SupplierMaterialOfferForm(initial=initial, material=material)

    return render(
        request,
        "materials/supplier_offer_create.html",
        {
            "page_title": "Новий офер",
            "page_title_center": True,
            "back_url": _safe_next_url(
                request,
                (request.GET.get("next") or "").strip(),
                fallback=reverse("purchase_start_material_offers", kwargs={"material_pk": material.pk}),
            ),
            "back_label": "Назад",
            "form": form,
            "material": material,
            "submit_label": "Додати",
            "next_url": (request.GET.get("next") or "").strip(),
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def supplier_offer_start(request):
    supplier_id = None
    if request.GET.get("supplier") and str(request.GET.get("supplier")).isdigit():
        supplier_id = int(request.GET.get("supplier"))

    next_url = _safe_next_url(
        request,
        (request.GET.get("next") or "").strip(),
        fallback=reverse("supplier_offers"),
    )

    if request.method == "POST":
        form = SupplierMaterialOfferStartForm(request.POST)
        if form.is_valid():
            supplier: Supplier = form.cleaned_data["supplier"]
            material: Material = form.cleaned_data["material"]
            url = reverse("supplier_offer_add", kwargs={"material_pk": material.pk})
            url = _append_query_params(url, {"supplier": str(supplier.pk), "next": next_url})
            return redirect(url)
    else:
        initial = {}
        if supplier_id and Supplier.objects.filter(pk=supplier_id, archived_at__isnull=True).exists():
            initial["supplier"] = supplier_id
        form = SupplierMaterialOfferStartForm(initial=initial)

    return render(
        request,
        "materials/supplier_offer_start.html",
        {
            "page_title": "Додати офер",
            "page_title_center": True,
            "back_url": next_url,
            "back_label": "Назад",
            "form": form,
            "submit_label": "Далі",
        },
    )

@login_required(login_url=reverse_lazy("auth_login"))
def purchase_add_from_offer(request, offer_pk: int):
    offer = get_object_or_404(
        SupplierMaterialOffer.objects.select_related("supplier", "material", "material_color"),
        pk=offer_pk,
        archived_at__isnull=True,
    )

    if offer.unit != offer.material.stock_unit:
        expected = offer.material.get_stock_unit_display()
        messages.error(request, f"Офер має невірну одиницю. Очікується: {expected}.")
        return redirect("purchase_start_material_offers", material_pk=offer.material_id)

    if offer.material.colors.filter(archived_at__isnull=True).exists() and offer.material_color_id is None:
        messages.error(request, "Офер без кольору. Додай офер з вибраним кольором.")
        return redirect("purchase_start_material_offers", material_pk=offer.material_id)

    if request.method == "POST":
        form = PurchaseAddFromOfferForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Упс. Перевір кількість.")
        else:
            quantity: Decimal = form.cleaned_data["quantity"]
            unit_price = form.cleaned_data.get("unit_price")
            if unit_price is None:
                unit_price = offer.price_per_unit

            with transaction.atomic():
                purchase_order = PurchaseOrder.objects.create(
                    supplier=offer.supplier,
                    status=PurchaseOrder.Status.DRAFT,
                    created_by=request.user,
                )
                PurchaseOrderLine.objects.create(
                    purchase_order=purchase_order,
                    supplier_offer=offer,
                    material=offer.material,
                    material_color=offer.material_color,
                    quantity=quantity,
                    unit=offer.material.stock_unit,
                    unit_price=unit_price,
                )

            messages.success(request, "Готово! Додано в замовлення.")
            return redirect("purchase_add_lines", pk=purchase_order.pk)
    else:
        form = PurchaseAddFromOfferForm(initial={"unit_price": offer.price_per_unit})

    return render(
        request,
        "materials/purchase_add_from_offer_form.html",
        {
            "page_title": "Додати з офера",
            "page_title_center": True,
            "back_url": reverse("purchase_start_material_offers", kwargs={"material_pk": offer.material_id}),
            "back_label": "Назад",
            "offer": offer,
            "form": form,
            "submit_label": "Додати",
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def purchase_add(request):
    supplier_id = None
    if request.GET.get("supplier") and str(request.GET.get("supplier")).isdigit():
        supplier_id = int(request.GET.get("supplier"))

    if request.method == "POST":
        form = PurchaseOrderStartForm(request.POST)
        if form.is_valid():
            purchase_order = PurchaseOrder.objects.create(
                supplier=form.cleaned_data["supplier"],
                status=PurchaseOrder.Status.DRAFT,
                created_by=request.user,
            )
            messages.success(request, "Готово! Замовлення створено.")
            return redirect("purchase_add_lines", pk=purchase_order.pk)
    else:
        initial = {}
        if supplier_id and Supplier.objects.filter(pk=supplier_id, archived_at__isnull=True).exists():
            initial["supplier"] = supplier_id
        form = PurchaseOrderStartForm(initial=initial)

    return render(
        request,
        "materials/purchase_form.html",
        {
            "page_title": "Нове замовлення",
            "page_title_center": True,
            "back_url": reverse("purchases"),
            "form": form,
            "submit_label": "Створити",
            "supplier_add_url": _append_query_params(
                reverse("supplier_add"), {"next": reverse("purchase_add")}
            ),
            "purchase_start_material_url": reverse("purchase_start_material"),
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def purchase_add_lines(request, pk: int):
    purchase_order = get_object_or_404(
        PurchaseOrder.objects.select_related("supplier"),
        pk=pk,
    )
    lines = list(
        purchase_order.lines.select_related("material", "material_color", "supplier_offer").order_by("id")
    )

    return render(
        request,
        "materials/purchase_add_lines.html",
        {
            "page_title": f"Додати позиції · Замовлення #{purchase_order.id}",
            "back_url": reverse("purchases"),
            "back_label": "Закупівлі",
            "purchase_order": purchase_order,
            "lines": lines,
            "done_url": reverse("purchase_detail", kwargs={"pk": purchase_order.pk}),
            "line_add_url": reverse("purchase_line_add", kwargs={"pk": purchase_order.pk}),
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def purchase_detail(request, pk: int):
    purchase_order = get_object_or_404(
        PurchaseOrder.objects.select_related("supplier"),
        pk=pk,
    )
    lines = list(
        purchase_order.lines.select_related("material", "material_color", "supplier_offer").order_by("id")
    )

    tabs = [
        {"id": "orders", "label": "Замовлення", "url": reverse("purchases")},
        {"id": "requests", "label": "Заявки", "url": reverse("purchase_requests")},
    ]

    actions = [
        {"label": "Змінити статус", "url": reverse("purchase_status_edit", kwargs={"pk": purchase_order.pk})},
    ]

    return render(
        request,
        "materials/purchase_detail.html",
        {
            "page_title": f"Замовлення #{purchase_order.id}",
            "tabs": tabs,
            "active_tab": "orders",
            "back_url": reverse("purchases"),
            "back_label": "Закупівлі",
            "purchase_order": purchase_order,
            "lines": lines,
            "line_add_url": reverse("purchase_line_add", kwargs={"pk": purchase_order.pk}),
            "line_add_from_request_url": reverse(
                "purchase_pick_request_line_for_order",
                kwargs={"pk": purchase_order.pk},
            ),
            "actions": actions,
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def purchase_status_edit(request, pk: int):
    purchase_order = get_object_or_404(PurchaseOrder.objects.select_related("supplier"), pk=pk)
    if request.method == "POST":
        form = PurchaseOrderStatusForm(request.POST)
        if form.is_valid():
            purchase_order.status = form.cleaned_data["status"]
            purchase_order.save(update_fields=["status", "updated_at"])
            messages.success(request, "Готово! Статус оновлено.")
            return redirect("purchase_detail", pk=purchase_order.pk)
    else:
        form = PurchaseOrderStatusForm(initial={"status": purchase_order.status})

    return render(
        request,
        "materials/purchase_status_form.html",
        {
            "page_title": "Статус замовлення",
            "page_title_center": True,
            "back_url": reverse("purchase_detail", kwargs={"pk": purchase_order.pk}),
            "form": form,
            "purchase_order": purchase_order,
            "submit_label": "Застосувати",
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def purchase_pick_request_line_for_order(request, pk: int):
    purchase_order = get_object_or_404(PurchaseOrder.objects.select_related("supplier"), pk=pk)
    search_query = (request.GET.get("q") or "").strip()

    queryset = (
        PurchaseRequestLine.objects.select_related("request", "material", "material_color")
        .exclude(status__in=[PurchaseRequestLine.Status.DONE, PurchaseRequestLine.Status.CANCELLED])
        .order_by("-request__created_at", "id")
    )
    if search_query:
        queryset = queryset.filter(
            Q(material__name__icontains=search_query) | Q(material_color__name__icontains=search_query)
        )

    paginator = Paginator(queryset, 50)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "materials/purchase_request_line_pick.html",
        {
            "page_title": "Додати з заявки",
            "show_page_header": False,
            "back_url": reverse("purchase_detail", kwargs={"pk": purchase_order.pk}),
            "purchase_order": purchase_order,
            "page_obj": page_obj,
            "search_query": search_query,
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
@require_POST
def purchase_set_status(request, pk: int):
    purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
    new_status = (request.POST.get("status") or "").strip()
    valid_statuses = {value for value, _ in PurchaseOrder.Status.choices}
    if new_status not in valid_statuses:
        messages.error(request, "Упс. Невірний статус.")
        return redirect("purchase_detail", pk=pk)

    purchase_order.status = new_status
    purchase_order.save(update_fields=["status", "updated_at"])
    messages.success(request, "Готово! Статус оновлено.")
    return redirect("purchase_detail", pk=pk)


@login_required(login_url=reverse_lazy("auth_login"))
def purchase_line_add(request, pk: int):
    purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
    raw_next_url = (request.GET.get("next") or request.POST.get("next") or "").strip()
    next_url = _safe_next_url(
        request,
        raw_next_url,
        fallback=reverse("purchase_detail", kwargs={"pk": purchase_order.pk}),
    )
    if request.method == "POST":
        form = PurchaseOrderLineForm(request.POST)
        if form.is_valid():
            line: PurchaseOrderLine = form.save(commit=False)
            line.purchase_order = purchase_order
            line.unit = line.material.stock_unit
            line.save()
            messages.success(request, "Готово! Позицію додано.")
            return redirect(next_url)
    else:
        form = PurchaseOrderLineForm()

    return render(
        request,
        "materials/purchase_line_form.html",
        {
            "page_title": f"Додати позицію · Замовлення #{purchase_order.id}",
            "page_title_center": True,
            "back_url": reverse("purchase_detail", kwargs={"pk": purchase_order.pk}),
            "form": form,
            "submit_label": "Додати",
            "next_url": next_url,
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def purchase_line_receive(request, pk: int, line_pk: int):
    purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
    line = get_object_or_404(
        PurchaseOrderLine.objects.select_related("material", "material_color", "purchase_order"),
        pk=line_pk,
        purchase_order=purchase_order,
    )
    warehouse = get_default_warehouse()

    if request.method == "POST":
        form = PurchaseOrderLineReceiveForm(request.POST)
        if form.is_valid():
            try:
                receive_purchase_order_line(
                    purchase_order_line=line,
                    quantity=form.cleaned_data["quantity"],
                    warehouse_id=warehouse.id,
                    received_by=request.user,
                    notes=form.cleaned_data.get("notes") or "",
                )
            except ValueError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, "Готово! Прийнято на склад.")
                return redirect("purchase_detail", pk=purchase_order.pk)
    else:
        form = PurchaseOrderLineReceiveForm()

    return render(
        request,
        "materials/purchase_receive_form.html",
        {
            "page_title": "Прийняти на склад",
            "page_title_center": True,
            "back_url": reverse("purchase_detail", kwargs={"pk": purchase_order.pk}),
            "form": form,
            "line": line,
            "warehouse": warehouse,
            "submit_label": "Прийняти",
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def purchase_requests_list(request):
    search_query = (request.GET.get("q") or "").strip()
    queryset = PurchaseRequest.objects.select_related("warehouse").order_by("-created_at")
    queryset = queryset.exclude(status=PurchaseRequest.Status.CANCELLED)
    if search_query:
        search_filters = Q(notes__icontains=search_query)
        if search_query.isdigit():
            search_filters |= Q(id=int(search_query))
        queryset = queryset.filter(search_filters)

    paginator = Paginator(queryset, 50)
    page_obj = paginator.get_page(request.GET.get("page"))

    open_requests_count = PurchaseRequest.objects.filter(
        status__in=[PurchaseRequest.Status.OPEN, PurchaseRequest.Status.IN_PROGRESS]
    ).count()
    tabs = [
        {"id": "orders", "label": "Замовлення", "url": reverse("purchases")},
        {"id": "requests", "label": "Заявки", "url": reverse("purchase_requests"), "count": open_requests_count},
    ]

    return render(
        request,
        "materials/purchase_requests.html",
        {
            "page_title": "Заявки на закупівлю",
            "show_page_header": False,
            "tabs": tabs,
            "active_tab": "requests",
            "page_obj": page_obj,
            "search_query": search_query,
            "request_add_url": reverse("purchase_request_add"),
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def purchase_request_add(request):
    warehouse = get_default_warehouse()
    if request.method == "POST":
        form = PurchaseRequestForm(request.POST)
        if form.is_valid():
            pr: PurchaseRequest = form.save(commit=False)
            pr.created_by = request.user
            pr.warehouse = warehouse
            pr.save()
            messages.success(request, "Готово! Заявку створено.")
            return redirect("purchase_request_detail", pk=pr.pk)
    else:
        form = PurchaseRequestForm(initial={"status": PurchaseRequest.Status.OPEN})

    return render(
        request,
        "materials/purchase_request_form.html",
        {
            "page_title": "Нова заявка",
            "page_title_center": True,
            "back_url": reverse("purchase_requests"),
            "form": form,
            "submit_label": "Створити",
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def purchase_request_detail(request, pk: int):
    pr = get_object_or_404(PurchaseRequest.objects.select_related("warehouse"), pk=pk)
    lines = list(
        pr.lines.select_related("material", "material_color").order_by("id")
    )
    po_lines = list(
        PurchaseOrderLine.objects.select_related("purchase_order", "purchase_order__supplier")
        .filter(request_line__request_id=pr.id)
        .order_by("id")
    )
    po_lines_by_request_line: dict[int, list[PurchaseOrderLine]] = {}
    for po_line in po_lines:
        if po_line.request_line_id is None:
            continue
        po_lines_by_request_line.setdefault(po_line.request_line_id, []).append(po_line)

    line_action_items: dict[int, list[dict]] = {}
    for line in lines:
        if line.status in {PurchaseRequestLine.Status.DONE, PurchaseRequestLine.Status.CANCELLED}:
            continue
        line_action_items[line.id] = [
            {
                "label": "Закрити",
                "url": reverse("purchase_request_line_set_status", kwargs={"line_pk": line.pk}),
                "method": "post",
                "icon": "check",
                "confirm": "Закрити позицію?",
                "extra_fields": {"status": PurchaseRequestLine.Status.DONE},
            },
            {"divider": True},
            {
                "label": "Скасувати",
                "url": reverse("purchase_request_line_set_status", kwargs={"line_pk": line.pk}),
                "method": "post",
                "icon": "trash",
                "danger": True,
                "confirm": "Скасувати позицію?",
                "extra_fields": {"status": PurchaseRequestLine.Status.CANCELLED},
            },
        ]

    actions = []
    if pr.status not in {PurchaseRequest.Status.DONE, PurchaseRequest.Status.CANCELLED}:
        actions.append(
            {
                "label": "В роботу",
                "url": reverse("purchase_request_set_status", kwargs={"pk": pr.pk}),
                "method": "post",
                "extra_fields": {"status": PurchaseRequest.Status.IN_PROGRESS},
            }
        )
        actions.append(
            {
                "label": "Закрити",
                "url": reverse("purchase_request_set_status", kwargs={"pk": pr.pk}),
                "method": "post",
                "icon": "check",
                "confirm": "Закрити заявку?",
                "extra_fields": {"status": PurchaseRequest.Status.DONE},
            }
        )
        actions.append({"divider": True})
        actions.append(
            {
                "label": "Скасувати",
                "url": reverse("purchase_request_set_status", kwargs={"pk": pr.pk}),
                "method": "post",
                "icon": "trash",
                "danger": True,
                "confirm": "Скасувати заявку?",
                "extra_fields": {"status": PurchaseRequest.Status.CANCELLED},
            }
        )
    tabs = [
        {"id": "orders", "label": "Замовлення", "url": reverse("purchases")},
        {"id": "requests", "label": "Заявки", "url": reverse("purchase_requests")},
    ]
    return render(
        request,
        "materials/purchase_request_detail.html",
        {
            "page_title": f"Заявка #{pr.id}",
            "tabs": tabs,
            "active_tab": "requests",
            "back_url": reverse("purchase_requests"),
            "back_label": "Заявки",
            "actions": actions,
            "purchase_request": pr,
            "lines": lines,
            "po_lines_by_request_line": po_lines_by_request_line,
            "line_action_items": line_action_items,
            "line_add_url": reverse("purchase_request_line_add", kwargs={"pk": pr.pk}),
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
@require_POST
def purchase_request_set_status(request, pk: int):
    pr = get_object_or_404(PurchaseRequest, pk=pk)
    new_status = (request.POST.get("status") or "").strip()
    valid_statuses = {value for value, _ in PurchaseRequest.Status.choices}
    if new_status not in valid_statuses:
        messages.error(request, "Упс. Невірний статус.")
        return redirect("purchase_request_detail", pk=pk)

    with transaction.atomic():
        pr.status = new_status
        pr.save(update_fields=["status", "updated_at"])

        # Manual close/cancel should also close the remaining lines,
        # otherwise a "closed" request still has active positions.
        if new_status in {PurchaseRequest.Status.DONE, PurchaseRequest.Status.CANCELLED}:
            now = timezone.now()
            pr.lines.exclude(
                status__in=[PurchaseRequestLine.Status.DONE, PurchaseRequestLine.Status.CANCELLED]
            ).update(status=new_status, updated_at=now)

    messages.success(request, "Готово! Статус оновлено.")
    return redirect("purchase_request_detail", pk=pk)


@login_required(login_url=reverse_lazy("auth_login"))
def purchase_request_line_add(request, pk: int):
    pr = get_object_or_404(PurchaseRequest, pk=pk)
    if request.method == "POST":
        form = PurchaseRequestLineForm(request.POST)
        if form.is_valid():
            line: PurchaseRequestLine = form.save(commit=False)
            line.request = pr
            line.save()
            messages.success(request, "Готово! Позицію додано.")
            return redirect("purchase_request_detail", pk=pr.pk)
    else:
        form = PurchaseRequestLineForm(initial={"status": PurchaseRequestLine.Status.OPEN})

    return render(
        request,
        "materials/purchase_request_line_form.html",
        {
            "page_title": f"Додати позицію · Заявка #{pr.id}",
            "page_title_center": True,
            "back_url": reverse("purchase_request_detail", kwargs={"pk": pr.pk}),
            "form": form,
            "submit_label": "Додати",
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def purchase_request_line_order(request, line_pk: int):
    line = get_object_or_404(
        PurchaseRequestLine.objects.select_related("request", "material", "material_color"),
        pk=line_pk,
    )
    supplier_id = None
    if request.GET.get("supplier") and str(request.GET.get("supplier")).isdigit():
        supplier_id = int(request.GET.get("supplier"))
    purchase_order_id = None
    if request.GET.get("purchase_order") and str(request.GET.get("purchase_order")).isdigit():
        purchase_order_id = int(request.GET.get("purchase_order"))

    if request.method == "POST":
        form = PurchaseRequestLineOrderForm(request.POST)
        if form.is_valid():
            supplier: Supplier = form.cleaned_data["supplier"]
            with transaction.atomic():
                purchase_order = form.cleaned_data.get("purchase_order")
                if purchase_order is None:
                    purchase_order = PurchaseOrder.objects.create(
                        supplier=supplier,
                        status=PurchaseOrder.Status.DRAFT,
                        created_by=request.user,
                    )
                po_line = PurchaseOrderLine.objects.create(
                    purchase_order=purchase_order,
                    request_line=line,
                    material=line.material,
                    material_color=line.material_color,
                    quantity=form.cleaned_data["quantity"],
                    unit=form.cleaned_data["unit"],
                    unit_price=form.cleaned_data.get("unit_price"),
                    notes=form.cleaned_data.get("notes") or "",
                )

                if line.status == PurchaseRequestLine.Status.OPEN:
                    line.status = PurchaseRequestLine.Status.ORDERED
                    line.save(update_fields=["status", "updated_at"])

            messages.success(request, "Готово! Додано в замовлення.")
            return redirect("purchase_detail", pk=po_line.purchase_order_id)
    else:
        initial = {
            "quantity": line.requested_quantity,
            "unit": line.unit,
        }
        if purchase_order_id is not None:
            initial["purchase_order"] = purchase_order_id
        form = PurchaseRequestLineOrderForm(initial=initial, supplier_id=supplier_id)

    return render(
        request,
        "materials/purchase_request_line_order_form.html",
        {
            "page_title": "Замовити",
            "page_title_center": True,
            "back_url": reverse("purchase_request_detail", kwargs={"pk": line.request_id}),
            "form": form,
            "line": line,
            "submit_label": "Додати",
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
@require_POST
def purchase_request_line_set_status(request, line_pk: int):
    line = get_object_or_404(PurchaseRequestLine.objects.select_related("request"), pk=line_pk)
    new_status = (request.POST.get("status") or "").strip()
    allowed_statuses = {PurchaseRequestLine.Status.DONE, PurchaseRequestLine.Status.CANCELLED}
    if new_status not in allowed_statuses:
        messages.error(request, "Упс. Невірний статус.")
        return redirect("purchase_request_detail", pk=line.request_id)

    with transaction.atomic():
        line.status = new_status
        line.save(update_fields=["status", "updated_at"])

        pr = line.request
        if pr.status not in {PurchaseRequest.Status.DONE, PurchaseRequest.Status.CANCELLED}:
            has_open_lines = pr.lines.exclude(
                status__in=[PurchaseRequestLine.Status.DONE, PurchaseRequestLine.Status.CANCELLED]
            ).exists()
            if not has_open_lines:
                has_done_lines = pr.lines.filter(status=PurchaseRequestLine.Status.DONE).exists()
                pr.status = PurchaseRequest.Status.DONE if has_done_lines else PurchaseRequest.Status.CANCELLED
                pr.save(update_fields=["status", "updated_at"])
            elif pr.status == PurchaseRequest.Status.OPEN:
                pr.status = PurchaseRequest.Status.IN_PROGRESS
                pr.save(update_fields=["status", "updated_at"])

    messages.success(request, "Готово! Статус оновлено.")
    return redirect("purchase_request_detail", pk=line.request_id)
