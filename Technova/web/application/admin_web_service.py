import re
from decimal import Decimal, InvalidOperation

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from producto.models import Producto, ProductoCatalogoExtra
from proveedor.models import Proveedor
from usuario.adapters.web.session_views import SESSION_USUARIO_ID
from usuario.infrastructure.models.usuario_model import Usuario
from venta.models import Venta

NOMBRE_PERSONA_RE = re.compile(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]{2,}$")
EMAIL_ALTA_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

PRODUCTO_CATEGORIAS_ALTA_WEB = frozenset({"Celulares", "Portátiles"})
PRODUCTO_MARCAS_ALTA_WEB = frozenset({"Apple", "Lenovo", "Motorola", "Xiaomi"})
PRODUCTO_COLORES_ALTA_WEB = frozenset(
    {
        "Negro",
        "Blanco",
        "Gris",
        "Azul",
        "Rojo",
        "Dorado",
        "Plateado",
        "Verde",
        "Morado",
        "Rosa",
    }
)


def normalizar_color_producto(val: str | None) -> str:
    """Espacios extremos + ``str.capitalize()`` (evita duplicados por mayúsculas)."""
    return (val or "").strip().capitalize()


def validar_color_producto_normalizado(s: str) -> str | None:
    """None si es válido; mensaje corto en español si no."""
    if not s:
        return "Indica un color."
    if len(s) > 40:
        return "El color admite máximo 40 caracteres."
    return None


def colores_sugeridos_inventario() -> list[str]:
    """Colores base + valores distintos ya usados en productos (normalizados), ordenados."""
    merged: set[str] = set(PRODUCTO_COLORES_ALTA_WEB)
    for raw in Producto.objects.exclude(color="").values_list("color", flat=True):
        n = normalizar_color_producto(raw)
        if n:
            merged.add(n)
    return sorted(merged, key=lambda x: x.lower())


TELEFONO_PROV_RE = re.compile(r"^[\d\s+\-().]{7,20}$")


def admin_usuario_sesion(request) -> Usuario:
    uid = request.session.get(SESSION_USUARIO_ID)
    return get_object_or_404(Usuario, pk=uid)


def _galeria_urls_producto(p: Producto) -> list[str]:
    """URLs en orden: principal + adicionales activas (sin duplicados). Base del carrusel en ficha/modal."""
    out: list[str] = []
    seen: set[str] = set()

    def add(u: str | None) -> None:
        if not u:
            return
        t = str(u).strip()
        if not t or t in seen:
            return
        seen.add(t)
        out.append(t)

    main = ""
    if hasattr(p, "imagen") and getattr(p, "imagen", None):
        try:
            main = str(p.imagen.url or "")
        except Exception:
            main = ""
    if not main.strip():
        main = str(getattr(p, "imagen_url", None) or "").strip()
    add(main or None)

    if hasattr(p, "imagenes"):
        for img in p.imagenes.filter(activa=True).order_by("orden", "id"):
            add(getattr(img, "url", None))
    return out


def usuario_modal_dict(u: Usuario) -> dict:
    ventas_preview: list[dict] = []
    if u.rol == Usuario.Rol.CLIENTE:
        ventas_preview = [
            {
                "id": v.id,
                "fecha": v.fecha_venta.isoformat(),
                "total": str(v.total),
                "estado": v.estado,
            }
            for v in Venta.objects.filter(usuario=u).order_by("-fecha_venta")[:12]
        ]
    return {
        "id": u.id,
        "name": f"{u.nombres} {u.apellidos}".strip(),
        "firstName": u.nombres,
        "lastName": u.apellidos,
        "email": u.correo_electronico,
        "role": u.rol,
        "estado": u.activo,
        "documentType": u.tipo_documento,
        "documentNumber": u.numero_documento,
        "phone": u.telefono,
        "address": u.direccion,
        "ventas_preview": ventas_preview,
    }


def producto_modal_dict(p: Producto) -> dict:
    precio_base = p.precio_venta if p.precio_venta is not None else p.costo_unitario
    precio_publico = p.precio_publico if hasattr(p, "precio_publico") else precio_base

    costo_f = float(p.costo_unitario) if p.costo_unitario is not None else 0.0
    margen_pct = None
    if p.precio_venta is not None and costo_f > 0:
        margen_pct = round((float(p.precio_venta) / costo_f - 1) * 100, 2)

    # Obtener imágenes adicionales
    imagenes_adicionales = []
    if hasattr(p, "imagenes"):
        imagenes_adicionales = [
            {
                "url": img.url,
                "orden": img.orden,
                "activa": img.activa,
            }
            for img in p.imagenes.filter(activa=True).order_by("orden")
        ]

    # Obtener imagen principal
    imagen_url = ""
    if hasattr(p, "imagen") and p.imagen:
        imagen_url = p.imagen.url
    elif hasattr(p, "imagen_url") and p.imagen_url:
        imagen_url = p.imagen_url

    precio_venta_f = float(p.precio_venta) if p.precio_venta is not None else None

    return {
        "id": p.id,
        "codigo": p.codigo,
        "nombre": p.nombre,
        "stock": p.stock,
        "activo": p.activo,
        "estado": p.activo,
        "imagen": imagen_url,
        "galeria_urls": _galeria_urls_producto(p),
        "imagenes_adicionales": imagenes_adicionales,
        "proveedor": p.proveedor.nombre if p.proveedor_id else "",
        "categoria": p.categoria or "",
        "marca": p.marca or "",
        "color": p.color or "",
        "descripcion": p.descripcion or "",
        "costo_unitario": costo_f,
        "precio_venta": precio_venta_f,
        "precio_promocion": float(p.precio_promocion) if p.precio_promocion is not None else None,
        "fecha_fin_promocion": (
            p.fecha_fin_promocion.isoformat() if p.fecha_fin_promocion else None
        ),
        "promocion_activa": bool(getattr(p, "promocion_activa", False)),
        "precio_base": float(precio_base) if precio_base is not None else 0,
        "precio": float(precio_publico) if precio_publico is not None else 0,
        "margen_pct": margen_pct,
        "stock_inicial": int(getattr(p, "stock_inicial", 0) or 0),
        "caracteristica": {
            "categoria": p.categoria or "",
            "marca": p.marca or "",
            "color": p.color or "",
            "descripcion": p.descripcion or "",
            "precioCompra": str(p.costo_unitario),
            "precioVenta": str(p.precio_venta) if p.precio_venta is not None else None,
        },
    }


def proveedor_modal_dict(p: Proveedor) -> dict:
    return {
        "id": p.id,
        "identificacion": p.identificacion,
        "nombre": p.nombre,
        "telefono": p.telefono,
        "correo": p.correo_electronico,
        "empresa": p.empresa or "",
        "estado": p.activo,
    }


def validar_nombre_persona(val: str) -> bool:
    val = (val or "").strip()
    if len(val) < 2:
        return False
    return bool(NOMBRE_PERSONA_RE.match(val))


def decimal_desde_post(val: str | None) -> Decimal | None:
    if val is None:
        return None
    s = str(val).strip().replace(",", ".")
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def normalizar_nombre_catalogo(s: str) -> str:
    return " ".join((s or "").strip().split())


def categorias_alta_permitidas() -> set[str]:
    base = set(PRODUCTO_CATEGORIAS_ALTA_WEB)
    extras = set(
        ProductoCatalogoExtra.objects.filter(tipo=ProductoCatalogoExtra.Tipo.CATEGORIA).values_list(
            "nombre", flat=True
        )
    )
    return base | extras


def marcas_alta_permitidas() -> set[str]:
    base = set(PRODUCTO_MARCAS_ALTA_WEB)
    extras = set(
        ProductoCatalogoExtra.objects.filter(tipo=ProductoCatalogoExtra.Tipo.MARCA).values_list(
            "nombre", flat=True
        )
    )
    return base | extras


def redirect_inventario_tab_marcas():
    return redirect(reverse("web_admin_inventario") + "?tab=marcas")
