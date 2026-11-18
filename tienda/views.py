import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from cuentas.permisos import es_admin

from .carrito import Carrito
from .models import ILUSTRACIONES, Categoria, ItemPedido, Pedido, Producto, Slide

ORDENES = {
    "vendidos": ("Más vendidos", ["-unidades_vendidas", "-creado"]),
    "nuevos": ("Más nuevos", ["-creado"]),
    "precio_asc": ("Precio: menor a mayor", ["precio", "nombre"]),
    "precio_desc": ("Precio: mayor a menor", ["-precio", "nombre"]),
    "nombre": ("Nombre A–Z", ["nombre"]),
}

RANGOS_PRECIO = {
    "hasta-30": ("Hasta $30.000", None, 30000),
    "30-60": ("$30.000 – $60.000", 30000, 60000),
    "60-100": ("$60.000 – $100.000", 60000, 100000),
    "mas-100": ("Más de $100.000", 100000, None),
}


def _es_fetch(request):
    return request.headers.get("x-requested-with") == "fetch"


def _volver(request, defecto="tienda:carrito"):
    destino = request.META.get("HTTP_REFERER")
    if destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        return redirect(destino)
    return redirect(defecto)


def _leer_cantidad(request, defecto=1):
    valor = request.POST.get("cantidad")
    if valor is None and request.content_type == "application/json":
        try:
            valor = json.loads(request.body or b"{}").get("cantidad")
        except (ValueError, AttributeError):
            valor = None
    try:
        return max(0, min(99, int(valor)))
    except (TypeError, ValueError):
        return defecto


# --- Home de clientes ------------------------------------------------------
@login_required
def home(request):
    productos = Producto.objects.activos().select_related("categoria").con_ventas()

    q = request.GET.get("q", "").strip()
    if q:
        productos = productos.filter(
            Q(nombre__icontains=q) | Q(descripcion__icontains=q) | Q(categoria__nombre__icontains=q)
        )

    categoria_actual = None
    if request.GET.get("categoria"):
        categoria_actual = Categoria.objects.filter(slug=request.GET["categoria"]).first()
        if categoria_actual:
            productos = productos.filter(categoria=categoria_actual)

    precio = request.GET.get("precio", "")
    if precio in RANGOS_PRECIO:
        _, minimo, maximo = RANGOS_PRECIO[precio]
        if minimo is not None:
            productos = productos.filter(precio__gte=minimo)
        if maximo is not None:
            productos = productos.filter(precio__lte=maximo)

    disponibilidad = request.GET.get("disponible", "")
    if disponibilidad == "si":
        productos = productos.filter(stock__gt=0)

    orden = request.GET.get("orden", "vendidos")
    if orden not in ORDENES:
        orden = "vendidos"
    productos = productos.order_by(*ORDENES[orden][1])

    return render(request, "tienda/home.html", {
        "slides": Slide.objects.filter(activo=True),
        "productos": productos,
        "categorias": Categoria.objects.all(),
        "categoria_actual": categoria_actual,
        "ordenes": [(k, v[0]) for k, v in ORDENES.items()],
        "orden": orden,
        "rangos": [(k, v[0]) for k, v in RANGOS_PRECIO.items()],
        "precio": precio,
        "disponibilidad": disponibilidad,
        "q": q,
        "hay_filtros": bool(q or categoria_actual or precio or disponibilidad),
    })


@login_required
def producto_detalle(request, slug):
    producto = get_object_or_404(Producto.objects.select_related("categoria"), slug=slug, activo=True)
    relacionados = (Producto.objects.activos().filter(categoria=producto.categoria)
                    .exclude(pk=producto.pk)[:4])
    return render(request, "tienda/producto.html", {"producto": producto, "relacionados": relacionados})


# --- Carrito (API JSON usada por el panel lateral) -------------------------
@login_required
def carrito_api(request):
    return JsonResponse(Carrito(request).como_json())


@login_required
@require_POST
def carrito_agregar(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id, activo=True)
    carrito = Carrito(request)
    if not producto.disponible:
        mensaje = f"«{producto.nombre}» está agotado por ahora."
        if _es_fetch(request):
            return JsonResponse({**carrito.como_json(), "error": mensaje}, status=409)
        messages.error(request, mensaje)
        return _volver(request)

    antes = int(carrito.datos.get(str(producto.pk), 0))
    despues = carrito.agregar(producto, _leer_cantidad(request) or 1)
    if despues == antes:
        mensaje, nivel = f"Ya tienes todas las unidades disponibles de «{producto.nombre}».", "aviso"
    else:
        mensaje, nivel = f"«{producto.nombre}» se agregó a tu carrito.", "exito"
    if _es_fetch(request):
        return JsonResponse({**carrito.como_json(), "mensaje": mensaje, "nivel": nivel})
    messages.success(request, mensaje)
    return _volver(request)


@login_required
@require_POST
def carrito_actualizar(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    carrito = Carrito(request)
    carrito.actualizar(producto, _leer_cantidad(request, defecto=0))
    if _es_fetch(request):
        return JsonResponse(carrito.como_json())
    return redirect("tienda:carrito")


@login_required
@require_POST
def carrito_eliminar(request, producto_id):
    carrito = Carrito(request)
    carrito.eliminar(producto_id)
    if _es_fetch(request):
        return JsonResponse(carrito.como_json())
    messages.info(request, "Producto eliminado del carrito.")
    return redirect("tienda:carrito")


@login_required
@require_POST
def carrito_nota(request):
    carrito = Carrito(request)
    carrito.nota = request.POST.get("nota", "")
    return JsonResponse({"ok": True, "nota": carrito.nota})


@login_required
def carrito_pagina(request):
    carrito = Carrito(request)
    items = carrito.items()
    subtotal = carrito.subtotal(items)
    envio = carrito.envio(subtotal)
    return render(request, "tienda/carrito.html", {
        "items": items,
        "subtotal": subtotal,
        "envio": envio,
        "total": subtotal + envio,
        "nota": carrito.nota,
        "falta_envio_gratis": max(0, settings.TIENDA["envio_gratis_desde"] - subtotal),
    })


@login_required
@require_POST
def checkout(request):
    carrito = Carrito(request)
    if "nota" in request.POST:
        carrito.nota = request.POST.get("nota", "")
    items = carrito.items()
    if not items:
        messages.warning(request, "Tu carrito está vacío.")
        return redirect("tienda:carrito")

    with transaction.atomic():
        ids = [i["producto"].pk for i in items]
        productos = {p.pk: p for p in Producto.objects.select_for_update().filter(pk__in=ids)}
        for item in items:
            producto = productos[item["producto"].pk]
            if item["cantidad"] > producto.stock:
                messages.error(
                    request,
                    f"Solo quedan {producto.stock} unidades de «{producto.nombre}». Ajusta la cantidad.",
                )
                return redirect("tienda:carrito")

        subtotal = sum(productos[i["producto"].pk].precio * i["cantidad"] for i in items)
        envio = carrito.envio(subtotal)
        pedido = Pedido.objects.create(
            usuario=request.user, subtotal=subtotal, envio=envio,
            total=subtotal + envio, nota=carrito.nota,
        )
        for item in items:
            producto = productos[item["producto"].pk]
            ItemPedido.objects.create(
                pedido=pedido, producto=producto, nombre=producto.nombre,
                precio=producto.precio, cantidad=item["cantidad"],
            )
            producto.stock -= item["cantidad"]
            producto.save(update_fields=["stock"])

    carrito.limpiar()
    messages.success(request, "¡Pedido confirmado! Ya estamos preparando tus tejidos.")
    return redirect("tienda:pedido", pk=pedido.pk)


@login_required
def pedido_detalle(request, pk):
    pedido = get_object_or_404(Pedido.objects.prefetch_related("items"), pk=pk)
    if pedido.usuario_id != request.user.id and not es_admin(request.user):
        raise PermissionDenied
    return render(request, "tienda/pedido.html", {"pedido": pedido})


@login_required
def mis_pedidos(request):
    pedidos = request.user.pedidos.prefetch_related("items")
    return render(request, "tienda/mis_pedidos.html", {"pedidos": pedidos})


# --- Identidad de marca ----------------------------------------------------
PALETA = [
    {"nombre": "Chocolate", "hex": "#4A2812", "var": "--chocolate", "uso": "Logotipo, textos fuertes y fondos de contraste.", "texto": "claro"},
    {"nombre": "Crema", "hex": "#FFF6DE", "var": "--crema", "uso": "Fondo principal: cálido y suave como el algodón.", "texto": "oscuro"},
    {"nombre": "Mantequilla", "hex": "#FFD966", "var": "--mantequilla", "uso": "Botones de acción, banners y destacados.", "texto": "oscuro"},
    {"nombre": "Verde bosque", "hex": "#1F5C3F", "var": "--verde", "uso": "Títulos, enlaces e íconos de navegación.", "texto": "claro"},
    {"nombre": "Rosa algodón", "hex": "#F4B6C2", "var": "--rosa", "uso": "Acentos tiernos, mejillas y etiquetas.", "texto": "oscuro"},
    {"nombre": "Celeste cielo", "hex": "#A8D5EA", "var": "--celeste", "uso": "Fondos secundarios e ilustraciones.", "texto": "oscuro"},
    {"nombre": "Caramelo", "hex": "#C9803A", "var": "--caramelo", "uso": "Detalles cálidos y amigurumis.", "texto": "claro"},
]

TIPOGRAFIAS = [
    {"nombre": "Fraunces", "clase": "fuente-titulos", "rol": "Títulos y precios",
     "descripcion": "Serif suave y redondeada, con personalidad artesanal. Transmite calidez y tradición.",
     "pesos": "SemiBold 600 · Bold 700 · Italic"},
    {"nombre": "Nunito", "clase": "fuente-texto", "rol": "Textos y botones",
     "descripcion": "Sans-serif de terminaciones redondas, muy legible en pantallas pequeñas.",
     "pesos": "Regular 400 · SemiBold 600 · Bold 700 · ExtraBold 800"},
    {"nombre": "Gochi Hand", "clase": "fuente-mano", "rol": "Acentos manuscritos",
     "descripcion": "Letra a mano alzada para títulos de campaña, como una nota escrita por la tejedora.",
     "pesos": "Regular 400"},
]


@login_required
def identidad(request):
    return render(request, "tienda/identidad.html", {
        "paleta": PALETA,
        "tipografias": TIPOGRAFIAS,
        "ilustraciones": ILUSTRACIONES,
    })
