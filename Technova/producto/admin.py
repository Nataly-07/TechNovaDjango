from django.contrib import admin

from producto.models import Producto, ProductoImagen


class ProductoImagenInline(admin.TabularInline):
    model = ProductoImagen
    extra = 1
    fields = ['url', 'orden', 'activa']
    ordering = ['orden']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'categoria', 'marca', 'stock', 'precio_venta', 'activo']
    list_filter = ['categoria', 'marca', 'activo']
    search_fields = ['codigo', 'nombre', 'descripcion']
    readonly_fields = ['creado_en', 'actualizado_en']
    inlines = [ProductoImagenInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo', 'nombre', 'proveedor')
        }),
        ('Detalles del Producto', {
            'fields': ('categoria', 'marca', 'color', 'descripcion')
        }),
        ('Precios e Inventario', {
            'fields': ('costo_unitario', 'precio_venta', 'stock')
        }),
        ('Multimedia', {
            'fields': ('imagen_url',)
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Fechas', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProductoImagen)
class ProductoImagenAdmin(admin.ModelAdmin):
    list_display = ['producto', 'url_preview', 'orden', 'activa', 'creado_en']
    list_filter = ['activa', 'creado_en']
    search_fields = ['producto__nombre', 'producto__codigo']
    ordering = ['producto', 'orden']
    
    def url_preview(self, obj):
        if obj.url:
            return f'<img src="{obj.url}" width="50" height="50" style="object-fit: cover;" />'
        return "Sin imagen"
    url_preview.short_description = 'Vista previa'
    url_preview.allow_tags = True
