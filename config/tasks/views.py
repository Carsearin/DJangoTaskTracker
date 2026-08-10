import json
import logging

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from common.responses import error_response
from tasks.models import Task
from users.auth import jwt_required


logger = logging.getLogger(__name__)


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
        tasks = (
            Task.objects
            .filter(user=request.user)
            .order_by("-created_at")
        )

        logger.debug(
            "Retrieved %d tasks for user_id=%s",
            tasks.count(),
            request.user.id,
        )

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

    allowed_fields = {"title", "description", "status"}

    if not data:
        return error_response(
            code="validation_error",
            message="At least one field is required",
            status=400,
        )

    unknown_fields = set(data) - allowed_fields

    if unknown_fields:
        return error_response(
            code="unknown_fields",
            message="Unknown fields",
            status=400,
            fields=sorted(unknown_fields),
        )

    title = data.get("title")
    description = data.get("description", "")
    status = data.get("status", Task.Status.TODO)

    if not isinstance(title, str) or not title.strip():
        return error_response(
            code="validation_error",
            message="Title must be a non-empty string",
            status=400,
            fields={
                "title": [
                    "Title must be a non-empty string",
                ],
            },
        )

    if not isinstance(description, str):
        return error_response(
            code="validation_error",
            message="Description must be a string",
            status=400,
            fields={
                "description": [
                    "Description must be a string",
                ],
            },
        )

    if not isinstance(status, str):
        return error_response(
            code="validation_error",
            message="Status must be a string",
            status=400,
            fields={
                "status": [
                    "Status must be a string",
                ],
            },
        )

    if status not in Task.Status.values:
        return error_response(
            code="invalid_status",
            message="Invalid status",
            status=400,
            fields={
                "status": [
                    f"Allowed values: {', '.join(Task.Status.values)}",
                ],
            },
        )

    logger.debug(
        "Creating task for user_id=%s status=%s",
        request.user.id,
        status,
    )

    task = Task.objects.create(
        title=title.strip(),
        description=description,
        status=status,
        user=request.user,
    )

    logger.info(
        "Task created task_id=%s user_id=%s status=%s",
        task.id,
        request.user.id,
        task.status,
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
        task = Task.objects.get(
            id=task_id,
            user=request.user,
        )
    except Task.DoesNotExist:
        logger.warning(
            "Task access failed task_id=%s user_id=%s",
            task_id,
            request.user.id,
        )

        return error_response(
            code="not_found",
            message="Task not found",
            status=404,
        )

    if request.method == "GET":
        logger.debug(
            "Retrieved task_id=%s for user_id=%s",
            task.id,
            request.user.id,
        )

        return JsonResponse(
            serialize_task(task),
            status=200,
        )

    if request.method == "DELETE":
        deleted_task_id = task.id
        owner_id = task.user_id

        task.delete()

        logger.info(
            "Task deleted task_id=%s user_id=%s",
            deleted_task_id,
            owner_id,
        )

        return HttpResponse(status=204)

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

    if not data:
        return error_response(
            code="validation_error",
            message="At least one field is required",
            status=400,
        )

    allowed_fields = {"title", "description", "status"}
    unknown_fields = set(data) - allowed_fields

    if unknown_fields:
        return error_response(
            code="unknown_fields",
            message="Unknown fields",
            status=400,
            fields=sorted(unknown_fields),
        )

    logger.debug(
        "Updating task_id=%s user_id=%s fields=%s",
        task.id,
        request.user.id,
        ",".join(sorted(data.keys())),
    )

    if "title" in data:
        if (
            not isinstance(data["title"], str)
            or not data["title"].strip()
        ):
            return error_response(
                code="validation_error",
                message="Title must be a non-empty string",
                status=400,
                fields={
                    "title": [
                        "Title must be a non-empty string",
                    ],
                },
            )

        task.title = data["title"].strip()

    if "description" in data:
        if not isinstance(data["description"], str):
            return error_response(
                code="validation_error",
                message="Description must be a string",
                status=400,
                fields={
                    "description": [
                        "Description must be a string",
                    ],
                },
            )

        task.description = data["description"]

    if "status" in data:
        if not isinstance(data["status"], str):
            return error_response(
                code="validation_error",
                message="Status must be a string",
                status=400,
                fields={
                    "status": [
                        "Status must be a string",
                    ],
                },
            )

        if data["status"] not in Task.Status.values:
            return error_response(
                code="invalid_status",
                message="Invalid status",
                status=400,
                fields={
                    "status": [
                        f"Allowed values: {', '.join(Task.Status.values)}",
                    ],
                },
            )

        task.status = data["status"]

    task.save()

    updated_fields = sorted(data.keys())

    logger.info(
        "Task updated task_id=%s user_id=%s fields=%s",
        task.id,
        request.user.id,
        ",".join(updated_fields),
    )

    return JsonResponse(
        serialize_task(task),
        status=200,
    )