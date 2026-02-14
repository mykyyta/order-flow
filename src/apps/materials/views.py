from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView, UpdateView
from django.db.models.functions import Lower

from apps.materials.forms import (
    MaterialColorForm,
    MaterialForm,
    PurchaseOrderFilterForm,
    PurchaseOrderForm,
    PurchaseOrderLineForm,
    PurchaseOrderLineReceiveForm,
    PurchaseRequestForm,
    PurchaseRequestLineForm,
    PurchaseRequestLineOrderForm,
)
from apps.materials.models import (
    Material,
    MaterialColor,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseRequest,
    PurchaseRequestLine,
    Supplier,
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
    """Placeholder view for suppliers list."""
    return render(
        request,
        "materials/suppliers.html",
        {"page_title": "Постачальники"},
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
            "tabs": tabs,
            "active_tab": "orders",
            "page_obj": page_obj,
            "filter_form": filter_form,
            "search_query": search_query,
            "status": status,
            "purchase_add_url": reverse("purchase_add"),
            "clear_url": reverse("purchases"),
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def purchase_add(request):
    if request.method == "POST":
        form = PurchaseOrderForm(request.POST)
        if form.is_valid():
            purchase_order: PurchaseOrder = form.save(commit=False)
            purchase_order.created_by = request.user
            purchase_order.save()
            messages.success(request, "Готово! Замовлення створено.")
            return redirect("purchase_detail", pk=purchase_order.pk)
    else:
        form = PurchaseOrderForm(initial={"status": PurchaseOrder.Status.DRAFT})

    return render(
        request,
        "materials/purchase_form.html",
        {
            "page_title": "Нове замовлення",
            "page_title_center": True,
            "back_url": reverse("purchases"),
            "form": form,
            "submit_label": "Створити",
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def purchase_detail(request, pk: int):
    purchase_order = get_object_or_404(
        PurchaseOrder.objects.select_related("supplier"),
        pk=pk,
    )
    lines = list(
        purchase_order.lines.select_related("material", "material_color").order_by("id")
    )

    tabs = [
        {"id": "orders", "label": "Замовлення", "url": reverse("purchases")},
        {"id": "requests", "label": "Заявки", "url": reverse("purchase_requests")},
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
    if request.method == "POST":
        form = PurchaseOrderLineForm(request.POST)
        if form.is_valid():
            line: PurchaseOrderLine = form.save(commit=False)
            line.purchase_order = purchase_order
            line.save()
            messages.success(request, "Готово! Позицію додано.")
            return redirect("purchase_detail", pk=purchase_order.pk)
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
            "purchase_request": pr,
            "lines": lines,
            "line_add_url": reverse("purchase_request_line_add", kwargs={"pk": pr.pk}),
        },
    )


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
