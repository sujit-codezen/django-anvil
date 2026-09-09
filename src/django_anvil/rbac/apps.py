from django.apps import AppConfig


class RbacConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_anvil.rbac"
    label = "anvil_rbac"
    verbose_name = "Anvil RBAC"
