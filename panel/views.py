"""Home del administrador (métricas) y gestión (CRUD) de productos, blog y videos."""
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Avg, Count, F, Q, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from actividades.forms import EntradaBlogForm, VideoForm
from actividades.models import (Comentario, EntradaBlog, Foto, MensajeChat,
                                RespuestaEncuesta, Ubicacion, Video)
from cuentas.permisos import AdminRequeridoMixin, admin_requerido
from django.db.models import ProtectedError

from tienda.forms import CategoriaForm, ProductoForm
from tienda.models import Categoria, ItemPedido, Pedido, Producto


def _variacion(actual, anterior):
    if not anterior:
        return None
    return round((actual - anterior) * 100 / anterior)


def _ultimas_ubicaciones():
    """Última ubicación registrada por cada cliente."""
    vistos, resultado = set(), []
    for u in Ubicacion.objects.select_related("usuario").filter(usuario__is_staff=False):
        if u.usuario_id in vistos:
            continue
        vistos.add(u.usuario_id)
        resultado.append(u)
    return resultado


@admin_requerido
def dashboard(request):
    ahora = timezone.localtime()
    hoy = ahora.date()

    pedidos = Pedido.objects.all()
    ingresos = pedidos.aggregate(t=Coalesce(Sum("total"), 0))["t"]
    num_pedidos = pedidos.count()
    num_clientes = User.objects.filter(is_staff=False).count()
    clientes_nuevos = User.objects.filter(is_staff=False, date_joined__gte=ahora - timedelta(days=30)).count()

    # Comparación de los últimos 7 días contra los 7 anteriores.
    hace7, hace14 = ahora - timedelta(days=7), ahora - timedelta(days=14)
    ingresos_7 = pedidos.filter(creado__gte=hace7).aggregate(t=Coalesce(Sum("total"), 0))["t"]
    ingresos_prev = pedidos.filter(creado__gte=hace14, creado__lt=hace7).aggregate(t=Coalesce(Sum("total"), 0))["t"]
    pedidos_7 = pedidos.filter(creado__gte=hace7).count()
    pedidos_prev = pedidos.filter(creado__gte=hace14, creado__lt=hace7).count()

    # Serie diaria de ingresos (14 días).
    inicio = hoy - timedelta(days=13)
    por_dia = {
        fila["dia"]: fila
        for fila in pedidos.filter(creado__date__gte=inicio)
        .annotate(dia=TruncDate("creado")).values("dia")
        .annotate(total=Sum("total"), n=Count("id"))
    }
    serie_dias = []
    for i in range(14):
        dia = inicio + timedelta(days=i)
        fila = por_dia.get(dia, {})
        serie_dias.append({
            "etiqueta": dia.strftime("%d/%m"),
            "total": fila.get("total") or 0,
            "pedidos": fila.get("n") or 0,
        })

    por_categoria = list(
        ItemPedido.objects.filter(producto__isnull=False)
        .values(categoria=F("producto__categoria__nombre"))
        .annotate(unidades=Sum("cantidad"), ingresos=Sum(F("precio") * F("cantidad")))
        .order_by("-unidades")
    )
    top_productos = (Producto.objects.con_ventas().filter(unidades_vendidas__gt=0)
                     .select_related("categoria").order_by("-unidades_vendidas")[:5])
    stock_bajo = Producto.objects.activos().filter(stock__lte=3).order_by("stock")[:6]

    # Encuesta.
    respuestas = RespuestaEncuesta.objects.all()
    total_resp = respuestas.count()
    promedio = respuestas.aggregate(p=Avg("calificacion"))["p"] or 0
    conteo_calif = dict(respuestas.values_list("calificacion").annotate(n=Count("id")))
    calificaciones = [{"etiqueta": f"{i} ★", "valor": conteo_calif.get(i, 0)} for i in range(1, 6)]
    # Nombres cortos para que las etiquetas del eje no se recorten.
    nombres_canal = {"instagram": "Instagram", "tiktok": "TikTok", "amigos": "Amigos",
                     "feria": "Feria", "google": "Google", "otro": "Otro"}
    canales = [
        {"etiqueta": nombres_canal.get(f["canal"], f["canal"]), "valor": f["n"]}
        for f in respuestas.values("canal").annotate(n=Count("id")).order_by("-n")
    ]
    conteo_rec = dict(respuestas.values_list("recomendaria").annotate(n=Count("id")))
    recomendaria = []
    for clave, etiqueta in RespuestaEncuesta.RECOMENDARIA:
        n = conteo_rec.get(clave, 0)
        recomendaria.append({
            "clave": clave, "etiqueta": etiqueta, "valor": n,
            "porcentaje": round(n * 100 / total_resp) if total_resp else 0,
        })

    # Ubicaciones de clientes.
    ultimas = _ultimas_ubicaciones()
    distancia_prom = sum(u.distancia_km for u in ultimas) / len(ultimas) if ultimas else None
    cerca = sum(1 for u in ultimas if u.distancia_km <= 3)
    puntos = [
        {"lat": u.latitud, "lng": u.longitud, "nombre": u.usuario.get_full_name() or u.usuario.username,
         "distancia": round(u.distancia_km, 2)}
        for u in ultimas
    ]

    return render(request, "panel/dashboard.html", {
        "seccion": "dashboard",
        "kpi": {
            "ingresos": ingresos,
            "ingresos_7": ingresos_7,
            "ingresos_var": _variacion(ingresos_7, ingresos_prev),
            "pedidos": num_pedidos,
            "pedidos_7": pedidos_7,
            "pedidos_var": _variacion(pedidos_7, pedidos_prev),
            "clientes": num_clientes,
            "clientes_nuevos": clientes_nuevos,
            "ticket": round(ingresos / num_pedidos) if num_pedidos else 0,
            "calificacion": promedio,
            "respuestas": total_resp,
            "distancia": distancia_prom,
            "clientes_cerca": cerca,
            "con_ubicacion": len(ultimas),
        },
        "actividad": {
            "mensajes": MensajeChat.objects.count(),
            "comentarios": Comentario.objects.count(),
            "fotos": Foto.objects.count(),
            "videos": Video.objects.count(),
            "entradas": EntradaBlog.objects.count(),
            "productos": Producto.objects.activos().count(),
        },
        "graficas": {
            "dias": serie_dias,
            "categorias": [{"etiqueta": c["categoria"], "valor": c["unidades"], "ingresos": c["ingresos"]}
                           for c in por_categoria],
            "calificaciones": calificaciones,
            "canales": canales,
        },
        "recomendaria": recomendaria,
        "serie_dias": serie_dias,
        "por_categoria": por_categoria,
        "top_productos": top_productos,
        "stock_bajo": stock_bajo,
        "ultimos_pedidos": pedidos.select_related("usuario")[:6],
        "mapa_datos": {"puntos": puntos},
    })


# --- Utilidades comunes de CRUD ---------------------------------------------
class PanelMixin(AdminRequeridoMixin):
    seccion = ""
    titulo = ""
    lista_url = ""

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update({
            "seccion": self.seccion,
            "titulo": self.titulo,
            "volver_url": reverse(self.lista_url) if self.lista_url else None,
        })
        return contexto

    def get_success_url(self):
        return reverse(self.lista_url)


class EliminarMixin(PanelMixin):
    template_name = "panel/confirmar_eliminar.html"
    mensaje_eliminado = "Elemento eliminado."

    def form_valid(self, form):
        nombre = str(self.object)
        respuesta = super().form_valid(form)
        messages.success(self.request, self.mensaje_eliminado.format(nombre=nombre))
        return respuesta


# --- CRUD de productos -------------------------------------------------------
class ProductoLista(PanelMixin, ListView):
    template_name = "panel/productos_lista.html"
    seccion, titulo = "productos", "Productos"
    paginate_by = 15

    def get_queryset(self):
        qs = Producto.objects.select_related("categoria").con_ventas().order_by("-creado")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(categoria__nombre__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["q"] = self.request.GET.get("q", "")
        return contexto


class ProductoCrear(PanelMixin, SuccessMessageMixin, CreateView):
    model = Producto
    form_class = ProductoForm
    template_name = "panel/formulario.html"
    seccion, titulo, lista_url = "productos", "Nuevo producto", "panel:productos"
    success_message = "Producto «%(nombre)s» creado."


class ProductoEditar(PanelMixin, SuccessMessageMixin, UpdateView):
    model = Producto
    form_class = ProductoForm
    template_name = "panel/formulario.html"
    seccion, titulo, lista_url = "productos", "Editar producto", "panel:productos"
    success_message = "Cambios guardados en «%(nombre)s»."


class ProductoEliminar(EliminarMixin, DeleteView):
    model = Producto
    seccion, titulo, lista_url = "productos", "Eliminar producto", "panel:productos"
    mensaje_eliminado = "Producto «{nombre}» eliminado."


# --- CRUD de categorías ------------------------------------------------------
class CategoriaLista(PanelMixin, ListView):
    template_name = "panel/categorias_lista.html"
    seccion, titulo = "categorias", "Categorías"

    def get_queryset(self):
        return Categoria.objects.annotate(num_productos=Count("productos"))


class CategoriaCrear(PanelMixin, SuccessMessageMixin, CreateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = "panel/formulario.html"
    seccion, titulo, lista_url = "categorias", "Nueva categoría", "panel:categorias"
    success_message = "Categoría «%(nombre)s» creada."


class CategoriaEditar(PanelMixin, SuccessMessageMixin, UpdateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = "panel/formulario.html"
    seccion, titulo, lista_url = "categorias", "Editar categoría", "panel:categorias"
    success_message = "Categoría «%(nombre)s» actualizada."


class CategoriaEliminar(EliminarMixin, DeleteView):
    model = Categoria
    seccion, titulo, lista_url = "categorias", "Eliminar categoría", "panel:categorias"
    mensaje_eliminado = "Categoría «{nombre}» eliminada."

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, "No se puede eliminar: tiene productos. Mueve o elimina esos productos primero.")
            return redirect("panel:categorias")


# --- CRUD del blog -----------------------------------------------------------
class EntradaLista(PanelMixin, ListView):
    template_name = "panel/blog_lista.html"
    seccion, titulo = "blog", "Blog"

    def get_queryset(self):
        return EntradaBlog.objects.select_related("autor").annotate(num_comentarios=Count("comentarios"))


class EntradaCrear(PanelMixin, SuccessMessageMixin, CreateView):
    model = EntradaBlog
    form_class = EntradaBlogForm
    template_name = "panel/formulario.html"
    seccion, titulo, lista_url = "blog", "Nueva entrada del blog", "panel:blog"
    success_message = "Entrada «%(titulo)s» publicada."

    def form_valid(self, form):
        form.instance.autor = self.request.user
        return super().form_valid(form)


class EntradaEditar(PanelMixin, SuccessMessageMixin, UpdateView):
    model = EntradaBlog
    form_class = EntradaBlogForm
    template_name = "panel/formulario.html"
    seccion, titulo, lista_url = "blog", "Editar entrada", "panel:blog"
    success_message = "Entrada «%(titulo)s» actualizada."


class EntradaEliminar(EliminarMixin, DeleteView):
    model = EntradaBlog
    seccion, titulo, lista_url = "blog", "Eliminar entrada", "panel:blog"
    mensaje_eliminado = "Entrada «{nombre}» eliminada."


# --- CRUD de videos ----------------------------------------------------------
class VideoLista(PanelMixin, ListView):
    model = Video
    template_name = "panel/videos_lista.html"
    seccion, titulo = "videos", "Videos"


class VideoCrear(PanelMixin, SuccessMessageMixin, CreateView):
    model = Video
    form_class = VideoForm
    template_name = "panel/formulario.html"
    seccion, titulo, lista_url = "videos", "Nuevo video", "panel:videos"
    success_message = "Video «%(titulo)s» agregado."


class VideoEditar(PanelMixin, SuccessMessageMixin, UpdateView):
    model = Video
    form_class = VideoForm
    template_name = "panel/formulario.html"
    seccion, titulo, lista_url = "videos", "Editar video", "panel:videos"
    success_message = "Video «%(titulo)s» actualizado."


class VideoEliminar(EliminarMixin, DeleteView):
    model = Video
    seccion, titulo, lista_url = "videos", "Eliminar video", "panel:videos"
    mensaje_eliminado = "Video «{nombre}» eliminado."


# --- Pedidos, clientes, encuestas y ubicaciones -------------------------------
@admin_requerido
def pedidos(request):
    lista = Pedido.objects.select_related("usuario").prefetch_related("items")
    estado = request.GET.get("estado", "")
    if estado in dict(Pedido.ESTADOS):
        lista = lista.filter(estado=estado)
    return render(request, "panel/pedidos.html", {
        "seccion": "pedidos", "pedidos": lista[:100], "estados": Pedido.ESTADOS, "estado": estado,
    })


@admin_requerido
@require_POST
def pedido_estado(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    nuevo = request.POST.get("estado")
    if nuevo in dict(Pedido.ESTADOS):
        pedido.estado = nuevo
        pedido.save(update_fields=["estado"])
        messages.success(request, f"{pedido.numero}: estado cambiado a «{pedido.get_estado_display()}».")
    volver = request.POST.get("volver", "")
    if volver and url_has_allowed_host_and_scheme(volver, allowed_hosts={request.get_host()}):
        return redirect(volver)
    return redirect("panel:pedidos")


@admin_requerido
def clientes(request):
    lista = (User.objects.filter(is_staff=False)
             .annotate(num_pedidos=Count("pedidos", distinct=True),
                       gastado=Coalesce(Sum("pedidos__total"), 0))
             .order_by("-date_joined"))
    return render(request, "panel/clientes.html", {"seccion": "clientes", "clientes": lista})


@admin_requerido
def encuestas(request):
    respuestas = RespuestaEncuesta.objects.select_related("usuario", "categoria_favorita")
    return render(request, "panel/encuestas.html", {
        "seccion": "encuestas",
        "respuestas": respuestas,
        "promedio": respuestas.aggregate(p=Avg("calificacion"))["p"] or 0,
    })


@admin_requerido
def ubicaciones(request):
    ultimas = _ultimas_ubicaciones()
    return render(request, "panel/ubicaciones.html", {
        "seccion": "ubicaciones",
        "ultimas": sorted(ultimas, key=lambda u: u.distancia_km),
        "registros": Ubicacion.objects.select_related("usuario")[:30],
        "mapa_datos": {"puntos": [
            {"lat": u.latitud, "lng": u.longitud,
             "nombre": u.usuario.get_full_name() or u.usuario.username,
             "distancia": round(u.distancia_km, 2)}
            for u in ultimas
        ]},
    })
