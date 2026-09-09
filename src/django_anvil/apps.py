from django.apps import AppConfig


class DjangoAnvilConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_anvil"
    verbose_name = "Django Anvil"

    def ready(self):
        from django.utils.module_loading import autodiscover_modules

        # Mirrors Django's own admin.py autodiscovery: every installed app
        # gets its resources.py imported, which registers its Resource
        # subclasses via Resource.__init_subclass__.
        autodiscover_modules("resources")
