from django_anvil.core.resource import Resource
from django_anvil.mixins import OwnerScopedViewSetMixin, SoftDeleteViewSetMixin, TimestampedSerializerMixin

from .models import Coupon, Product, Review, Tag


class ProductResource(Resource):
    model = Product
    fields = ["id", "name", "price", "stock", "is_active", "created_at", "updated_at"]
    read_only_fields = ["id", "created_at", "updated_at"]
    searchable = ["name"]
    filters = ["is_active"]
    sortable = ["price", "created_at"]
    mixins = [SoftDeleteViewSetMixin, TimestampedSerializerMixin]
    permissions = {
        "view": "public",
        "create": "products.add_product",
        "update": "products.change_product",
        "delete": "products.delete_product",
    }
    tenant_scoped = True


class CouponResource(Resource):
    model = Coupon
    fields = [
        "id",
        "code",
        "percent_off",
        "amount_off",
        "expires_at",
        "max_uses",
        "times_used",
        "is_active",
        "created_at",
    ]
    read_only_fields = ["id", "times_used", "created_at"]
    searchable = ["code"]
    filters = ["is_active"]
    sortable = ["expires_at", "created_at"]
    permissions = {
        "view": "products.view_coupon",
        "create": "products.add_coupon",
        "update": "products.change_coupon",
        "delete": "products.delete_coupon",
    }
    tenant_scoped = True
    audited = True


class ReviewResource(Resource):
    """Your own reviews only, including for listing/retrieving --
    OwnerScopedViewSetMixin scopes every action alike, so this is a
    "my reviews" private resource, not a public reviews-on-a-product
    feed (that would need view=public, which needs a different
    get_queryset than this mixin provides out of the box -- see its
    docstring). Also demos the "authenticated" (vs "public" / a real
    codename) permission rule, and is deliberately NOT tenant-scoped.
    """

    model = Review
    fields = ["id", "owner", "rating", "comment", "created_at"]
    read_only_fields = ["id", "owner", "created_at"]
    filters = ["rating"]
    sortable = ["created_at", "rating"]
    mixins = [OwnerScopedViewSetMixin]
    permissions = {
        "view": "authenticated",
        "create": "authenticated",
        "update": "authenticated",
        "delete": "authenticated",
    }


class TagResource(Resource):
    model = Tag
    fields = ["id", "name", "slug"]
    read_only_fields = ["id"]
    searchable = ["name"]
    filters = []
    sortable = ["name"]
    permissions = {
        "view": "public",
        "create": "products.add_tag",
        "update": "products.change_tag",
        "delete": "products.delete_tag",
    }
    tenant_scoped = True
