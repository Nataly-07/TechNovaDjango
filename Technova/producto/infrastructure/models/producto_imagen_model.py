from django.db import models


class ProductoImagen(models.Model):
    """Imágenes adicionales para un producto."""
    
    producto = models.ForeignKey(
        "producto.Producto",
        on_delete=models.CASCADE,
        related_name="imagenes"
    )
    url = models.URLField(max_length=500)
    orden = models.PositiveIntegerField(default=0)
    activa = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "producto_imagenes"
        verbose_name = "imagen de producto"
        verbose_name_plural = "imágenes de productos"
        ordering = ["orden", "id"]
        unique_together = [["producto", "orden"]]
    
    def __str__(self) -> str:
        return f"Imagen {self.orden} de {self.producto.nombre}"
