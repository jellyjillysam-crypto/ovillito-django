"""Rutas principales del proyecto Ovillito."""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as servir_media

from cuentas import views as cuentas_views
from tienda import views as tienda_views

admin.site.site_header = "Ovillito · Administración avanzada"
admin.site.site_title = "Ovillito"
admin.site.index_title = "Gestión de datos"

urlpatterns = [
    # Punto de entrada: siempre pasa por el login y luego redirige según el rol.
    path("", cuentas_views.inicio, name="inicio"),
    path("cuentas/", include("cuentas.urls")),
    path("tienda/", include("tienda.urls")),
    path("actividades/", include("actividades.urls")),
    path("panel/", include("panel.urls")),
    path("marca/", tienda_views.identidad, name="identidad"),
    path("django-admin/", admin.site.urls),
]

# Imágenes y archivos subidos (fotos de productos, videos, etc.). Se sirven también
# en producción porque Render no tiene un servidor de archivos aparte.
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", servir_media, {"document_root": settings.MEDIA_ROOT}),
]
