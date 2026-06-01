from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase

from tasks.models import Task


User = get_user_model()


class DatabaseConnectionTest(TestCase):
    def test_database_connection(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()

        self.assertEqual(result[0], 1)


class TaskModelTest(TestCase):
    def test_create_task(self):
        user = User.objects.create_user(
            username="test_user",
            password="test_password"
        )

        task = Task.objects.create(
            title="Learn Django",
            user=user
        )

        self.assertEqual(task.title, "Learn Django")
        self.assertEqual(task.status, Task.Status.TODO)
        self.assertEqual(task.user, user)
        self.assertEqual(str(task), "Learn Django")
        self.assertIsNotNone(task.created_at)