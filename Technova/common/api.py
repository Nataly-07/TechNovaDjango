import json

from django.http import JsonResponse


def success_response(data=None, message="OK", status=200):
    return JsonResponse(
        {
            "ok": True,
            "message": message,
            "data": data if data is not None else {},
        },
        status=status,
    )


def error_response(message="Error", status=400, details=None):
    payload = {
        "ok": False,
        "message": message,
    }
    if details is not None:
        payload["details"] = details
    return JsonResponse(payload, status=status)


def parse_json_body(request):
    try:
        return json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON invalido: {exc.msg}") from exc
