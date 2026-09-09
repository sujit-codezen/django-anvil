"""Reusable ViewSet/Serializer mixins a Resource can opt into via its
`mixins` list. These are plain classes generated ViewSets inherit from
alongside rest_framework.viewsets.ModelViewSet -- normal Python MRO, no
hidden magic.
"""


class SoftDeleteViewSetMixin:
    """Excludes soft-deleted rows and turns destroy() into a soft delete.

    Requires the model to have an `is_deleted` boolean field.
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted"])


class OwnerScopedViewSetMixin:
    """Scopes the queryset to the requesting user and auto-assigns the
    owner on create -- "your own stuff only", for every action including
    list/retrieve. If a Resource combines this with a "public" view
    permission (public reads, owner-only writes), override get_queryset
    on the generated ViewSet to only scope destructive actions, since as
    shipped this mixin scopes every action alike.

    Requires the model to have an owner FK to the user model. Override
    `owner_field` on the generated ViewSet if the field isn't named
    "owner".
    """

    owner_field = "owner"

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_authenticated:
            # Fail closed, not a crash: filtering by AnonymousUser (not a
            # real row) raises instead of matching nothing.
            return queryset.none()
        return queryset.filter(**{self.owner_field: self.request.user})

    def perform_create(self, serializer):
        serializer.save(**{self.owner_field: self.request.user})


class TenantScopedViewSetMixin:
    """Scopes the queryset and new rows to the current request's
    organization (see django_anvil.tenancy.context).

    Resolves the organization itself, in `initial()`, rather than relying
    on CurrentOrganizationMiddleware: DRF authentication (token/JWT, or
    `force_authenticate` in tests) runs *inside* the view, via
    `super().initial()` below, so `request.user` isn't reliably resolved
    until after that call returns -- a plain Django middleware running
    ahead of the view would still see AnonymousUser. Doing it here means
    this works no matter which DRF authentication scheme is in use.

    Also deliberately does NOT read `self.queryset` in get_queryset() -- a
    `queryset = Model.objects.all()` class attribute is evaluated once,
    at import time, before any request exists, which would freeze in "no
    organization" forever (TenantScopedManager's fail-closed default).
    Calling `model.objects.all()` inside the method instead re-evaluates
    it fresh on every request, when the current organization is actually
    known. Put this mixin last, right before ModelViewSet, so mixins
    ahead of it (e.g. SoftDeleteViewSetMixin) can still narrow the
    queryset further via their own `super().get_queryset()` call.
    """

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        from django_anvil.tenancy.context import set_current_organization_id
        from django_anvil.tenancy.resolver import resolve_organization_id

        self._organization_context_token = set_current_organization_id(
            resolve_organization_id(request)
        )

    def finalize_response(self, request, response, *args, **kwargs):
        from django_anvil.tenancy.context import reset_current_organization_id

        token = getattr(self, "_organization_context_token", None)
        if token is not None:
            reset_current_organization_id(token)
        return super().finalize_response(request, response, *args, **kwargs)

    def get_queryset(self):
        model = self.serializer_class.Meta.model
        return model.objects.all()

    def perform_create(self, serializer):
        from django_anvil.tenancy.context import get_current_organization_id

        serializer.save(organization_id=get_current_organization_id())


class TimestampedSerializerMixin:
    """Marks created_at/updated_at read-only if the serializer has them,
    so callers can't set timestamps by hand through the API.
    """

    def get_fields(self):
        fields = super().get_fields()
        for name in ("created_at", "updated_at"):
            if name in fields:
                fields[name].read_only = True
        return fields
