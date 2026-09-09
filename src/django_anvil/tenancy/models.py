from django.conf import settings
from django.db import models

from .managers import TenantScopedManager


class Organization(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "anvil_tenancy"

    def __str__(self):
        return self.name


class OrganizationMembership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="organization_memberships"
    )
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="memberships")

    class Meta:
        app_label = "anvil_tenancy"
        unique_together = [("user", "organization")]

    def __str__(self):
        return f"{self.user} @ {self.organization}"


class TenantScopedModel(models.Model):
    """Base class for any model whose rows belong to one organization.

    `objects` (the default manager) is filtered to the current request's
    organization and returns nothing if there isn't one -- see
    TenantScopedManager. `all_objects` is the same queryset with no
    filtering, for the deliberate cases (Django admin, scripts) that
    need every organization's rows.
    """

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    objects = TenantScopedManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
