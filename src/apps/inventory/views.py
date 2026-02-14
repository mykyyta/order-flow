from __future__ import annotations

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models.functions import Lower
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_http_methods

from apps.catalog.models import Product, Variant
from apps.inventory.forms import (
    MaterialAdjustmentSelectForm,
    MaterialStockAdjustmentForm,
    ProductAdjustmentSelectForm,
    ProductStockAdjustmentForm,
)
from apps.inventory.models import ProductStock
from apps.inventory.models import ProductStockMovement
from apps.inventory.services import add_to_stock, remove_from_stock
from apps.materials.models import Material, MaterialColor, MaterialStock, MaterialStockMovement
from apps.materials.services import add_material_stock, remove_material_stock
from apps.warehouses.services import get_default_warehouse


@login_required(login_url=reverse_lazy("auth_login"))
def inventory_products(request):
    warehouse = get_default_warehouse()
    search_query = (request.GET.get("q") or "").strip()
    sort = (request.GET.get("sort") or "name").strip()
    if sort not in {"name", "qty_desc", "qty_asc"}:
        sort = "name"
    stocks = (
        ProductStock.objects.select_related(
            "variant",
            "variant__product",
            "variant__primary_material_color",
            "variant__secondary_material_color",
        )
        .filter(warehouse=warehouse)
    )
    if sort == "qty_desc":
        stocks = stocks.order_by("-quantity", "variant__product__name", "variant_id")
    elif sort == "qty_asc":
        stocks = stocks.order_by("quantity", "variant__product__name", "variant_id")
    else:
        stocks = stocks.order_by("variant__product__name", "variant_id")
    if search_query:
        stocks = stocks.filter(
            Q(variant__product__name__icontains=search_query)
            | Q(variant__primary_material_color__name__icontains=search_query)
            | Q(variant__secondary_material_color__name__icontains=search_query)
        )

    paginator = Paginator(stocks, 50)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "inventory/products.html",
        {
            "page_title": "Готова продукція",
            "show_page_header": False,
            "warehouse": warehouse,
            "page_obj": page_obj,
            "search_query": search_query,
            "sort": sort,
            "add_url": reverse("inventory_products_add"),
            "remove_url": reverse("inventory_products_remove"),
            "writeoff_url": reverse("inventory_products_writeoff"),
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def inventory_product_stock_detail(request, pk: int):
    warehouse = get_default_warehouse()
    record = (
        ProductStock.objects.select_related(
            "variant",
            "variant__product",
            "variant__primary_material_color",
            "variant__secondary_material_color",
        )
        .filter(warehouse=warehouse, id=pk)
        .first()
    )
    if record is None:
        return redirect("inventory_products")

    paginator = Paginator(record.movements.select_related("created_by", "related_production_order"), 50)
    movements_page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "inventory/product_stock_detail.html",
        {
            "page_title": "Деталі залишку",
            "page_title_center": True,
            "back_url": reverse("inventory_products"),
            "record": record,
            "movements_page_obj": movements_page_obj,
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def inventory_wip(request):
    """Placeholder view for WIP (work in progress) inventory."""
    return render(
        request,
        "inventory/wip.html",
        {"page_title": "WIP"},
    )


@login_required(login_url=reverse_lazy("auth_login"))
def inventory_materials(request):
    warehouse = get_default_warehouse()
    search_query = (request.GET.get("q") or "").strip()
    sort = (request.GET.get("sort") or "name").strip()
    if sort not in {"name", "qty_desc", "qty_asc"}:
        sort = "name"
    stocks = (
        MaterialStock.objects.select_related("material", "material_color")
        .filter(warehouse=warehouse)
    )
    if sort == "qty_desc":
        stocks = stocks.order_by("-quantity", "material__name", "material_color__name", "unit")
    elif sort == "qty_asc":
        stocks = stocks.order_by("quantity", "material__name", "material_color__name", "unit")
    else:
        stocks = stocks.order_by("material__name", "material_color__name", "unit")
    if search_query:
        stocks = stocks.filter(
            Q(material__name__icontains=search_query) | Q(material_color__name__icontains=search_query)
        )
    paginator = Paginator(stocks, 50)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "inventory/materials.html",
        {
            "page_title": "Матеріали",
            "show_page_header": False,
            "warehouse": warehouse,
            "page_obj": page_obj,
            "search_query": search_query,
            "sort": sort,
            "add_url": reverse("inventory_materials_add"),
            "remove_url": reverse("inventory_materials_remove"),
            "writeoff_url": reverse("inventory_materials_writeoff"),
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
def inventory_material_stock_detail(request, pk: int):
    warehouse = get_default_warehouse()
    record = (
        MaterialStock.objects.select_related("material", "material_color")
        .filter(warehouse=warehouse, id=pk)
        .first()
    )
    if record is None:
        return redirect("inventory_materials")

    paginator = Paginator(
        record.movements.select_related(
            "created_by",
            "related_purchase_order_line",
            "related_receipt_line",
        ),
        50,
    )
    movements_page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "inventory/material_stock_detail.html",
        {
            "page_title": "Деталі залишку",
            "page_title_center": True,
            "back_url": reverse("inventory_materials"),
            "record": record,
            "movements_page_obj": movements_page_obj,
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
@require_http_methods(["GET", "POST"])
def inventory_materials_writeoff(request):
    warehouse = get_default_warehouse()
    stock_id = (request.GET.get("stock_id") or "").strip()
    initial: dict[str, object] = {}
    lock = False
    locked_stock_record = None

    if stock_id.isdigit():
        record = (
            MaterialStock.objects.select_related("material", "material_color")
            .filter(warehouse=warehouse, id=int(stock_id))
            .first()
        )
        if record:
            lock = True
            locked_stock_record = record
            initial = {
                "material": record.material_id,
                "material_color": record.material_color_id,
            }

    if request.method == "GET" and not initial and not (request.GET.get("material") or "").strip():
        select_form = MaterialAdjustmentSelectForm(request.GET or None)
        return render(
            request,
            "inventory/material_adjustment_select.html",
            {
                "page_title": "Списати матеріал зі складу",
                "page_title_center": True,
                "back_url": reverse("inventory_materials"),
                "form": select_form,
            },
        )

    if not initial:
        raw_material = (request.GET.get("material") or "").strip()
        raw_color = (request.GET.get("material_color") or "").strip()
        if raw_material.isdigit():
            initial["material"] = int(raw_material)
        if raw_color.isdigit():
            initial["material_color"] = int(raw_color)

    if request.method == "POST":
        form = MaterialStockAdjustmentForm(request.POST)
        _narrow_material_form(form=form, warehouse=warehouse, is_remove=True)
        if form.is_valid():
            try:
                unit = None
                if locked_stock_record is not None:
                    unit = locked_stock_record.unit
                else:
                    unit = form.cleaned_data["material"].stock_unit
                if not unit:
                    messages.error(
                        request,
                        "Для матеріалу не задана одиниця складу. Вкажи її в картці матеріалу.",
                    )
                    return redirect("inventory_materials_writeoff")

                remove_material_stock(
                    warehouse_id=warehouse.id,
                    material=form.cleaned_data["material"],
                    material_color=form.cleaned_data.get("material_color"),
                    quantity=Decimal(str(form.cleaned_data["quantity"])),
                    unit=unit,
                    reason=MaterialStockMovement.Reason.WRITE_OFF,
                    created_by=request.user,
                    notes="",
                )
            except ValueError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, "Готово! Списано зі складу.")
                return redirect("inventory_materials")
    else:
        form = MaterialStockAdjustmentForm(initial=initial)
        _narrow_material_form(form=form, warehouse=warehouse, is_remove=True)

    locked_material = None
    if not lock:
        raw_material = None
        if form.is_bound:
            raw_material = form.data.get(form.add_prefix("material"))
        else:
            raw_material = form.initial.get("material")
        if raw_material and str(raw_material).isdigit():
            locked_material = Material.objects.filter(id=int(raw_material)).first()
    lock_material = bool(locked_material is not None and locked_stock_record is None)

    return render(
        request,
        "inventory/material_adjustment_form.html",
        {
            "page_title": "Списати матеріал зі складу",
            "page_title_center": True,
            "back_url": reverse("inventory_materials"),
            "form": form,
            "submit_label": "Списати",
            "lock": lock,
            "locked_stock_record": locked_stock_record,
            "lock_material": lock_material,
            "locked_material": locked_material,
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
@require_http_methods(["GET", "POST"])
def inventory_products_writeoff(request):
    warehouse = get_default_warehouse()
    variant_id = (request.GET.get("variant_id") or "").strip()
    initial: dict[str, object] = {}
    lock = False
    variant = None
    if variant_id.isdigit():
        variant = Variant.objects.select_related(
            "product", "primary_material_color", "secondary_material_color"
        ).filter(id=int(variant_id)).first()
        if variant:
            lock = True
            initial = {
                "product": variant.product_id,
                "primary_material_color": variant.primary_material_color_id,
                "secondary_material_color": variant.secondary_material_color_id,
            }

    if request.method == "GET" and not initial and not (request.GET.get("product") or "").strip():
        select_form = ProductAdjustmentSelectForm(request.GET or None)
        return render(
            request,
            "inventory/product_adjustment_select.html",
            {
                "page_title": "Списати готову продукцію зі складу",
                "page_title_center": True,
                "back_url": reverse("inventory_products"),
                "form": select_form,
            },
        )

    if not initial:
        raw_product = (request.GET.get("product") or "").strip()
        raw_primary = (request.GET.get("primary_material_color") or "").strip()
        raw_secondary = (request.GET.get("secondary_material_color") or "").strip()
        if raw_product.isdigit():
            initial["product"] = int(raw_product)
        if raw_primary.isdigit():
            initial["primary_material_color"] = int(raw_primary)
        if raw_secondary.isdigit():
            initial["secondary_material_color"] = int(raw_secondary)

    if request.method == "POST":
        form = ProductStockAdjustmentForm(request.POST)
        if form.is_valid():
            try:
                posted_variant_id = (request.POST.get("variant_id") or "").strip()
                remove_from_stock_kwargs: dict[str, object] = {
                    "warehouse_id": warehouse.id,
                    "quantity": int(form.cleaned_data["quantity"]),
                    "reason": ProductStockMovement.Reason.WRITE_OFF,
                    "user": request.user,
                    "notes": form.cleaned_data.get("notes") or "",
                }
                if posted_variant_id.isdigit():
                    posted_variant = Variant.objects.select_related("product").filter(
                        id=int(posted_variant_id)
                    ).first()
                    if posted_variant is None:
                        messages.error(request, "Упс. Невірний варіант.")
                        return redirect("inventory_products_writeoff")
                    if posted_variant.product.kind == Product.Kind.BUNDLE:
                        messages.error(request, "Комплекти не обліковуються на складі.")
                        return redirect("inventory_products_writeoff")
                    if posted_variant.product_id != form.cleaned_data["product"].id:
                        messages.error(request, "Упс. Варіант не відповідає вибраному виробу.")
                        return redirect("inventory_products_writeoff")

                    remove_from_stock_kwargs["variant_id"] = int(posted_variant_id)
                else:
                    remove_from_stock_kwargs["product_id"] = form.cleaned_data["product"].id
                    remove_from_stock_kwargs["primary_material_color_id"] = (
                        form.cleaned_data["primary_material_color"].id
                        if form.cleaned_data.get("primary_material_color")
                        else None
                    )
                    remove_from_stock_kwargs["secondary_material_color_id"] = (
                        form.cleaned_data["secondary_material_color"].id
                        if form.cleaned_data.get("secondary_material_color")
                        else None
                    )

                remove_from_stock(**remove_from_stock_kwargs)
            except ValueError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, "Готово! Списано зі складу.")
                return redirect("inventory_products")
    else:
        form = ProductStockAdjustmentForm(initial=initial)

    locked_product = None
    if not lock:
        raw_product = None
        if form.is_bound:
            raw_product = form.data.get(form.add_prefix("product"))
        else:
            raw_product = form.initial.get("product")
        if raw_product and str(raw_product).isdigit():
            locked_product = Product.objects.filter(id=int(raw_product)).first()
    lock_product = bool(locked_product is not None and variant is None)

    raw_product = None
    if form.is_bound:
        raw_product = form.data.get(form.add_prefix("product"))
    else:
        raw_product = form.initial.get("product")
    selected_product = (
        Product.objects.filter(id=int(raw_product)).first()
        if raw_product and str(raw_product).isdigit()
        else None
    )
    show_primary_color = bool(
        selected_product
        and selected_product.primary_material_id
        and MaterialColor.objects.filter(
            material_id=selected_product.primary_material_id,
            archived_at__isnull=True,
        ).exists()
    )
    show_secondary_color = bool(
        selected_product
        and selected_product.secondary_material_id
        and MaterialColor.objects.filter(
            material_id=selected_product.secondary_material_id,
            archived_at__isnull=True,
        ).exists()
    )

    return render(
        request,
        "inventory/product_adjustment_form.html",
        {
            "page_title": "Списати готову продукцію зі складу",
            "page_title_center": True,
            "back_url": reverse("inventory_products"),
            "form": form,
            "submit_label": "Списати",
            "lock": lock,
            "variant_id": variant_id if variant_id.isdigit() else "",
            "locked_variant": variant if lock else None,
            "show_primary_color": show_primary_color,
            "show_secondary_color": show_secondary_color,
            "lock_product": lock_product,
            "locked_product": locked_product,
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
@require_http_methods(["GET", "POST"])
def inventory_materials_add(request):
    warehouse = get_default_warehouse()
    stock_id = (request.GET.get("stock_id") or "").strip()
    initial: dict[str, object] = {}
    lock = False
    locked_stock_record = None

    if stock_id.isdigit():
        record = (
            MaterialStock.objects.select_related("material", "material_color")
            .filter(warehouse=warehouse, id=int(stock_id))
            .first()
        )
        if record:
            lock = True
            locked_stock_record = record
            initial = {
                "material": record.material_id,
                "material_color": record.material_color_id,
            }

    if request.method == "GET" and not initial and not (request.GET.get("material") or "").strip():
        select_form = MaterialAdjustmentSelectForm(request.GET or None)
        return render(
            request,
            "inventory/material_adjustment_select.html",
            {
                "page_title": "Додати матеріал на склад",
                "page_title_center": True,
                "back_url": reverse("inventory_materials"),
                "form": select_form,
            },
        )

    if not initial:
        raw_material = (request.GET.get("material") or "").strip()
        raw_color = (request.GET.get("material_color") or "").strip()
        if raw_material.isdigit():
            initial["material"] = int(raw_material)
        if raw_color.isdigit():
            initial["material_color"] = int(raw_color)

    if request.method == "POST":
        form = MaterialStockAdjustmentForm(request.POST)
        _narrow_material_form(form=form, warehouse=warehouse, is_remove=False)
        if form.is_valid():
            unit = None
            if locked_stock_record is not None:
                unit = locked_stock_record.unit
            else:
                unit = form.cleaned_data["material"].stock_unit
            if not unit:
                messages.error(request, "Для матеріалу не задана одиниця складу. Вкажи її в картці матеріалу.")
                return redirect("inventory_materials_add")

            add_material_stock(
                warehouse_id=warehouse.id,
                material=form.cleaned_data["material"],
                material_color=form.cleaned_data.get("material_color"),
                quantity=Decimal(str(form.cleaned_data["quantity"])),
                unit=unit,
                reason=MaterialStockMovement.Reason.ADJUSTMENT_IN,
                created_by=request.user,
                notes="",
            )
            messages.success(request, "Готово! Додано на склад.")
            return redirect("inventory_materials")
    else:
        form = MaterialStockAdjustmentForm(initial=initial)
        _narrow_material_form(form=form, warehouse=warehouse, is_remove=False)

    locked_material = None
    if not lock:
        raw_material = None
        if form.is_bound:
            raw_material = form.data.get(form.add_prefix("material"))
        else:
            raw_material = form.initial.get("material")
        if raw_material and str(raw_material).isdigit():
            locked_material = Material.objects.filter(id=int(raw_material)).first()
    lock_material = bool(locked_material is not None and locked_stock_record is None)

    return render(
        request,
        "inventory/material_adjustment_form.html",
        {
            "page_title": "Додати матеріал на склад",
            "page_title_center": True,
            "back_url": reverse("inventory_materials"),
            "form": form,
            "submit_label": "Додати",
            "lock": lock,
            "locked_stock_record": locked_stock_record,
            "lock_material": lock_material,
            "locked_material": locked_material,
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
@require_http_methods(["GET", "POST"])
def inventory_materials_remove(request):
    warehouse = get_default_warehouse()
    stock_id = (request.GET.get("stock_id") or "").strip()
    initial: dict[str, object] = {}
    lock = False
    locked_stock_record = None

    if stock_id.isdigit():
        record = (
            MaterialStock.objects.select_related("material", "material_color")
            .filter(warehouse=warehouse, id=int(stock_id))
            .first()
        )
        if record:
            lock = True
            locked_stock_record = record
            initial = {
                "material": record.material_id,
                "material_color": record.material_color_id,
            }

    if request.method == "GET" and not initial and not (request.GET.get("material") or "").strip():
        select_form = MaterialAdjustmentSelectForm(request.GET or None)
        return render(
            request,
            "inventory/material_adjustment_select.html",
            {
                "page_title": "Зняти матеріал зі складу",
                "page_title_center": True,
                "back_url": reverse("inventory_materials"),
                "form": select_form,
            },
        )

    if not initial:
        raw_material = (request.GET.get("material") or "").strip()
        raw_color = (request.GET.get("material_color") or "").strip()
        if raw_material.isdigit():
            initial["material"] = int(raw_material)
        if raw_color.isdigit():
            initial["material_color"] = int(raw_color)

    if request.method == "POST":
        form = MaterialStockAdjustmentForm(request.POST)
        _narrow_material_form(form=form, warehouse=warehouse, is_remove=True)
        if form.is_valid():
            try:
                unit = None
                if locked_stock_record is not None:
                    unit = locked_stock_record.unit
                else:
                    unit = form.cleaned_data["material"].stock_unit
                if not unit:
                    messages.error(
                        request,
                        "Для матеріалу не задана одиниця складу. Вкажи її в картці матеріалу.",
                    )
                    return redirect("inventory_materials_remove")

                remove_material_stock(
                    warehouse_id=warehouse.id,
                    material=form.cleaned_data["material"],
                    material_color=form.cleaned_data.get("material_color"),
                    quantity=Decimal(str(form.cleaned_data["quantity"])),
                    unit=unit,
                    reason=MaterialStockMovement.Reason.ADJUSTMENT_OUT,
                    created_by=request.user,
                    notes="",
                )
            except ValueError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, "Готово! Знято зі складу.")
                return redirect("inventory_materials")
    else:
        form = MaterialStockAdjustmentForm(initial=initial)
        _narrow_material_form(form=form, warehouse=warehouse, is_remove=True)

    locked_material = None
    if not lock:
        raw_material = None
        if form.is_bound:
            raw_material = form.data.get(form.add_prefix("material"))
        else:
            raw_material = form.initial.get("material")
        if raw_material and str(raw_material).isdigit():
            locked_material = Material.objects.filter(id=int(raw_material)).first()
    lock_material = bool(locked_material is not None and locked_stock_record is None)

    return render(
        request,
        "inventory/material_adjustment_form.html",
        {
            "page_title": "Зняти матеріал зі складу",
            "page_title_center": True,
            "back_url": reverse("inventory_materials"),
            "form": form,
            "submit_label": "Зняти",
            "lock": lock,
            "locked_stock_record": locked_stock_record,
            "lock_material": lock_material,
            "locked_material": locked_material,
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
@require_http_methods(["GET", "POST"])
def inventory_products_add(request):
    warehouse = get_default_warehouse()
    variant_id = (request.GET.get("variant_id") or "").strip()
    initial: dict[str, object] = {}
    lock = False
    variant = None
    if variant_id.isdigit():
        variant = Variant.objects.select_related(
            "product", "primary_material_color", "secondary_material_color"
        ).filter(id=int(variant_id)).first()
        if variant:
            lock = True
            initial = {
                "product": variant.product_id,
                "primary_material_color": variant.primary_material_color_id,
                "secondary_material_color": variant.secondary_material_color_id,
            }

    if request.method == "GET" and not initial and not (request.GET.get("product") or "").strip():
        select_form = ProductAdjustmentSelectForm(request.GET or None)
        return render(
            request,
            "inventory/product_adjustment_select.html",
            {
                "page_title": "Додати готову продукцію на склад",
                "page_title_center": True,
                "back_url": reverse("inventory_products"),
                "form": select_form,
            },
        )

    if not initial:
        raw_product = (request.GET.get("product") or "").strip()
        raw_primary = (request.GET.get("primary_material_color") or "").strip()
        raw_secondary = (request.GET.get("secondary_material_color") or "").strip()
        if raw_product.isdigit():
            initial["product"] = int(raw_product)
        if raw_primary.isdigit():
            initial["primary_material_color"] = int(raw_primary)
        if raw_secondary.isdigit():
            initial["secondary_material_color"] = int(raw_secondary)

    if request.method == "POST":
        form = ProductStockAdjustmentForm(request.POST)
        if form.is_valid():
            posted_variant_id = (request.POST.get("variant_id") or "").strip()
            add_to_stock_kwargs: dict[str, object] = {
                "warehouse_id": warehouse.id,
                "quantity": int(form.cleaned_data["quantity"]),
                "reason": ProductStockMovement.Reason.ADJUSTMENT_IN,
                "user": request.user,
                "notes": form.cleaned_data.get("notes") or "",
            }
            if posted_variant_id.isdigit():
                posted_variant = Variant.objects.select_related("product").filter(
                    id=int(posted_variant_id)
                ).first()
                if posted_variant is None:
                    messages.error(request, "Упс. Невірний варіант.")
                    return redirect("inventory_products_add")
                if posted_variant.product.kind == Product.Kind.BUNDLE:
                    messages.error(request, "Комплекти не обліковуються на складі.")
                    return redirect("inventory_products_add")
                if posted_variant.product_id != form.cleaned_data["product"].id:
                    messages.error(request, "Упс. Варіант не відповідає вибраному виробу.")
                    return redirect("inventory_products_add")

                add_to_stock_kwargs["variant_id"] = int(posted_variant_id)
            else:
                add_to_stock_kwargs["product_id"] = form.cleaned_data["product"].id
                add_to_stock_kwargs["primary_material_color_id"] = (
                    form.cleaned_data["primary_material_color"].id
                    if form.cleaned_data.get("primary_material_color")
                    else None
                )
                add_to_stock_kwargs["secondary_material_color_id"] = (
                    form.cleaned_data["secondary_material_color"].id
                    if form.cleaned_data.get("secondary_material_color")
                    else None
                )

            add_to_stock(**add_to_stock_kwargs)
            messages.success(request, "Готово! Додано на склад.")
            return redirect("inventory_products")
    else:
        form = ProductStockAdjustmentForm(initial=initial)

    locked_product = None
    if not lock:
        raw_product = None
        if form.is_bound:
            raw_product = form.data.get(form.add_prefix("product"))
        else:
            raw_product = form.initial.get("product")
        if raw_product and str(raw_product).isdigit():
            locked_product = Product.objects.filter(id=int(raw_product)).first()
    lock_product = bool(locked_product is not None and variant is None)

    raw_product = None
    if form.is_bound:
        raw_product = form.data.get(form.add_prefix("product"))
    else:
        raw_product = form.initial.get("product")
    selected_product = (
        Product.objects.filter(id=int(raw_product)).first()
        if raw_product and str(raw_product).isdigit()
        else None
    )
    show_primary_color = bool(
        selected_product
        and selected_product.primary_material_id
        and MaterialColor.objects.filter(
            material_id=selected_product.primary_material_id,
            archived_at__isnull=True,
        ).exists()
    )
    show_secondary_color = bool(
        selected_product
        and selected_product.secondary_material_id
        and MaterialColor.objects.filter(
            material_id=selected_product.secondary_material_id,
            archived_at__isnull=True,
        ).exists()
    )

    return render(
        request,
        "inventory/product_adjustment_form.html",
        {
            "page_title": "Додати готову продукцію на склад",
            "page_title_center": True,
            "back_url": reverse("inventory_products"),
            "form": form,
            "submit_label": "Додати",
            "lock": lock,
            "variant_id": variant_id if variant_id.isdigit() else "",
            "locked_variant": variant if lock else None,
            "show_primary_color": show_primary_color,
            "show_secondary_color": show_secondary_color,
            "lock_product": lock_product,
            "locked_product": locked_product,
        },
    )


@login_required(login_url=reverse_lazy("auth_login"))
@require_http_methods(["GET", "POST"])
def inventory_products_remove(request):
    warehouse = get_default_warehouse()
    variant_id = (request.GET.get("variant_id") or "").strip()
    initial: dict[str, object] = {}
    lock = False
    variant = None
    if variant_id.isdigit():
        variant = Variant.objects.select_related(
            "product", "primary_material_color", "secondary_material_color"
        ).filter(id=int(variant_id)).first()
        if variant:
            lock = True
            initial = {
                "product": variant.product_id,
                "primary_material_color": variant.primary_material_color_id,
                "secondary_material_color": variant.secondary_material_color_id,
            }

    if request.method == "GET" and not initial and not (request.GET.get("product") or "").strip():
        select_form = ProductAdjustmentSelectForm(request.GET or None)
        return render(
            request,
            "inventory/product_adjustment_select.html",
            {
                "page_title": "Зняти готову продукцію зі складу",
                "page_title_center": True,
                "back_url": reverse("inventory_products"),
                "form": select_form,
            },
        )

    if not initial:
        raw_product = (request.GET.get("product") or "").strip()
        raw_primary = (request.GET.get("primary_material_color") or "").strip()
        raw_secondary = (request.GET.get("secondary_material_color") or "").strip()
        if raw_product.isdigit():
            initial["product"] = int(raw_product)
        if raw_primary.isdigit():
            initial["primary_material_color"] = int(raw_primary)
        if raw_secondary.isdigit():
            initial["secondary_material_color"] = int(raw_secondary)

    if request.method == "POST":
        form = ProductStockAdjustmentForm(request.POST)
        if form.is_valid():
            try:
                posted_variant_id = (request.POST.get("variant_id") or "").strip()
                remove_from_stock_kwargs: dict[str, object] = {
                    "warehouse_id": warehouse.id,
                    "quantity": int(form.cleaned_data["quantity"]),
                    "reason": ProductStockMovement.Reason.ADJUSTMENT_OUT,
                    "user": request.user,
                    "notes": form.cleaned_data.get("notes") or "",
                }
                if posted_variant_id.isdigit():
                    posted_variant = Variant.objects.select_related("product").filter(
                        id=int(posted_variant_id)
                    ).first()
                    if posted_variant is None:
                        messages.error(request, "Упс. Невірний варіант.")
                        return redirect("inventory_products_remove")
                    if posted_variant.product.kind == Product.Kind.BUNDLE:
                        messages.error(request, "Комплекти не обліковуються на складі.")
                        return redirect("inventory_products_remove")
                    if posted_variant.product_id != form.cleaned_data["product"].id:
                        messages.error(request, "Упс. Варіант не відповідає вибраному виробу.")
                        return redirect("inventory_products_remove")

                    remove_from_stock_kwargs["variant_id"] = int(posted_variant_id)
                else:
                    remove_from_stock_kwargs["product_id"] = form.cleaned_data["product"].id
                    remove_from_stock_kwargs["primary_material_color_id"] = (
                        form.cleaned_data["primary_material_color"].id
                        if form.cleaned_data.get("primary_material_color")
                        else None
                    )
                    remove_from_stock_kwargs["secondary_material_color_id"] = (
                        form.cleaned_data["secondary_material_color"].id
                        if form.cleaned_data.get("secondary_material_color")
                        else None
                    )

                remove_from_stock(**remove_from_stock_kwargs)
            except ValueError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, "Готово! Знято зі складу.")
                return redirect("inventory_products")
    else:
        form = ProductStockAdjustmentForm(initial=initial)

    locked_product = None
    if not lock:
        raw_product = None
        if form.is_bound:
            raw_product = form.data.get(form.add_prefix("product"))
        else:
            raw_product = form.initial.get("product")
        if raw_product and str(raw_product).isdigit():
            locked_product = Product.objects.filter(id=int(raw_product)).first()
    lock_product = bool(locked_product is not None and variant is None)

    raw_product = None
    if form.is_bound:
        raw_product = form.data.get(form.add_prefix("product"))
    else:
        raw_product = form.initial.get("product")
    selected_product = (
        Product.objects.filter(id=int(raw_product)).first()
        if raw_product and str(raw_product).isdigit()
        else None
    )
    show_primary_color = bool(
        selected_product
        and selected_product.primary_material_id
        and MaterialColor.objects.filter(
            material_id=selected_product.primary_material_id,
            archived_at__isnull=True,
        ).exists()
    )
    show_secondary_color = bool(
        selected_product
        and selected_product.secondary_material_id
        and MaterialColor.objects.filter(
            material_id=selected_product.secondary_material_id,
            archived_at__isnull=True,
        ).exists()
    )

    return render(
        request,
        "inventory/product_adjustment_form.html",
        {
            "page_title": "Зняти готову продукцію зі складу",
            "page_title_center": True,
            "back_url": reverse("inventory_products"),
            "form": form,
            "submit_label": "Зняти",
            "lock": lock,
            "variant_id": variant_id if variant_id.isdigit() else "",
            "locked_variant": variant if lock else None,
            "show_primary_color": show_primary_color,
            "show_secondary_color": show_secondary_color,
            "lock_product": lock_product,
            "locked_product": locked_product,
        },
    )


def _narrow_material_form(
    *,
    form: MaterialStockAdjustmentForm,
    warehouse,
    is_remove: bool,
) -> None:
    # Narrow color list and unit choices for selected material/material_color.
    raw_material = None
    if form.is_bound:
        raw_material = form.data.get(form.add_prefix("material"))
    else:
        raw_material = form.initial.get("material")
    material_id = int(raw_material) if raw_material and str(raw_material).isdigit() else None
    if material_id is not None:
        color_qs = MaterialColor.objects.filter(
            material_id=material_id,
            archived_at__isnull=True,
        )
        if is_remove:
            # Only show colors that exist in stock with positive quantity.
            color_ids = (
                MaterialStock.objects.filter(
                    warehouse=warehouse,
                    material_id=material_id,
                    quantity__gt=0,
                )
                .exclude(material_color_id__isnull=True)
                .values_list("material_color_id", flat=True)
                .distinct()
            )
            color_qs = color_qs.filter(id__in=list(color_ids))

        form.fields["material_color"].queryset = color_qs.order_by(Lower("name"), "name")
    else:
        form.fields["material_color"].queryset = MaterialColor.objects.none()
