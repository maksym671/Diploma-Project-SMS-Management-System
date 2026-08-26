from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        # Registers the deploy-time mail configuration checks.
        from . import checks  # noqa: F401
