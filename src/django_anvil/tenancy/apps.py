from django.apps import AppConfig


class TenancyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_anvil.tenancy"
    label = "anvil_tenancy"
    verbose_name = "Anvil Tenancy"
