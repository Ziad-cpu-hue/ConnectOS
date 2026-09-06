from django.apps import AppConfig


class NasManagerConfig(AppConfig):
    name = 'nas_manager'

    def ready(self):
        from . import signals  # noqa: F401
