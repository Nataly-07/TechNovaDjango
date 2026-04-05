"""
Umbrales oficiales de stock (inventario, badges, KPIs, filtros rápidos, notificaciones).

- Agotado: stock == 0 (producto activo).
- Bajo: 1 <= stock <= STOCK_BAJO_MAX
- Medio: STOCK_MEDIO_MIN <= stock <= STOCK_MEDIO_MAX
- Alto: stock >= STOCK_ALTO_MIN
"""

from __future__ import annotations

from django.db.models import Q

STOCK_BAJO_MAX = 7
STOCK_MEDIO_MIN = 8
STOCK_MEDIO_MAX = 20
STOCK_ALTO_MIN = 21

# Valores de ?nivel_stock= en inventario admin
NIVEL_AGOTADO = "agotado"
NIVEL_BAJO = "bajo"


def q_filtro_listado_nivel_stock(nivel: str) -> Q | None:
    """Filtro para el listado paginado (misma regla que las tarjetas KPI)."""
    n = (nivel or "").strip().lower()
    if n in (NIVEL_AGOTADO, "agotados"):
        return Q(activo=True, stock=0)
    if n in (NIVEL_BAJO, "bajo_stock"):
        return Q(activo=True, stock__gte=1, stock__lte=STOCK_BAJO_MAX)
    return None


def normalizar_nivel_stock_param(nivel: str) -> str:
    """Devuelve '' o un valor canónico para plantillas y enlaces."""
    n = (nivel or "").strip().lower()
    if n in (NIVEL_AGOTADO, "agotados"):
        return NIVEL_AGOTADO
    if n in (NIVEL_BAJO, "bajo_stock"):
        return NIVEL_BAJO
    return ""
