import factory
from factory.django import DjangoModelFactory

from apps.accounts.models import User
from apps.catalog.models import Product
from apps.materials.models import Material, MaterialColor
from apps.production.models import ProductionOrder


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user_{n}")

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        password = extracted or "testpass123"
        obj.set_password(password)
        if create:
            obj.save(update_fields=["password"])


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f"Model {n}")
    primary_material = None


class ColorFactory(DjangoModelFactory):
    class Meta:
        model = MaterialColor

    material = factory.SubFactory(
        "apps.production.tests.factories.MaterialFactory"
    )
    name = factory.Sequence(lambda n: f"Primary Color {n}")
    code = factory.Sequence(lambda n: n + 100)


class MaterialFactory(DjangoModelFactory):
    class Meta:
        model = Material

    name = factory.Sequence(lambda n: f"Material {n}")


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = ProductionOrder

    product = factory.SubFactory(ProductFactory)
    color = factory.SubFactory(ColorFactory)
    variant = None
    status = "new"
    is_embroidery = False
    is_urgent = False
    is_etsy = False

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        from apps.catalog.variants import resolve_or_create_variant

        product = kwargs.get("product")
        if product is None:
            product = ProductFactory()
        kwargs["product"] = product

        primary_material_color = kwargs.pop("primary_material_color", None)
        legacy_color = kwargs.pop("color", None)
        if primary_material_color is None and legacy_color is not None:
            primary_material_color = legacy_color

        variant = kwargs.get("variant")
        if variant is None:
            if primary_material_color is None:
                primary_material_color = ColorFactory()
            if product.primary_material_id is None:
                product.primary_material = primary_material_color.material
                product.save(update_fields=["primary_material"])
            variant = resolve_or_create_variant(
                product_id=product.id,
                primary_material_color_id=primary_material_color.id,
            )
            kwargs["variant"] = variant
        return super()._create(model_class, *args, **kwargs)
