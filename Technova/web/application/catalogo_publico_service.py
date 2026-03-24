from producto.models import Producto


def capitalize_catalogo(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return s
    return s[0].upper() + s[1:].lower() if len(s) > 1 else s.upper()


def listas_categorias_marcas_publicas():
    """Listas para menús del index (sin rutas /categoria/ en Django)."""
    qs = Producto.objects.filter(activo=True)
    cats = sorted(
        {
            capitalize_catalogo(c)
            for c in qs.exclude(categoria__exact="").values_list("categoria", flat=True).distinct()
            if c and c.strip() and c.strip().lower() != "temporal"
        }
    )
    marcas = sorted(
        {
            capitalize_catalogo(m)
            for m in qs.exclude(marca__exact="").values_list("marca", flat=True).distinct()
            if m and m.strip() and m.strip().lower() != "temporal"
        }
    )
    return cats, marcas


def precio_tarjeta_index(p: Producto):
    base = p.precio_venta if p.precio_venta is not None else p.costo_unitario
    if base is None:
        return None, None
    d = float(base)
    o = round(d * 1.05)
    return o, d


def imagen_producto_publica(p: Producto) -> str:
    img = (p.imagen_url or "").strip()
    if not img:
        return "/static/frontend/imagenes/placeholder.svg"
    if img.startswith("http://") or img.startswith("https://"):
        return img
    if img.startswith("/"):
        return img
    return f"/static/frontend/imagenes/{img}"


def producto_card_ctx(p: Producto) -> dict:
    po, pd = precio_tarjeta_index(p)
    return {
        "id": p.id,
        "nombre": p.nombre,
        "imagen": imagen_producto_publica(p),
        "stock": p.stock or 0,
        "precio_original": po,
        "precio_descuento": pd,
    }
