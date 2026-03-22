from decimal import Decimal, InvalidOperation

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from producto.models import Caracteristica


def _dto(c: Caracteristica) -> dict:
    return {
        "id": c.id,
        "categoria": c.categoria,
        "marca": c.marca,
        "color": c.color,
        "descripcion": c.descripcion,
        "precioCompra": str(c.precio_compra),
        "precioVenta": str(c.precio_venta),
    }


@require_http_methods(["GET"])
def listar_caracteristicas(request):
    items = [_dto(c) for c in Caracteristica.objects.order_by("id")]
    return success_response({"items": items})


@csrf_exempt
@require_http_methods(["GET", "POST"])
def caracteristicas_raiz(request):
    if request.method == "GET":
        return listar_caracteristicas(request)
    return require_auth(roles=["admin", "empleado"])(_crear_caracteristica)(request)


def _crear_caracteristica(request):
    try:
        p = parse_json_body(request)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    try:
        c = Caracteristica.objects.create(
            categoria=str(p["categoria"]).strip(),
            marca=str(p["marca"]).strip(),
            color=str(p.get("color", "") or ""),
            descripcion=str(p.get("descripcion", "") or ""),
            precio_compra=Decimal(str(p.get("precioCompra", p.get("precio_compra", "0")))),
            precio_venta=Decimal(str(p.get("precioVenta", p.get("precio_venta", "0")))),
        )
    except (KeyError, InvalidOperation) as exc:
        return error_response(str(exc), status=400)
    return success_response(_dto(c), status=201)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def caracteristica_por_id(request, caracteristica_id: int):
    if request.method == "GET":
        c = Caracteristica.objects.filter(id=caracteristica_id).first()
        if c is None:
            return error_response("Caracteristica no encontrada.", status=404)
        return success_response(_dto(c))
    return require_auth(roles=["admin", "empleado"])(_mutar_caracteristica)(
        request, caracteristica_id
    )


def _mutar_caracteristica(request, caracteristica_id: int):
    if request.method == "PUT":
        c = Caracteristica.objects.filter(id=caracteristica_id).first()
        if c is None:
            return error_response("Caracteristica no encontrada.", status=404)
        try:
            p = parse_json_body(request)
        except ValueError as exc:
            return error_response(str(exc), status=400)
        if "categoria" in p:
            c.categoria = str(p["categoria"]).strip()
        if "marca" in p:
            c.marca = str(p["marca"]).strip()
        if "color" in p:
            c.color = str(p["color"] or "")
        if "descripcion" in p:
            c.descripcion = str(p["descripcion"] or "")
        try:
            if "precioCompra" in p or "precio_compra" in p:
                c.precio_compra = Decimal(str(p.get("precioCompra", p.get("precio_compra"))))
            if "precioVenta" in p or "precio_venta" in p:
                c.precio_venta = Decimal(str(p.get("precioVenta", p.get("precio_venta"))))
        except InvalidOperation as exc:
            return error_response(str(exc), status=400)
        c.save()
        return success_response(_dto(c))
    deleted, _ = Caracteristica.objects.filter(id=caracteristica_id).delete()
    if not deleted:
        return error_response("Caracteristica no encontrada.", status=404)
    return success_response({}, message="Eliminada")
