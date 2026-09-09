from django.apps import AppConfig


class TenancyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_forge.tenancy"
    label = "forge_tenancy"
    verbose_name = "Forge Tenancy"
