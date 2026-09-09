from django.apps import AppConfig


class RbacConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_forge.rbac"
    label = "forge_rbac"
    verbose_name = "Forge RBAC"
