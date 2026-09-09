"""Turns a Resource's `permissions` mapping into real DRF enforcement.

A generated ViewSet carries a `permission_map` class attribute (copied
straight from Resource.permissions) and this one BasePermission reads it
per request. Two special values are recognised; anything else is treated
as a Django permission codename ("app_label.codename") checked against
the requesting user.
"""

from rest_framework.permissions import BasePermission

PUBLIC = "public"
AUTHENTICATED = "authenticated"

ACTION_KEYS = {
    "list": "view",
    "retrieve": "view",
    "create": "create",
    "update": "update",
    "partial_update": "update",
    "destroy": "delete",
}


class ResourcePermission(BasePermission):
    def has_permission(self, request, view):
        permission_map = getattr(view, "permission_map", {})
        key = ACTION_KEYS.get(view.action)
        rule = permission_map.get(key)

        if rule == PUBLIC:
            return True
        if rule == AUTHENTICATED:
            return request.user.is_authenticated
        if rule:
            return request.user.is_authenticated and request.user.has_perm(rule)

        # No rule declared for this action: fail closed, not open.
        return False
