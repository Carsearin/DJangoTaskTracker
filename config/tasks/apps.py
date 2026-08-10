import logging

from django.apps import AppConfig


logger = logging.getLogger(__name__)


class TasksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tasks"

    def ready(self):
        logger.info(
            "Task tracker application initialized"
        )