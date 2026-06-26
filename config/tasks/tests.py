import jwt
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.urls import reverse

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
            password="test_password",
        )

        task = Task.objects.create(
            title="Learn Django",
            user=user,
        )

        self.assertEqual(task.title, "Learn Django")
        self.assertEqual(task.status, Task.Status.TODO)
        self.assertEqual(task.user, user)
        self.assertEqual(str(task), "Learn Django")
        self.assertIsNotNone(task.created_at)


class TasksAuthTest(TestCase):

    def setUp(self):
        self.url = reverse("tasks-list")

        self.user = User.objects.create_user(
            username="test_user",
            password="StrongPassword123!",
        )

    def make_token(
        self,
        user=None,
        user_id=None,
        username=None,
        expired=False,
        secret=None,
    ):
        now = datetime.now(timezone.utc)
        token_user = user or self.user

        payload = {
            "user_id": user_id or token_user.id,
            "username": username or token_user.username,
            "iat": now,
            "exp": now - timedelta(minutes=1) if expired else now + timedelta(
                minutes=settings.JWT_EXPIRATION_MINUTES,
            ),
        }

        return jwt.encode(
            payload,
            secret or settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    def test_tasks_without_token_returns_401(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)

    def test_tasks_without_bearer_prefix_returns_401(self):
        token = self.make_token()

        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=token,
        )

        self.assertEqual(response.status_code, 401)

    def test_tasks_with_empty_bearer_token_returns_401(self):
        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION="Bearer ",
        )

        self.assertEqual(response.status_code, 401)

    def test_tasks_with_invalid_token_returns_401(self):
        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION="Bearer invalid_token",
        )

        self.assertEqual(response.status_code, 401)

    def test_tasks_with_expired_token_returns_401(self):
        token = self.make_token(expired=True)

        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 401)

    def test_tasks_with_invalid_signature_returns_401(self):
        token = self.make_token(
            secret="wrong_secret_key_that_is_long_enough",
        )

        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 401)

    def test_tasks_with_token_for_missing_user_returns_401(self):
        token = self.make_token(
            user_id=999999,
            username="missing_user",
        )

        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 401)

    def test_tasks_with_valid_token_returns_200(self):
        token = self.make_token()

        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)

    def test_tasks_user_is_resolved_from_token(self):
        token = self.make_token()

        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"], self.user.username)