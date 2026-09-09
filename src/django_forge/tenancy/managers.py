from django.db import models

from .context import get_current_organization_id


class TenantScopedQuerySet(models.QuerySet):
    def for_current_organization(self):
        organization_id = get_current_organization_id()
        if organization_id is None:
            return self.none()
        return self.filter(organization_id=organization_id)


class TenantScopedManager(models.Manager.from_queryset(TenantScopedQuerySet)):
    """Default manager for TenantScopedModel: every query is filtered to
    the current request's organization, and no organization in context
    means no rows -- not "every organization's rows". This applies even
    to plain `Model.objects.all()` calls anywhere in the codebase, which
    is the point: a developer who forgets to scope a query by hand still
    can't leak another tenant's data through it.

    Use `Model.all_objects` (a second, unfiltered manager also present
    on every TenantScopedModel) for the deliberate cases that need every
    organization's rows -- the Django admin and one-off scripts.
    """

    def get_queryset(self):
        return super().get_queryset().for_current_organization()
