import factory
from factory.django import DjangoModelFactory

from apps.accounts.models import User
from apps.catalog.models import Color, Product
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


class ColorFactory(DjangoModelFactory):
    class Meta:
        model = Color

    name = factory.Sequence(lambda n: f"Color {n}")
    code = factory.Sequence(lambda n: n + 100)
    status = "in_stock"


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

        color = kwargs.pop("color", None)
        variant = kwargs.get("variant")
        if variant is None:
            if color is None:
                color = ColorFactory()
            variant = resolve_or_create_variant(
                product_id=product.id,
                color_id=color.id,
            )
            kwargs["variant"] = variant
        return super()._create(model_class, *args, **kwargs)
