import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from tasks.models import Task
from users.auth import jwt_required


def serialize_task(task):
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "created_at": task.created_at.isoformat(),
        "user_id": task.user_id,
    }


@csrf_exempt
@require_http_methods(["GET", "POST"])
@jwt_required
def tasks_list(request):
    if request.method == "GET":
        tasks = Task.objects.all().order_by("-created_at")

        return JsonResponse(
            {
                "tasks": [
                    serialize_task(task)
                    for task in tasks
                ],
            },
            status=200,
        )

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"error": "Invalid JSON"},
            status=400,
        )

    if not isinstance(data, dict):
        return JsonResponse(
            {"error": "JSON body must be an object"},
            status=400,
        )

    allowed_fields = {"title", "description", "status"}

    if not data:
        return JsonResponse(
            {"error": "At least one field is required"},
            status=400,
        )

    unknown_fields = set(data) - allowed_fields

    if unknown_fields:
        return JsonResponse(
            {
                "error": "Unknown fields",
                "fields": sorted(unknown_fields),
            },
            status=400,
        )

    title = data.get("title")
    description = data.get("description", "")
    status = data.get("status", Task.Status.TODO)

    if not isinstance(title, str) or not title.strip():
        return JsonResponse(
            {"error": "Title must be a non-empty string"},
            status=400,
        )

    if not isinstance(description, str):
        return JsonResponse(
            {"error": "Description must be a string"},
            status=400,
        )

    if not isinstance(status, str):
        return JsonResponse(
            {"error": "Status must be a string"},
            status=400,
        )

    if status not in Task.Status.values:
        return JsonResponse(
            {"error": "Invalid status"},
            status=400,
        )

    task = Task.objects.create(
        title=title.strip(),
        description=description,
        status=status,
        user=request.user,
    )

    return JsonResponse(
        serialize_task(task),
        status=201,
    )


@csrf_exempt
@require_http_methods(["GET", "PATCH", "DELETE"])
@jwt_required
def task_detail(request, task_id):
    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return JsonResponse(
            {"error": "Task not found"},
            status=404,
        )

    if request.method == "GET":
        return JsonResponse(
            serialize_task(task),
            status=200,
        )

    if request.method == "DELETE":
        task.delete()

        return JsonResponse(
            {},
            status=204,
        )

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"error": "Invalid JSON"},
            status=400,
        )

    if not isinstance(data, dict):
        return JsonResponse(
            {"error": "JSON body must be an object"},
            status=400,
        )

    if "title" in data:
        if (
                not isinstance(data["title"], str)
                or not data["title"].strip()
        ):
            return JsonResponse(
                {"error": "Title must be a non-empty string"},
                status=400,
            )

        task.title = data["title"].strip()

    if "description" in data:
        if not isinstance(data["description"], str):
            return JsonResponse(
                {"error": "Description must be a string"},
                status=400,
            )

        task.description = data["description"]

    if "status" in data:
        if not isinstance(data["status"], str):
            return JsonResponse(
                {"error": "Status must be a string"},
                status=400,
            )

        if data["status"] not in Task.Status.values:
            return JsonResponse(
                {"error": "Invalid status"},
                status=400,
            )

        task.status = data["status"]

    task.save()

    return JsonResponse(
        serialize_task(task),
        status=200,
    )