from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    response.data = {
        "ok": False,
        "message": "Error de API",
        "details": response.data,
    }
    return response
