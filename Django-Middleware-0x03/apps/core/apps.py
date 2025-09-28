# apps/core/apps.py
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core'

    def ready(self):
        """Import signals and perform startup tasks"""
        try:
            import apps.core.signals  # noqa
        except ImportError:
            pass