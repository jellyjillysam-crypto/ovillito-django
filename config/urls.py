"""Rutas principales del proyecto Ovillito."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

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

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
