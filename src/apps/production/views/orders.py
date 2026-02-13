from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.timezone import localtime
from django.views.decorators.http import require_POST

from apps.catalog.models import BundleComponent, Product
from apps.production.exceptions import InvalidStatusTransition
from apps.production.forms import OrderForm, OrderStatusUpdateForm
from apps.production.domain.order_statuses import (
    ACTIVE_LIST_ORDER,
    status_choices,
    status_choices_for_active_page,
    status_label_map,
)
from apps.production.domain.order_statuses import (
    transition_map as build_transition_map,
)
from apps.production.domain.status import STATUS_DONE
from apps.production.models import ProductionOrder, ProductionOrderStatusHistory
from apps.production.services import change_production_order_status, create_production_order

STATUS_LABELS = status_label_map(include_legacy=True)
CURRENT_STATUS_OPTIONS = status_choices(include_legacy=False, include_terminal=False)
TRANSITION_MAP = {
    status: sorted(transitions)
    for status, transitions in build_transition_map(include_legacy_current=True).items()
}


def _sync_sales_line_after_order_done(sales_order_line) -> None:
    from apps.sales.services import sync_sales_order_line_production

    sync_sales_order_line_production(sales_order_line)


def _filtered_current_orders_queryset(*, filter_value: str):
    status_rank = Case(
        *[When(status=code, then=Value(i)) for i, code in enumerate(ACTIVE_LIST_ORDER)],
        default=Value(999),
        output_field=IntegerField(),
    )
    queryset = (
        ProductionOrder.objects.select_related(
            "product",
            "variant",
            "variant__primary_material_color",
            "variant__secondary_material_color",
        )
        .exclude(status=STATUS_DONE)
        .annotate(_status_rank=status_rank)
        .order_by("_status_rank", "-created_at", "-id")
    )

    status_values = {value for value, _ in CURRENT_STATUS_OPTIONS}
    if filter_value.startswith("tag:"):
        tag = filter_value[4:]
        if tag == "is_etsy":
            queryset = queryset.filter(is_etsy=True)
        elif tag == "is_embroidery":
            queryset = queryset.filter(is_embroidery=True)
        elif tag == "is_urgent":
            queryset = queryset.filter(is_urgent=True)
    elif filter_value in status_values:
        queryset = queryset.filter(status=filter_value)

    return queryset, filter_value


COMBINED_FILTER_OPTIONS = (
    [
        ("", "Усі"),
    ]
    + list(CURRENT_STATUS_OPTIONS)
    + [
        ("tag:is_etsy", "Etsy"),
        ("tag:is_embroidery", "Вишивка"),
        ("tag:is_urgent", "Терміново"),
    ]
)


@login_required
def orders_active(request):
    filter_value = (request.GET.get("filter") or "").strip()
    orders_queryset, filter_value = _filtered_current_orders_queryset(
        filter_value=filter_value,
    )

    form = OrderStatusUpdateForm()
    form.fields["orders"].queryset = orders_queryset
    form.fields["new_status"].choices = [("", "Новий статус")] + list(
        status_choices_for_active_page()
    )
    paginator = Paginator(orders_queryset, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    query_params = request.GET.copy()
    query_params.pop("page", None)
    query_string = query_params.urlencode()

    return render(
        request,
        "orders/active.html",
        {
            "page_title": "У роботі",
            "form": form,
            "orders": page_obj.object_list,
            "page_obj": page_obj,
            "filter_value": filter_value,
            "filter_options": COMBINED_FILTER_OPTIONS,
            "query_string": query_string,
            "transition_map": TRANSITION_MAP,
        },
    )


@login_required
@require_POST
def orders_bulk_status(request):
    filter_value = (request.GET.get("filter") or "").strip()
    orders_queryset, filter_value = _filtered_current_orders_queryset(
        filter_value=filter_value,
    )

    form = OrderStatusUpdateForm(request.POST)
    form.fields["orders"].queryset = orders_queryset
    if not form.is_valid():
        messages.error(request, "Упс. Щось пішло не так — спробуй ще раз.")
        url = reverse("orders_active")
        if request.GET:
            url += "?" + request.GET.urlencode()
        return redirect(url)

    selected_orders = form.cleaned_data["orders"]
    new_status = (form.cleaned_data.get("new_status") or "").strip()

    if not selected_orders:
        messages.warning(request, "Спочатку познач хоча б одне замовлення.")
        url = reverse("orders_active")
        if request.GET:
            url += "?" + request.GET.urlencode()
        return redirect(url)

    if not new_status:
        messages.warning(request, "Обери новий статус.")
        url = reverse("orders_active")
        if request.GET:
            url += "?" + request.GET.urlencode()
        return redirect(url)

    try:
        change_production_order_status(
            production_orders=list(selected_orders),
            new_status=new_status,
            changed_by=request.user,
            on_sales_line_done=_sync_sales_line_after_order_done,
        )
    except InvalidStatusTransition as exc:
        current_label = STATUS_LABELS.get(exc.status, exc.status)
        next_label = STATUS_LABELS.get(exc.next_status, exc.next_status)
        messages.error(
            request,
            f"Так не можна: {current_label} → {next_label}.",
        )
        url = reverse("orders_active")
        if request.GET:
            url += "?" + request.GET.urlencode()
        return redirect(url)

    messages.success(request, "Готово! Статус оновлено для вибраних замовлень.")
    url = reverse("orders_active")
    if request.GET:
        url += "?" + request.GET.urlencode()
    return redirect(url)


@login_required
def orders_completed(request):
    search_query = (request.GET.get("q") or "").strip()
    orders = (
        ProductionOrder.objects.only("id", "finished_at", "product_id", "variant_id")
        .select_related(
            "product",
            "variant",
            "variant__primary_material_color",
            "variant__secondary_material_color",
        )
        .filter(status=STATUS_DONE)
        .order_by("-finished_at")
    )
    if search_query:
        search_filters = (
            Q(product__name__icontains=search_query)
            | Q(variant__primary_material_color__name__icontains=search_query)
            | Q(variant__secondary_material_color__name__icontains=search_query)
            | Q(comment__icontains=search_query)
        )
        if search_query.isdigit():
            search_filters |= Q(id=int(search_query))
        orders = orders.filter(search_filters)

    paginator = Paginator(orders, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    query_params = request.GET.copy()
    query_params.pop("page", None)
    query_string = query_params.urlencode()

    return render(
        request,
        "orders/completed.html",
        {
            "page_title": "Завершені",
            "page_obj": page_obj,
            "search_query": search_query,
            "query_string": query_string,
        },
    )


@login_required
def orders_create(request):
    template_name = "orders/create.html"
    context = {"page_title": "Нове замовлення", "page_title_center": True}

    def _create_orders_for_bundle(*, form: OrderForm, orders_url: str) -> int:
        created = 0
        for row in form.bundle_component_rows:
            bc: BundleComponent = row["bundle_component"]  # type: ignore[assignment]
            component: Product = row["component"]  # type: ignore[assignment]
            primary_field_name = str(row["primary_field_name"])
            secondary_field_name = str(row["secondary_field_name"])
            embroidery_field_name = row.get("embroidery_field_name")
            primary_color = form.cleaned_data.get(primary_field_name)
            secondary_color = form.cleaned_data.get(secondary_field_name)
            is_embroidery = (
                bool(form.cleaned_data.get(embroidery_field_name))
                if embroidery_field_name
                else False
            )
            for _ in range(int(bc.quantity)):
                create_production_order(
                    product=component,
                    primary_material_color=primary_color,
                    secondary_material_color=secondary_color,
                    is_etsy=form.cleaned_data["is_etsy"],
                    is_embroidery=is_embroidery,
                    is_urgent=form.cleaned_data["is_urgent"],
                    comment=form.cleaned_data.get("comment"),
                    created_by=request.user,
                    orders_url=orders_url,
                )
                created += 1
        return created

    if request.method == "POST":
        form = OrderForm(request.POST)
        if form.is_valid():
            orders_url = request.build_absolute_uri(reverse_lazy("orders_active"))
            try:
                product: Product = form.cleaned_data["product"]
                if product.kind == Product.Kind.BUNDLE:
                    created = _create_orders_for_bundle(form=form, orders_url=orders_url)
                else:
                    create_production_order(
                        product=product,
                        primary_material_color=form.cleaned_data["primary_material_color"],
                        secondary_material_color=form.cleaned_data.get("secondary_material_color"),
                        is_etsy=form.cleaned_data["is_etsy"],
                        is_embroidery=form.cleaned_data["is_embroidery"],
                        is_urgent=form.cleaned_data["is_urgent"],
                        comment=form.cleaned_data.get("comment"),
                        created_by=request.user,
                        orders_url=orders_url,
                    )
                    created = 1
            except ValueError:
                form.add_error("primary_material_color", "Обери основний колір для цієї моделі.")
                context["form"] = form
                return render(request, template_name, context)
            if created == 1:
                messages.success(request, "Готово! Замовлення створено.")
            else:
                messages.success(request, f"Готово! Створено замовлень: {created}.")
            return redirect("orders_active")
        context["form"] = form
        return render(request, template_name, context)

    initial = {}
    raw_product_id = (request.GET.get("product") or "").strip()
    if raw_product_id:
        initial["product"] = raw_product_id

    form = OrderForm(initial=initial)
    context["form"] = form
    return render(request, template_name, context)


@login_required
def order_detail(request, pk):
    order = get_object_or_404(ProductionOrder, id=pk)
    statuses = ProductionOrderStatusHistory.objects.filter(order=order).order_by("-changed_at")

    order_data = {
        "id": order.id,
        "product": order.product.name,
        "color": order.variant.display_color_label() if order.variant else "-",
        "is_embroidery": order.is_embroidery,
        "comment": order.comment,
        "is_urgent": order.is_urgent,
        "is_etsy": order.is_etsy,
        "created_at": localtime(order.created_at) if order.created_at else None,
        "finished_at": localtime(order.finished_at) if order.finished_at else None,
        "status_code": order.status,
        "status_display": order.get_status_display(),
        "status_history": [
            {
                "id": status.id,
                "new_status": status.new_status,
                "new_status_display": dict(ProductionOrderStatusHistory.STATUS_CHOICES).get(
                    status.new_status, "Unknown"
                ),
                "changed_by": status.changed_by.username if status.changed_by else "Unknown",
                "changed_at": localtime(status.changed_at) if status.changed_at else None,
            }
            for status in statuses
        ],
    }

    return render(
        request,
        "orders/detail.html",
        {
            "order": order_data,
            "page_title": f"Замовлення #{order.id}",
            "order_edit_url": reverse("order_edit", args=[order.id]),
        },
    )


@login_required
def order_edit(request, pk):
    order = get_object_or_404(ProductionOrder, id=pk)
    if request.method == "POST":
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, "Готово! Замовлення оновлено.")
            return redirect("order_detail", pk=order.id)
    else:
        form = OrderForm(instance=order)
    form.fields["product"].queryset = Product.objects.filter(
        Q(archived_at__isnull=True) | Q(pk=order.product_id)
    ).order_by("name")
    return render(
        request,
        "orders/order_edit.html",
        {
            "form": form,
            "order": order,
            "page_title": f"Підправити замовлення #{order.id}",
        },
    )
