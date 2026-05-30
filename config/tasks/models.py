from django.conf import settings
from django.db import models


class Task(models.Model):

    class Status(models.TextChoices):
        TODO = "todo", "To Do"
        IN_PROGRESS = "in_progress", "In Progress"
        DONE = "done", "Done"

    title = models.CharField(
        max_length=255,
        verbose_name="Title"
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Description"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
        verbose_name="Status"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created at"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tasks"
    )

    def __str__(self):
        return self.title