# Celery ilovasi Django bilan birga yuklansin: `@shared_task` bilan
# yozilgan vazifalar shu ilovaga bog'lanadi.
from .celery import app as celery_app

__all__ = ('celery_app',)
