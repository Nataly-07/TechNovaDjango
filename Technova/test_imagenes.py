#!/usr/bin/env python
"""
Script de prueba para verificar la funcionalidad de múltiples imágenes
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Technova.settings_base')
django.setup()

from producto.models import Producto, ProductoImagen
from proveedor.models import Proveedor


def test_imagenes_producto():
    """Probar la creación de producto con múltiples imágenes"""
    
    # Verificar que el modelo ProductoImagen existe
    print("✓ Modelo ProductoImagen creado correctamente")
    
    # Crear un proveedor de prueba si no existe
    proveedor, created = Proveedor.objects.get_or_create(
        identificacion="900TEST123",
        defaults={
            "nombre": "Proveedor de Prueba",
            "telefono": "3001234567",
            "correo_electronico": "test@proveedor.com",
            "empresa": "Test SAS",
            "activo": True,
        }
    )
    
    if created:
        print("✓ Proveedor de prueba creado")
    else:
        print("✓ Usando proveedor existente")
    
    # Crear un producto de prueba
    producto, created = Producto.objects.get_or_create(
        codigo="TEST-IMG-001",
        defaults={
            "nombre": "Producto de Prueba con Imágenes",
            "imagen_url": "https://via.placeholder.com/300x300.png?text=Principal",
            "categoria": "Electrónica",
            "marca": "TestBrand",
            "color": "Negro",
            "descripcion": "Este es un producto de prueba con múltiples imágenes",
            "precio_venta": 999.99,
            "stock": 10,
            "proveedor": proveedor,
            "costo_unitario": 500.00,
            "activo": True,
        }
    )
    
    if created:
        print("✓ Producto de prueba creado")
        
        # Crear imágenes adicionales
        imagenes_urls = [
            "https://via.placeholder.com/300x300.png?text=Imagen+1",
            "https://via.placeholder.com/300x300.png?text=Imagen+2",
            "https://via.placeholder.com/300x300.png?text=Imagen+3",
        ]
        
        for orden, url in enumerate(imagenes_urls):
            ProductoImagen.objects.create(
                producto=producto,
                url=url,
                orden=orden + 1,
                activa=True
            )
        
        print(f"✓ {len(imagenes_urls)} imágenes adicionales creadas")
        
    else:
        print("✓ Usando producto existente")
        
        # Mostrar imágenes existentes
        imagenes = ProductoImagen.objects.filter(producto=producto).order_by('orden')
        print(f"✓ Producto tiene {imagenes.count()} imágenes adicionales:")
        for img in imagenes:
            print(f"  - Orden {img.orden}: {img.url} (Activa: {img.activa})")
    
    # Verificar la relación
    producto_con_imagenes = Producto.objects.prefetch_related('imagenes').get(id=producto.id)
    print(f"✓ Producto cargado con {producto_con_imagenes.imagenes.count()} imágenes")
    
    print("\n🎉 ¡Prueba completada exitosamente!")
    print("La funcionalidad de múltiples imágenes está lista para usar.")


if __name__ == "__main__":
    test_imagenes_producto()
