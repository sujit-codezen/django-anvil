"""Builds a compact text summary of the project's models and Resources --
just enough context for the AI engine to propose code that matches the
project's existing conventions instead of inventing its own.
"""

from django.apps import apps

from django_anvil.core.registry import registry

_SKIP_APP_LABELS = {
    "admin",
    "auth",
    "contenttypes",
    "sessions",
    "messages",
    "staticfiles",
    "django_anvil",
    "anvil_rbac",
    "anvil_tenancy",
}


def build_project_summary() -> str:
    lines = []
    for app_config in apps.get_app_configs():
        if app_config.label in _SKIP_APP_LABELS:
            continue

        models = list(app_config.get_models())
        if not models:
            continue

        lines.append(f"App: {app_config.label}")
        for model in models:
            lines.append(f"  Model {model.__name__}:")
            for field in model._meta.get_fields():
                if field.auto_created and not field.concrete:
                    continue
                field_type = getattr(field, "get_internal_type", lambda: type(field).__name__)()
                lines.append(f"    - {field.name}: {field_type}")

            try:
                resource = registry.get_for_model(model)
            except LookupError:
                continue

            lines.append(f"    Resource: {resource.__name__}")
            lines.append(f"      fields: {resource.fields}")
            lines.append(f"      permissions: {resource.permissions}")
            lines.append(f"      tenant_scoped: {resource.tenant_scoped}")

    return "\n".join(lines) if lines else "(no project models yet)"
