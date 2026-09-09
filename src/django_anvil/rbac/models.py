"""RBAC = Django's own Group/Permission system, given a friendlier name
and a couple of convenience methods. No new permissions table, no new
concepts a Django developer doesn't already know -- `Role` just *is* a
`Group`, so it shows up in the normal Django admin "Groups" machinery
and works with `user.has_perm(...)`, `user.groups.add(...)`, etc.
"""

from django.contrib.auth.models import Group, Permission
from django.db.models import Q


class Role(Group):
    class Meta:
        proxy = True
        app_label = "forge_rbac"
        verbose_name = "Role"
        verbose_name_plural = "Roles"

    def grant(self, *codenames):
        """Add one or more permissions by "app_label.codename", e.g.
        role.grant("products.add_product", "products.change_product").
        """
        query = Q()
        for codename in codenames:
            app_label, _, name = codename.partition(".")
            query |= Q(content_type__app_label=app_label, codename=name)

        matched = Permission.objects.filter(query) if codenames else Permission.objects.none()
        found_codenames = {f"{p.content_type.app_label}.{p.codename}" for p in matched}
        missing = set(codenames) - found_codenames
        if missing:
            raise ValueError(f"Unknown permission codename(s): {', '.join(sorted(missing))}")

        self.permissions.add(*matched)
        return self
