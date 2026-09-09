"""Resolves the current organization for a request and binds it for the
request's duration -- for plain Django views. Session authentication
means `request.user` is already correct by the time middleware runs.

DRF views don't get their organization from here: DRF's own
authentication (token/JWT, or even `force_authenticate` in tests) runs
*inside* the view, after Django's middleware chain has already executed,
so `request.user` at middleware time is still AnonymousUser for those.
Generated ViewSets instead resolve it themselves, later, via
TenantScopedViewSetMixin -- see that class's docstring. This middleware
is only useful for organization-scoped logic outside DRF.
"""

from .context import reset_current_organization_id, set_current_organization_id
from .resolver import resolve_organization_id


class CurrentOrganizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = set_current_organization_id(resolve_organization_id(request))
        try:
            return self.get_response(request)
        finally:
            reset_current_organization_id(token)
