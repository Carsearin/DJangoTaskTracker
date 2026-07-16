from functools import wraps

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model

from common.responses import error_response


User = get_user_model()


def jwt_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return error_response(
                code="unauthorized",
                message="Authorization header is required",
                status=401,
            )

        if not auth_header.startswith("Bearer "):
            return error_response(
                code="unauthorized",
                message="Invalid authorization header",
                status=401,
            )

        token = auth_header.split(" ", 1)[1]

        if not token:
            return error_response(
                code="unauthorized",
                message="Token is required",
                status=401,
            )

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={
                    "require": ["exp", "iat", "user_id"],
                },
            )
        except jwt.ExpiredSignatureError:
            return error_response(
                code="token_expired",
                message="Token has expired",
                status=401,
            )
        except jwt.InvalidTokenError:
            return error_response(
                code="invalid_token",
                message="Invalid token",
                status=401,
            )

        user_id = payload["user_id"]

        try:
            request.user = User.objects.get(id=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return error_response(
                code="invalid_token",
                message="Invalid token",
                status=401,
            )

        return view_func(request, *args, **kwargs)

    return wrapper