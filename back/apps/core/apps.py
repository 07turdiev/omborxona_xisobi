from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    label = 'core'
    verbose_name = 'Yadro'

    def ready(self):
        """Tenant izolyatsiyasi tekshiruvlarini ro'yxatdan o'tkazadi."""
        from apps.core import checks  # noqa: F401
