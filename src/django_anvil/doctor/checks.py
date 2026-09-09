"""`anvil doctor` -- static checks over the project's settings and
registered Resources. Nothing here touches the database; it's meant to
run in CI or on a machine with no `migrate` yet.
"""

import dataclasses

from django.conf import settings

from django_anvil.core.registry import registry


@dataclasses.dataclass
class CheckResult:
    level: str  # "ok", "info", "warning", "error"
    category: str
    message: str


def run_checks() -> list[CheckResult]:
    results = []
    results.extend(_check_security_settings())
    results.extend(_check_resources())
    return results


def _check_security_settings() -> list[CheckResult]:
    results = []

    if getattr(settings, "DEBUG", False):
        results.append(
            CheckResult("warning", "security", "DEBUG=True -- fine for local development, never deploy with this on.")
        )
    else:
        results.append(CheckResult("ok", "security", "DEBUG=False"))

    secret_key = getattr(settings, "SECRET_KEY", "")
    if secret_key.startswith("django-insecure-"):
        results.append(
            CheckResult(
                "warning",
                "security",
                "SECRET_KEY is still Django's auto-generated insecure default -- replace it before deploying.",
            )
        )
    else:
        results.append(CheckResult("ok", "security", "SECRET_KEY has been changed from the insecure default"))

    if not getattr(settings, "DEBUG", False) and not getattr(settings, "ALLOWED_HOSTS", []):
        results.append(
            CheckResult(
                "error", "security", "DEBUG=False but ALLOWED_HOSTS is empty -- every request will be rejected."
            )
        )

    return results


_MIXIN_FIELD_REQUIREMENTS = {
    "SoftDeleteViewSetMixin": "is_deleted",
    "OwnerScopedViewSetMixin": "owner",
}


def _check_resources() -> list[CheckResult]:
    resources = registry.all()
    if not resources:
        return [CheckResult("warning", "resources", "No Resources registered yet -- define one in <app>/resources.py.")]

    results = []
    for resource in resources:
        results.extend(_check_resource(resource))
    return results


def _check_resource(resource) -> list[CheckResult]:
    label = f"{resource.__name__} ({resource.app_label()}.{resource.model_name()})"
    model = resource.model
    field_names = {f.name for f in model._meta.get_fields()}
    results = []

    if resource.tenant_scoped:
        from django_anvil.tenancy.models import TenantScopedModel

        if not issubclass(model, TenantScopedModel):
            results.append(
                CheckResult(
                    "error",
                    "tenancy",
                    f"{label}: tenant_scoped=True but {model.__name__} doesn't inherit TenantScopedModel.",
                )
            )

    if resource.audited and not hasattr(model, "history"):
        results.append(
            CheckResult(
                "warning",
                "audit",
                f"{label}: audited=True but {model.__name__} has no `history = HistoricalRecords()` field yet.",
            )
        )

    for mixin in resource.mixins:
        required_field = _MIXIN_FIELD_REQUIREMENTS.get(mixin.__name__)
        if required_field and required_field not in field_names:
            results.append(
                CheckResult(
                    "error",
                    "mixins",
                    f"{label}: uses {mixin.__name__} but {model.__name__} has no `{required_field}` field.",
                )
            )

    results.extend(_check_permission_codenames(resource, label, model))
    results.extend(_check_missing_indexes(resource, label, model))

    if not results:
        results.append(CheckResult("ok", "resources", f"{label}: looks good"))

    return results


def _check_permission_codenames(resource, label, model) -> list[CheckResult]:
    """Every action's permission rule should name a real Django
    permission: one of the four auto-created per model (add/change/
    delete/view) or one declared in the model's own Meta.permissions.
    Catches a typo'd or renamed codename before it silently locks
    everyone out (RBAC fails closed, so a bad codename means 403 for
    everyone, forever, with no error to point at the cause).
    """
    default_codenames = {f"{action}_{model.__name__.lower()}" for action in ("add", "change", "delete", "view")}
    custom_codenames = {name for name, _ in model._meta.permissions}
    known_codenames = default_codenames | custom_codenames

    results = []
    for action, rule in resource.permissions.items():
        if rule in ("public", "authenticated", None, ""):
            continue
        app_label, _, codename = rule.partition(".")
        if app_label != resource.app_label() or codename not in known_codenames:
            results.append(
                CheckResult(
                    "warning",
                    "rbac",
                    f"{label}: permission '{rule}' for action '{action}' doesn't match any known "
                    f"permission on {model.__name__} -- that action will be unreachable by anyone.",
                )
            )
    return results


def _check_missing_indexes(resource, label, model) -> list[CheckResult]:
    """A field that's filtered or sorted on a lot deserves a database
    index; Anvil already knows exactly which fields those are, from the
    same Resource declaration that wires up the API -- most projects
    only discover this the hard way, under load.
    """
    results = []
    for field_name in sorted({*resource.filters, *resource.sortable}):
        try:
            field = model._meta.get_field(field_name)
        except Exception:
            continue
        if getattr(field, "db_index", False) or field.primary_key or field.unique:
            continue
        results.append(
            CheckResult(
                "info",
                "performance",
                f"{label}: '{field_name}' is filtered/sorted on but has no db_index -- "
                f"consider adding one if the table gets large.",
            )
        )
    return results
