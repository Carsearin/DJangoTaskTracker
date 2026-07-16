import json
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from common.responses import error_response


User = get_user_model()


def get_missing_auth_fields(username, password):
    missing_fields = {}

    if not username:
        missing_fields["username"] = [
            "This field is required",
        ]

    if not password:
        missing_fields["password"] = [
            "This field is required",
        ]

    return missing_fields


@csrf_exempt
@require_POST
def register(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return error_response(
            code="invalid_json",
            message="Invalid JSON",
            status=400,
        )

    if not isinstance(data, dict):
        return error_response(
            code="invalid_request",
            message="JSON body must be an object",
            status=400,
        )

    username = data.get("username")
    password = data.get("password")

    missing_fields = get_missing_auth_fields(
        username,
        password,
    )

    if missing_fields:
        return error_response(
            code="validation_error",
            message="Required fields are missing",
            status=400,
            fields=missing_fields,
        )

    if User.objects.filter(username=username).exists():
        return error_response(
            code="username_conflict",
            message="Username already exists",
            status=409,
            fields={
                "username": [
                    "Username already exists",
                ],
            },
        )

    temp_user = User(username=username)

    try:
        validate_password(
            password,
            user=temp_user,
        )
    except ValidationError as error:
        return error_response(
            code="validation_error",
            message="Password validation failed",
            status=400,
            fields={
                "password": error.messages,
            },
        )

    try:
        user = User.objects.create_user(
            username=username,
            password=password,
        )
    except IntegrityError:
        return error_response(
            code="username_conflict",
            message="Username already exists",
            status=409,
            fields={
                "username": [
                    "Username already exists",
                ],
            },
        )

    return JsonResponse(
        {
            "id": user.id,
            "username": user.username,
        },
        status=201,
    )


@csrf_exempt
@require_POST
def login(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return error_response(
            code="invalid_json",
            message="Invalid JSON",
            status=400,
        )

    if not isinstance(data, dict):
        return error_response(
            code="invalid_request",
            message="JSON body must be an object",
            status=400,
        )

    username = data.get("username")
    password = data.get("password")

    missing_fields = get_missing_auth_fields(
        username,
        password,
    )

    if missing_fields:
        return error_response(
            code="validation_error",
            message="Required fields are missing",
            status=400,
            fields=missing_fields,
        )

    user = authenticate(
        request,
        username=username,
        password=password,
    )

    if user is None:
        return error_response(
            code="invalid_credentials",
            message="Invalid credentials",
            status=401,
        )

    now = datetime.now(timezone.utc)

    payload = {
        "user_id": user.id,
        "username": user.username,
        "iat": now,
        "exp": now + timedelta(
            minutes=settings.JWT_EXPIRATION_MINUTES,
        ),
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return JsonResponse(
        {"token": token},
        status=200,
    )