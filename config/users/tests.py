import json
from unittest.mock import patch

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

        self.assertEqual(response.status_code, 400)

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

        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), 0)

    def test_register_only_accepts_post(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)