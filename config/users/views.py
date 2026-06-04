import json

from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


User = get_user_model()


@csrf_exempt
@require_POST
def register(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON"},
            status=400,
        )

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return JsonResponse(
            {"error": "Username and password are required"},
            status=400,
        )

    if User.objects.filter(username=username).exists():
        return JsonResponse(
            {"error": "Username already exists"},
            status=400,
        )

    user = User.objects.create_user(
        username=username,
        password=password,
    )

    return JsonResponse(
        {
            "id": user.id,
            "username": user.username,
        },
        status=201,
    )
