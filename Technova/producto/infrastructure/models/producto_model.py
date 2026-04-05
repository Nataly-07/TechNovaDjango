from django.db import models
from django.utils import timezone


class Producto(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=120)
    imagen_url = models.URLField(blank=True, max_length=500)
    categoria = models.CharField(max_length=120, blank=True, default="")
    marca = models.CharField(max_length=120, blank=True, default="")
    color = models.CharField(max_length=40, blank=True, default="")
    descripcion = models.TextField(blank=True, default="")
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    precio_promocion = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    fecha_fin_promocion = models.DateTimeField(null=True, blank=True)
    stock = models.PositiveIntegerField(
        "stock actual",
        default=0,
        help_text="Inventario disponible: baja con ventas y sube con compras u ajustes.",
    )
    stock_inicial = models.PositiveIntegerField(
        "stock inicial",
        default=0,
        editable=False,
        help_text="Fijo desde el alta (Excel o manual). No cambia con ventas ni con edición de ficha.",
    )
    proveedor = models.ForeignKey(
        "proveedor.Proveedor",
        on_delete=models.PROTECT,
        related_name="productos",
    )
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "productos"
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ["-creado_en", "-id"]

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nombre}"

    @property
    def stock_actual(self) -> int:
        """Alias de `stock`: cantidad operativa actual en Technova."""
        return int(self.stock)

    @property
    def promocion_activa(self) -> bool:
        return bool(
            self.precio_promocion is not None
            and self.fecha_fin_promocion is not None
            and self.fecha_fin_promocion > timezone.now()
        )

    @property
    def precio_base(self):
        return self.precio_venta if self.precio_venta is not None else self.costo_unitario

    @property
    def precio_publico(self):
        return self.precio_promocion if self.promocion_activa else self.precio_base
