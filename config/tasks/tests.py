import json
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.urls import reverse

from tasks.models import Task


User = get_user_model()


class ErrorResponseAssertionsMixin:
    def assert_error_response(
        self,
        response,
        status_code,
        error_code,
    ):
        self.assertEqual(response.status_code, status_code)

        data = response.json()

        self.assertIn("error", data)
        self.assertIsInstance(data["error"], dict)
        self.assertEqual(
            data["error"]["code"],
            error_code,
        )
        self.assertIn(
            "message",
            data["error"],
        )
        self.assertIsInstance(
            data["error"]["message"],
            str,
        )


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


class TasksAuthTest(
    ErrorResponseAssertionsMixin,
    TestCase,
):
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
            "user_id": (
                user_id
                if user_id is not None
                else token_user.id
            ),
            "username": (
                username
                if username is not None
                else token_user.username
            ),
            "iat": now,
            "exp": (
                now - timedelta(minutes=1)
                if expired
                else now + timedelta(
                    minutes=settings.JWT_EXPIRATION_MINUTES,
                )
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

        response = self.client.post(
            self.url,
            data=json.dumps({
                "title": "Authenticated user task",
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 201)

        task = Task.objects.get(
            id=response.json()["id"],
        )

        self.assertEqual(task.user, self.user)

    def test_tasks_with_missing_required_claim_returns_401(self):
        now = datetime.now(timezone.utc)

        token = jwt.encode(
            {
                "user_id": self.user.id,
                "username": self.user.username,
                "iat": now,
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 401)

    def test_tasks_with_invalid_user_id_type_returns_401(self):
        now = datetime.now(timezone.utc)

        token = jwt.encode(
            {
                "user_id": "abc",
                "username": self.user.username,
                "iat": now,
                "exp": now + timedelta(
                    minutes=settings.JWT_EXPIRATION_MINUTES,
                ),
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 401)

    def test_tasks_without_token_returns_standard_error_response(
        self,
    ):
        response = self.client.get(self.url)

        self.assert_error_response(
            response,
            401,
            "unauthorized",
        )


class TasksCrudTest(
    ErrorResponseAssertionsMixin,
    TestCase,
):
    def setUp(self):
        self.list_url = reverse("tasks-list")

        self.user = User.objects.create_user(
            username="crud_user",
            password="StrongPassword123!",
        )

        now = datetime.now(timezone.utc)

        self.token = jwt.encode(
            {
                "user_id": self.user.id,
                "username": self.user.username,
                "iat": now,
                "exp": now + timedelta(
                    minutes=settings.JWT_EXPIRATION_MINUTES,
                ),
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        self.auth_header = f"Bearer {self.token}"

        self.task = Task.objects.create(
            title="Initial task",
            description="Initial description",
            status=Task.Status.TODO,
            user=self.user,
        )

        self.other_user = User.objects.create_user(
            username="other_user",
            password="StrongPassword123!",
        )

        self.other_task = Task.objects.create(
            title="Other user's task",
            description="Other user's description",
            status=Task.Status.IN_PROGRESS,
            user=self.other_user,
        )

    def test_get_tasks_list(self):
        response = self.client.get(
            self.list_url,
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.json()["tasks"]),
            1,
        )
        self.assertEqual(
            response.json()["tasks"][0]["id"],
            self.task.id,
        )

    def test_create_task(self):
        response = self.client.post(
            self.list_url,
            data=json.dumps({
                "title": "New task",
                "description": "New description",
                "status": Task.Status.IN_PROGRESS,
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Task.objects.count(), 3)

        created_task = Task.objects.get(
            id=response.json()["id"],
        )

        self.assertEqual(
            created_task.title,
            "New task",
        )
        self.assertEqual(
            created_task.status,
            Task.Status.IN_PROGRESS,
        )
        self.assertEqual(
            created_task.user,
            self.user,
        )

    def test_get_task_by_id(self):
        detail_url = reverse(
            "task-detail",
            args=[self.task.id],
        )

        response = self.client.get(
            detail_url,
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["id"],
            self.task.id,
        )
        self.assertEqual(
            response.json()["title"],
            self.task.title,
        )

    def test_update_task(self):
        detail_url = reverse(
            "task-detail",
            args=[self.task.id],
        )

        response = self.client.patch(
            detail_url,
            data=json.dumps({
                "title": "Updated task",
                "status": Task.Status.DONE,
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 200)

        self.task.refresh_from_db()

        self.assertEqual(
            self.task.title,
            "Updated task",
        )
        self.assertEqual(
            self.task.status,
            Task.Status.DONE,
        )

    def test_delete_task(self):
        detail_url = reverse(
            "task-detail",
            args=[self.task.id],
        )

        response = self.client.delete(
            detail_url,
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertFalse(
            Task.objects.filter(
                id=self.task.id,
            ).exists(),
        )

    def test_create_task_returns_standard_error_response(self):
        response = self.client.post(
            self.list_url,
            data=json.dumps({}),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assert_error_response(
            response,
            400,
            "validation_error",
        )

    def test_missing_task_returns_standard_error_response(self):
        response = self.client.get(
            reverse(
                "task-detail",
                args=[999999],
            ),
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assert_error_response(
            response,
            404,
            "not_found",
        )

    def test_create_task_with_invalid_status_returns_400(self):
        response = self.client.post(
            self.list_url,
            data=json.dumps({
                "title": "Task with invalid status",
                "status": "invalid_status",
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assert_error_response(
            response,
            400,
            "invalid_status",
        )

        self.assertEqual(Task.objects.count(), 2)

    def test_user_does_not_see_other_users_tasks(self):
        response = self.client.get(
            self.list_url,
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 200)

        tasks = response.json()["tasks"]
        task_ids = [
            task["id"]
            for task in tasks
        ]

        self.assertIn(
            self.task.id,
            task_ids,
        )
        self.assertNotIn(
            self.other_task.id,
            task_ids,
        )
        self.assertEqual(len(tasks), 1)

    def test_user_cannot_get_other_users_task(self):
        detail_url = reverse(
            "task-detail",
            args=[self.other_task.id],
        )

        response = self.client.get(
            detail_url,
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assert_error_response(
            response,
            404,
            "not_found",
        )

    def test_user_cannot_update_other_users_task(self):
        detail_url = reverse(
            "task-detail",
            args=[self.other_task.id],
        )

        response = self.client.patch(
            detail_url,
            data=json.dumps({
                "title": "Hacked title",
                "status": Task.Status.DONE,
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assert_error_response(
            response,
            404,
            "not_found",
        )

        self.other_task.refresh_from_db()

        self.assertEqual(
            self.other_task.title,
            "Other user's task",
        )
        self.assertEqual(
            self.other_task.status,
            Task.Status.IN_PROGRESS,
        )
        self.assertEqual(
            self.other_task.user,
            self.other_user,
        )

    def test_user_cannot_delete_other_users_task(self):
        detail_url = reverse(
            "task-detail",
            args=[self.other_task.id],
        )

        response = self.client.delete(
            detail_url,
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assert_error_response(
            response,
            404,
            "not_found",
        )

        self.assertTrue(
            Task.objects.filter(
                id=self.other_task.id,
                user=self.other_user,
            ).exists(),
        )