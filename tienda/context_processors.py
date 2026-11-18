from django.conf import settings

from cuentas.permisos import es_admin

from .models import Categoria


def global_tienda(request):
    """Datos disponibles en todas las plantillas (marca, tienda, carrito, menú)."""
    contexto = {
        "MARCA": settings.MARCA,
        "TIENDA": settings.TIENDA,
        "es_admin": es_admin(getattr(request, "user", None)),
    }
    if getattr(request, "user", None) and request.user.is_authenticated:
        carrito = request.session.get("carrito") or {}
        contexto["carrito_cantidad"] = sum(int(c) for c in carrito.values()) if isinstance(carrito, dict) else 0
        contexto["menu_categorias"] = Categoria.objects.all()
    return contexto
