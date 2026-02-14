from django import forms
from django.db.models import Q
from django.db.models.functions import Lower

from apps.catalog.models import BundleComponent, Product
from apps.catalog.variants import resolve_or_create_variant
from apps.materials.models import MaterialColor
from apps.production.domain.order_statuses import status_choices
from apps.production.models import ProductionOrder

# Design system: one class set for all form controls (see assets/tailwind/input.css)
FORM_INPUT = "form-input"
FORM_SELECT = "form-select"
FORM_TEXTAREA = "form-textarea"
FORM_CHECKBOX = "form-checkbox"


class HiddenEmptyOptionSelect(forms.Select):
    def create_option(self, *args, **kwargs):
        option = super().create_option(*args, **kwargs)
        if option["value"] in ("", None):
            option["attrs"]["disabled"] = True
        return option


class PrimaryMaterialColorChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj: MaterialColor) -> str:
        return obj.name


class SecondaryMaterialColorChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj: MaterialColor) -> str:
        return obj.name


class OrderForm(forms.ModelForm):
    product = forms.ModelChoiceField(
        queryset=Product.objects.none(),
        required=True,
        widget=HiddenEmptyOptionSelect(attrs={"class": FORM_SELECT}),
    )
    primary_material_color = PrimaryMaterialColorChoiceField(
        queryset=MaterialColor.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": FORM_SELECT}),
    )
    secondary_material_color = SecondaryMaterialColorChoiceField(
        queryset=MaterialColor.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": FORM_SELECT}),
    )

    class Meta:
        model = ProductionOrder
        fields = ["is_etsy", "is_embroidery", "is_urgent", "comment"]
        widgets = {
            "is_etsy": forms.CheckboxInput(attrs={"class": FORM_CHECKBOX}),
            "is_urgent": forms.CheckboxInput(attrs={"class": FORM_CHECKBOX}),
            "is_embroidery": forms.CheckboxInput(attrs={"class": FORM_CHECKBOX}),
            "comment": forms.Textarea(
                attrs={
                    "class": FORM_TEXTAREA,
                    "rows": 3,
                    "placeholder": "Коментар (необов'язково)",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._locked_primary_color = False
        self.selected_product: Product | None = None
        self.is_bundle_mode = False
        self.bundle_component_rows: list[dict[str, object]] = []
        self.show_secondary_material_color = False
        self.fields["product"].empty_label = "—"
        self.fields["primary_material_color"].empty_label = "—"
        self.fields["secondary_material_color"].empty_label = "—"

        product_filters = Q(archived_at__isnull=True)
        if self.instance and self.instance.pk:
            product_filters |= Q(pk=self.instance.product_id)
        self.fields["product"].queryset = Product.objects.filter(product_filters).order_by("name")

        raw_product_id = None
        if self.is_bound:
            raw_product_id = self.data.get(self.add_prefix("product"))
        elif self.initial.get("product"):
            raw_product_id = self.initial.get("product")
        elif self.instance and self.instance.pk:
            raw_product_id = self.instance.product_id

        if raw_product_id:
            try:
                self.selected_product = Product.objects.filter(pk=int(raw_product_id)).first()
            except (TypeError, ValueError):
                self.selected_product = None

        self.fields["primary_material_color"].queryset = self._primary_color_queryset(
            product=self.selected_product
        )
        self.fields["secondary_material_color"].queryset = self._secondary_color_queryset(
            product=self.selected_product
        )
        if (
            self.selected_product
            and self.selected_product.secondary_material_id
            and self.fields["secondary_material_color"].queryset.exists()
        ):
            self.show_secondary_material_color = True

        if self.selected_product and self.selected_product.kind == Product.Kind.BUNDLE:
            self.is_bundle_mode = True
            self._init_bundle_component_color_fields(bundle=self.selected_product)
        elif (
            self.selected_product
            and not self.selected_product.allows_embroidery
            and not (self.instance and self.instance.pk)
        ):
            # Don't allow setting embroidery for products that don't support it.
            self.fields["is_embroidery"].disabled = True
            self.initial["is_embroidery"] = False

        if self.instance and self.instance.pk and self.instance.variant_id:
            self.initial["product"] = self.instance.product_id
            self.initial["primary_material_color"] = self.instance.variant.primary_material_color_id
            self.initial["secondary_material_color"] = (
                self.instance.variant.secondary_material_color_id
            )
            if self.instance.variant.primary_material_color_id:
                self.fields["primary_material_color"].queryset = self.fields[
                    "primary_material_color"
                ].queryset | MaterialColor.objects.filter(
                    pk=self.instance.variant.primary_material_color_id
                )
                self.fields["primary_material_color"].queryset = self.fields[
                    "primary_material_color"
                ].queryset.order_by("name")
            if self.instance.variant.secondary_material_color_id:
                self.fields["secondary_material_color"].queryset = self.fields[
                    "secondary_material_color"
                ].queryset | MaterialColor.objects.filter(
                    pk=self.instance.variant.secondary_material_color_id
                )
                self.fields["secondary_material_color"].queryset = self.fields[
                    "secondary_material_color"
                ].queryset.order_by("name")

        # If the model's primary material was changed after the order was created, keep the
        # existing order color but prevent editing it (legacy/grandfathered behavior).
        if (
            self.instance
            and self.instance.pk
            and self.instance.variant_id
            and self.instance.variant.primary_material_color_id
        ):
            instance_color = self.instance.variant.primary_material_color
            raw_product_id = None
            if self.is_bound:
                raw_product_id = self.data.get(self.add_prefix("product"))
            should_lock_for_product = (not self.is_bound) or (
                raw_product_id and str(self.instance.product_id) == str(raw_product_id)
            )
            if (
                should_lock_for_product
                and self.selected_product
                and self.selected_product.primary_material_id != instance_color.material_id
            ):
                self._locked_primary_color = True
                self.fields["primary_material_color"].disabled = True

    def _init_bundle_component_color_fields(self, *, bundle: Product) -> None:
        components = list(
            BundleComponent.objects.filter(bundle=bundle)
            .select_related(
                "component", "component__primary_material", "component__secondary_material"
            )
            .order_by("-is_primary", "id")
        )
        for bc in components:
            component = bc.component
            primary_field_name = f"bundle_component_{bc.pk}_primary_material_color"
            secondary_field_name = f"bundle_component_{bc.pk}_secondary_material_color"
            embroidery_field_name = f"bundle_component_{bc.pk}_is_embroidery"
            secondary_qs = self._secondary_color_queryset(product=component)

            self.fields[primary_field_name] = PrimaryMaterialColorChoiceField(
                queryset=self._primary_color_queryset(product=component),
                required=False,
                widget=forms.Select(attrs={"class": FORM_SELECT}),
                label="Основний колір",
            )
            self.fields[secondary_field_name] = SecondaryMaterialColorChoiceField(
                queryset=secondary_qs,
                required=False,
                widget=forms.Select(attrs={"class": FORM_SELECT}),
                label="Другорядний колір",
            )
            self.fields[primary_field_name].empty_label = "—"
            self.fields[secondary_field_name].empty_label = "—"

            if component.allows_embroidery:
                self.fields[embroidery_field_name] = forms.BooleanField(
                    required=False,
                    initial=False,
                    widget=forms.CheckboxInput(attrs={"class": FORM_CHECKBOX}),
                    label="Вишивка",
                )

            self.bundle_component_rows.append(
                {
                    "bundle_component": bc,
                    "component": component,
                    "quantity": bc.quantity,
                    "primary_field_name": primary_field_name,
                    "secondary_field_name": secondary_field_name,
                    "embroidery_field_name": embroidery_field_name
                    if component.allows_embroidery
                    else None,
                    "show_secondary": bool(
                        component.secondary_material_id and secondary_qs.exists()
                    ),
                }
            )

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get("product")
        primary_material_color = cleaned_data.get("primary_material_color")
        secondary_material_color = cleaned_data.get("secondary_material_color")
        if product and not product.allows_embroidery and not (self.instance and self.instance.pk):
            cleaned_data["is_embroidery"] = False
        if not product:
            return cleaned_data

        if self._locked_primary_color:
            return cleaned_data

        if product.kind == Product.Kind.BUNDLE:
            if not self.bundle_component_rows:
                self.add_error("product", "Спочатку додай компоненти в комплект.")
                return cleaned_data
            self._clean_bundle_component_colors(bundle=product, cleaned_data=cleaned_data)
            return cleaned_data

        available_colors = self._primary_color_queryset(product=product)
        if not product.primary_material_id:
            if primary_material_color is not None:
                self.add_error(
                    "primary_material_color",
                    "Для цієї моделі основний колір недоступний.",
                )
            return cleaned_data

        if (
            primary_material_color
            and primary_material_color.material_id != product.primary_material_id
        ):
            self.add_error(
                "primary_material_color",
                "Обраний колір не належить до матеріалу моделі.",
            )
            return cleaned_data

        if secondary_material_color and not product.secondary_material_id:
            self.add_error(
                "secondary_material_color",
                "Для цієї моделі другорядний колір недоступний.",
            )
            return cleaned_data

        if (
            secondary_material_color
            and product.secondary_material_id
            and secondary_material_color.material_id != product.secondary_material_id
        ):
            self.add_error(
                "secondary_material_color",
                "Обраний колір не належить до другорядного матеріалу моделі.",
            )
            return cleaned_data

        if secondary_material_color and primary_material_color is None:
            self.add_error(
                "primary_material_color",
                "Другорядний колір можливий лише разом з основним.",
            )
            return cleaned_data

        if available_colors.exists() and primary_material_color is None:
            self.add_error(
                "primary_material_color",
                "Обери основний колір для цієї моделі.",
            )

        return cleaned_data

    @staticmethod
    def _primary_color_queryset(*, product: Product | None):
        if product is None:
            return MaterialColor.objects.filter(archived_at__isnull=True).order_by(
                Lower("name"),
                "name",
            )
        if not product.primary_material_id:
            return MaterialColor.objects.none()
        return MaterialColor.objects.filter(
            material_id=product.primary_material_id,
            archived_at__isnull=True,
        ).order_by(Lower("name"), "name")

    @staticmethod
    def _secondary_color_queryset(*, product: Product | None):
        if product is None:
            return MaterialColor.objects.filter(archived_at__isnull=True).order_by(
                Lower("name"),
                "name",
            )
        if not product.secondary_material_id:
            return MaterialColor.objects.none()
        return MaterialColor.objects.filter(
            material_id=product.secondary_material_id,
            archived_at__isnull=True,
        ).order_by(Lower("name"), "name")

    def _clean_bundle_component_colors(self, *, bundle: Product, cleaned_data: dict) -> None:
        # Validate each component's chosen colors.
        for row in self.bundle_component_rows:
            component: Product = row["component"]  # type: ignore[assignment]
            primary_name = str(row["primary_field_name"])
            secondary_name = str(row["secondary_field_name"])
            primary = cleaned_data.get(primary_name)
            secondary = cleaned_data.get(secondary_name)

            requires_primary = bool(
                component.primary_material_id
                and MaterialColor.objects.filter(
                    material_id=component.primary_material_id,
                    archived_at__isnull=True,
                ).exists()
            )
            if requires_primary and primary is None:
                self.add_error(
                    primary_name, f"Обери основний колір для компонента: {component.name}."
                )
                continue
            if (
                primary
                and component.primary_material_id
                and primary.material_id != component.primary_material_id
            ):
                self.add_error(primary_name, "Обраний колір не належить до матеріалу компонента.")
                continue

            if secondary and not component.secondary_material_id:
                self.add_error(
                    secondary_name, "Для цього компонента другорядний колір недоступний."
                )
                continue
            if (
                secondary
                and component.secondary_material_id
                and secondary.material_id != component.secondary_material_id
            ):
                self.add_error(
                    secondary_name,
                    "Обраний колір не належить до другорядного матеріалу компонента.",
                )
                continue
            if secondary and primary is None:
                self.add_error(primary_name, "Другорядний колір можливий лише разом з основним.")

    def save(self, commit: bool = True):
        instance: ProductionOrder = super().save(commit=False)
        instance.product = self.cleaned_data["product"]
        primary_material_color = self.cleaned_data.get("primary_material_color")
        secondary_material_color = self.cleaned_data.get("secondary_material_color")
        instance.variant = resolve_or_create_variant(
            product_id=instance.product_id,
            primary_material_color_id=(
                primary_material_color.id if primary_material_color else None
            ),
            secondary_material_color_id=(
                secondary_material_color.id if secondary_material_color else None
            ),
        )
        if commit:
            instance.save()
        return instance


class OrderStatusUpdateForm(forms.Form):
    orders = forms.ModelMultipleChoiceField(
        queryset=ProductionOrder.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Позначити замовлення",
    )
    new_status = forms.ChoiceField(
        choices=status_choices(include_legacy=False, include_terminal=True),
        label="Новий статус",
    )
