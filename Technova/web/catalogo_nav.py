"""Listas de categorías/marcas y tarjetas de producto para index público e inicio cliente."""

from producto.models import Producto


def _capitalize_catalogo(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return s
    return s[0].upper() + s[1:].lower() if len(s) > 1 else s.upper()


def listas_categorias_marcas_publicas():
    """Menús del index / nav (sin rutas /categoria/ en Django)."""
    qs = Producto.objects.filter(activo=True)
    cats = sorted(
        {
            _capitalize_catalogo(c)
            for c in qs.exclude(categoria__exact="").values_list("categoria", flat=True).distinct()
            if c and c.strip() and c.strip().lower() != "temporal"
        }
    )
    marcas = sorted(
        {
            _capitalize_catalogo(m)
            for m in qs.exclude(marca__exact="").values_list("marca", flat=True).distinct()
            if m and m.strip() and m.strip().lower() != "temporal"
        }
    )
    return cats, marcas


def _precio_tarjeta_index(p: Producto):
    """
    Valores SSR para tarjetas de catálogo (tachado + promoción resaltada).
    """
    base = p.precio_venta if p.precio_venta is not None else p.costo_unitario
    if base is None:
        return None, None, None

    base = float(base)
    if getattr(p, "promocion_activa", False) and getattr(p, "precio_promocion", None):
        promo = float(p.precio_promocion)
        if promo > 0 and promo < base:
            pct = (base - promo) * 100.0 / base
            return base, promo, int(round(pct))

    return None, base, None


def _imagen_producto_publica(p: Producto) -> str:
    img = (p.imagen_url or "").strip()
    if not img:
        return "/static/frontend/imagenes/placeholder.svg"
    if img.startswith("http://") or img.startswith("https://"):
        return img
    if img.startswith("/"):
        return img
    return f"/static/frontend/imagenes/{img}"


def producto_card_ctx(p: Producto) -> dict:
    po, pd, descuento_pct = _precio_tarjeta_index(p)
    return {
        "id": p.id,
        "nombre": p.nombre,
        "imagen": _imagen_producto_publica(p),
        "stock": p.stock or 0,
        "precio_original": po,
        "precio_descuento": pd,
        "descuento_pct": descuento_pct,
    }


def ctx_catalogo_index():
    """Mismo contexto de tarjetas que `index_public` para `home` autenticado."""
    from web.application.catalogo_publico_service import fetch_productos_recientes

    productos_qs = Producto.objects.filter(activo=True).order_by("id")
    productos_cards = [producto_card_ctx(p) for p in productos_qs[:24]]
    productos_recientes = [producto_card_ctx(p) for p in fetch_productos_recientes()]
    oferta_dia = productos_cards[0] if productos_cards else None
    ofertas_interes = productos_cards[:3]
    return {
        "productos": productos_cards,
        "productos_recientes": productos_recientes,
        "oferta_dia": oferta_dia,
        "ofertas_interes": ofertas_interes,
    }
