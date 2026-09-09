from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from django_anvil.tenancy.models import TenantScopedModel


class Product(TenantScopedModel):
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Coupon(TenantScopedModel):
    code = models.CharField(max_length=50, unique=True)
    percent_off = models.PositiveIntegerField(null=True, blank=True)
    amount_off = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    times_used = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.code


class Review(models.Model):
    """Deliberately NOT tenant-scoped: a review belongs to the person who
    wrote it, not to an organization -- this is the demo for
    OwnerScopedViewSetMixin, the one mixin the rest of the demo doesn't
    otherwise exercise. No FK to Product on purpose: the sample-payload
    generator doesn't yet know how to fabricate a valid value for a
    required foreign key in generated tests (a real, open gap -- noted
    rather than worked around here).
    """

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.rating}/5 by {self.owner_id}"


class Tag(TenantScopedModel):
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=60)

    def __str__(self):
        return self.name
