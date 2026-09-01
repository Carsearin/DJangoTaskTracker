import json
from unittest.mock import patch

import jwt
from django.conf import settings

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class RegisterViewTest(TestCase):

    def setUp(self):
        self.url = reverse("register")

    def test_register_user_success(self):
        response = self.client.post(
            self.url,
            data=json.dumps({
                "username": "test_user",
                "password": "test_password",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(User.objects.count(), 1)

        user = User.objects.get(username="test_user")

        self.assertEqual(user.username, "test_user")
        self.assertNotEqual(user.password, "test_password")
        self.assertTrue(user.check_password("test_password"))

    def test_register_user_missing_fields(self):
        response = self.client.post(
            self.url,
            data=json.dumps({}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_register_user_empty_strings(self):
        response = self.client.post(
            self.url,
            data=json.dumps({
                "username": "",
                "password": "",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), 0)

    def test_register_user_duplicate_username(self):
        User.objects.create_user(
            username="test_user",
            password="test_password",
        )

        response = self.client.post(
            self.url,
            data=json.dumps({
                "username": "test_user",
                "password": "another_password",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)

    def test_register_user_invalid_json(self):
        response = self.client.post(
            self.url,
            data="{invalid json",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), 0)

    def test_register_user_invalid_json_type(self):
        response = self.client.post(
            self.url,
            data=json.dumps([]),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), 0)

    def test_register_user_weak_password(self):
        response = self.client.post(
            self.url,
            data=json.dumps({
                "username": "test_user",
                "password": "123",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), 0)

    def test_register_user_database_duplicate_fallback(self):
        with patch.object(
            User.objects,
            "create_user",
            side_effect=IntegrityError,
        ):
            response = self.client.post(
                self.url,
                data=json.dumps({
                    "username": "test_user",
                    "password": "StrongPassword123!",
                }),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(User.objects.count(), 0)

    def test_register_only_accepts_post(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)

    def test_register_user_password_similar_to_username(self):
        response = self.client.post(
            self.url,
            data=json.dumps({
                "username": "similarusername",
                "password": "similarusername",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), 0)

    def test_register_user_malformed_bytes(self):
        response = self.client.post(
            self.url,
            data=b"\x80\x81\x82",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), 0)


class LoginViewTest(TestCase):

    def setUp(self):
        self.url = reverse("login")

        self.user = User.objects.create_user(
            username="test_user",
            password="StrongPassword123!",
        )

    def test_successful_login_writes_info_log(self):
        with self.assertLogs(
                "users.views",
                level="INFO",
        ) as captured:
            response = self.client.post(
                self.url,
                data=json.dumps({
                    "username": "test_user",
                    "password": "StrongPassword123!",
                }),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)

        logs = "\n".join(captured.output)

        self.assertIn(
            "Login succeeded",
            logs,
        )
        self.assertIn(
            f"user_id={self.user.id}",
            logs,
        )
        self.assertIn(
            f"username={self.user.username}",
            logs,
        )

    def test_failed_login_writes_warning_log(self):
        with self.assertLogs(
                "users.views",
                level="WARNING",
        ) as captured:
            response = self.client.post(
                self.url,
                data=json.dumps({
                    "username": "test_user",
                    "password": "WrongPassword123!",
                }),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 401)

        logs = "\n".join(captured.output)

        self.assertIn(
            "WARNING",
            logs,
        )
        self.assertIn(
            "Login failed",
            logs,
        )
        self.assertIn(
            "username='test_user'",
            logs,
        )

    def test_login_user_success(self):
        response = self.client.post(
            self.url,
            data=json.dumps({
                "username": "test_user",
                "password": "StrongPassword123!",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        token = response.json()["token"]

        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        self.assertEqual(payload["user_id"], self.user.id)
        self.assertEqual(payload["username"], self.user.username)

        self.assertIn("iat", payload)
        self.assertIn("exp", payload)

    def test_login_user_wrong_password(self):
        response = self.client.post(
            self.url,
            data=json.dumps({
                "username": "test_user",
                "password": "WrongPassword123!",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertNotIn("token", response.json())

    def test_login_user_not_found(self):
        response = self.client.post(
            self.url,
            data=json.dumps({
                "username": "unknown_user",
                "password": "StrongPassword123!",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertNotIn("token", response.json())

    def test_login_user_missing_fields(self):
        response = self.client.post(
            self.url,
            data=json.dumps({}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_login_user_empty_strings(self):
        response = self.client.post(
            self.url,
            data=json.dumps({
                "username": "",
                "password": "",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_login_user_invalid_json(self):
        response = self.client.post(
            self.url,
            data="{invalid json",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_login_user_invalid_json_type(self):
        response = self.client.post(
            self.url,
            data=json.dumps([]),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_login_only_accepts_post(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)

    def test_login_user_malformed_bytes(self):
        response = self.client.post(
            self.url,
            data=b"\x80\x81\x82",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_failed_login_does_not_log_password(self):
        password = "PasswordThatMustNotAppearInLogs123!"

        with self.assertLogs(
                "users.views",
                level="WARNING",
        ) as captured:
            response = self.client.post(
                self.url,
                data=json.dumps({
                    "username": "test_user",
                    "password": password,
                }),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 401)

        logs = "\n".join(captured.output)

        self.assertNotIn(
            password,
            logs,
        )

    def test_successful_login_does_not_log_token(self):
        with self.assertLogs(
                "users.views",
                level="INFO",
        ) as captured:
            response = self.client.post(
                self.url,
                data=json.dumps({
                    "username": "test_user",
                    "password": "StrongPassword123!",
                }),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)

        token = response.json()["token"]
        logs = "\n".join(captured.output)

        self.assertNotIn(
            token,
            logs,
        )