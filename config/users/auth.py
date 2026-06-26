import jwt

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse


User = get_user_model()


def jwt_required(view_func):
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return JsonResponse(
                {"error": "Authorization header is required"},
                status=401,
            )

        if not auth_header.startswith("Bearer "):
            return JsonResponse(
                {"error": "Invalid authorization header"},
                status=401,
            )

        token = auth_header.split(" ", 1)[1]

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except jwt.ExpiredSignatureError:
            return JsonResponse(
                {"error": "Token has expired"},
                status=401,
            )
        except jwt.InvalidTokenError:
            return JsonResponse(
                {"error": "Invalid token"},
                status=401,
            )

        user_id = payload.get("user_id")

        try:
            request.user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse(
                {"error": "User not found"},
                status=401,
            )

        return view_func(request, *args, **kwargs)

    return wrapper