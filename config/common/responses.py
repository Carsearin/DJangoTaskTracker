from django.http import JsonResponse


def error_response(
    code,
    message,
    status,
    fields=None,
):
    error = {
        "code": code,
        "message": message,
    }

    if fields is not None:
        error["fields"] = fields

    return JsonResponse(
        {"error": error},
        status=status,
    )