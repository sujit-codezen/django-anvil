"""Shared "which organization is this for" logic, used by both the
middleware (for plain Django views, where session auth means
`request.user` is already correct by middleware time) and
TenantScopedViewSetMixin (for DRF views, where request.user often isn't
resolved until DRF's own authentication runs inside the view -- see that
mixin's docstring for why it can't just rely on the middleware).
"""

from .models import OrganizationMembership

ORG_HEADER = "HTTP_X_ORG_ID"


def resolve_organization_id(request):
    """`request.user` must already be authenticated by this point.

    An explicit `X-Org-Id` header is honored only if the user is really
    a member of that organization; otherwise, if the user belongs to
    exactly one organization, that one. Anything else -- anonymous,
    ambiguous membership, a header naming an org the user isn't in --
    resolves to no organization.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return None

    header_org_id = request.META.get(ORG_HEADER)
    if header_org_id:
        is_member = OrganizationMembership.objects.filter(
            user=user, organization_id=header_org_id
        ).exists()
        return header_org_id if is_member else None

    membership_org_ids = list(
        OrganizationMembership.objects.filter(user=user).values_list("organization_id", flat=True)[:2]
    )
    if len(membership_org_ids) == 1:
        return membership_org_ids[0]
    return None
