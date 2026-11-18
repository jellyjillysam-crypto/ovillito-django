"""
Control de acceso por rol.

El proyecto maneja dos tipos de usuario:
  * Administrador: usuario con ``is_staff=True``. Su home es el panel de métricas.
  * Cliente: cualquier otro usuario registrado. Su home es la tienda.
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.shortcuts import resolve_url

ROL_ADMIN = "admin"
ROL_CLIENTE = "cliente"


def es_admin(usuario):
    return bool(usuario and usuario.is_authenticated and usuario.is_staff)


def correo_es_admin(correo):
    return bool(correo) and correo.strip().lower() in settings.ADMIN_EMAILS


def sincronizar_admin(usuario):
    """Otorga o retira el rol de administrador según la lista ADMIN_EMAILS.

    Si la lista está vacía no se toca nada (así no se pierden admins creados
    por consola). Los superusuarios nunca pierden el acceso.
    """
    if not settings.ADMIN_EMAILS or usuario.is_superuser:
        return
    debe = correo_es_admin(usuario.email)
    if usuario.is_staff != debe:
        usuario.is_staff = debe
        usuario.save(update_fields=["is_staff"])


def rol_de(usuario):
    return ROL_ADMIN if es_admin(usuario) else ROL_CLIENTE


def home_por_rol(usuario):
    """URL del home que corresponde al rol del usuario."""
    if es_admin(usuario):
        return resolve_url("panel:dashboard")
    return resolve_url("tienda:home")


def admin_requerido(vista):
    """Exige sesión iniciada y rol administrador (responde 403 si es cliente)."""
    @login_required
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not es_admin(request.user):
            raise PermissionDenied("Esta sección es solo para administradores.")
        return vista(request, *args, **kwargs)
    return envoltura


class AdminRequeridoMixin(LoginRequiredMixin):
    """Versión para vistas basadas en clases."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not es_admin(request.user):
            raise PermissionDenied("Esta sección es solo para administradores.")
        return super().dispatch(request, *args, **kwargs)
