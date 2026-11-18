from django import template
from django.templatetags.static import static

register = template.Library()


@register.filter
def pesos(valor):
    """Formatea un entero como precio: 125000 -> $125.000"""
    try:
        numero = int(round(float(valor)))
    except (TypeError, ValueError):
        return valor
    signo = "-" if numero < 0 else ""
    return f"{signo}${abs(numero):,}".replace(",", ".")


@register.filter
def km(valor):
    """Distancia legible: 0.42 -> 420 m · 3.456 -> 3,5 km"""
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return "—"
    if valor < 1:
        return f"{round(valor * 1000)} m"
    return f"{valor:.1f} km".replace(".", ",")


@register.simple_tag
def figura(nombre):
    """Ruta de una figura transparente (para el carrusel y decoraciones)."""
    return static(f"img/figuras/{nombre}.svg")


@register.inclusion_tag("includes/icono.html")
def icono(nombre, clase=""):
    return {"nombre": nombre, "clase": clase}


@register.simple_tag(takes_context=True)
def url_con(context, **cambios):
    """Conserva los parámetros GET actuales y reemplaza/añade los indicados."""
    params = context["request"].GET.copy()
    for clave, valor in cambios.items():
        if valor in (None, ""):
            params.pop(clave, None)
        else:
            params[clave] = valor
    return "?" + params.urlencode() if params else "?"
