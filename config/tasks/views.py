from django.http import JsonResponse
from django.views.decorators.http import require_GET

from users.auth import jwt_required


@require_GET
@jwt_required
def tasks_list(request):
    return JsonResponse(
        {
            "message": "Tasks API works",
            "user": request.user.username,
        },
        status=200,
    )