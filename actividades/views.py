import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from cuentas.permisos import admin_requerido, es_admin

from .forms import ComentarioForm, EncuestaForm, FotoForm
from .geo import distancia_a_tienda, resumen_distancia
from .models import Comentario, EntradaBlog, Foto, MensajeChat, RespuestaEncuesta, Ubicacion, Video


def _es_fetch(request):
    return request.headers.get("x-requested-with") == "fetch"


def _cargar_json(request):
    try:
        return json.loads(request.body or b"{}")
    except ValueError:
        return {}


# --- Ubicación y mapa ------------------------------------------------------
@login_required
def ubicacion(request):
    ultima = request.user.ubicaciones.first()
    return render(request, "actividades/ubicacion.html", {
        "ultima": ultima,
        "resumen": resumen_distancia(ultima.distancia_km) if ultima else None,
        "historial": request.user.ubicaciones.all()[:5],
        "mapa_datos": {
            "tienda": {
                "lat": settings.TIENDA["latitud"],
                "lng": settings.TIENDA["longitud"],
                "nombre": settings.TIENDA["nombre"],
                "direccion": settings.TIENDA["direccion"],
            },
            "ultima": {"lat": ultima.latitud, "lng": ultima.longitud} if ultima else None,
        },
    })


@login_required
@require_POST
def ubicacion_guardar(request):
    datos = _cargar_json(request)
    try:
        latitud = float(datos.get("latitud"))
        longitud = float(datos.get("longitud"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Coordenadas inválidas."}, status=400)
    if not (-90 <= latitud <= 90 and -180 <= longitud <= 180):
        return JsonResponse({"error": "Coordenadas fuera de rango."}, status=400)

    precision = datos.get("precision")
    try:
        precision = round(float(precision), 1) if precision is not None else None
    except (TypeError, ValueError):
        precision = None
    origen = "manual" if datos.get("origen") == "manual" else "gps"

    distancia = distancia_a_tienda(latitud, longitud)
    registro = Ubicacion.objects.create(
        usuario=request.user, latitud=latitud, longitud=longitud,
        precision_m=precision, distancia_km=distancia, origen=origen,
    )
    return JsonResponse({
        "id": registro.pk,
        "latitud": latitud,
        "longitud": longitud,
        "precision": precision,
        "origen": registro.get_origen_display(),
        "fecha": timezone.localtime(registro.creada).strftime("%d/%m/%Y %H:%M"),
        **resumen_distancia(distancia),
    })


# --- Blog ------------------------------------------------------------------
@login_required
def blog_lista(request):
    entradas = EntradaBlog.objects.select_related("autor").annotate(num_comentarios=Count("comentarios"))
    if not es_admin(request.user):
        entradas = entradas.filter(publicada=True)
    return render(request, "actividades/blog_lista.html", {"entradas": entradas})


@login_required
def blog_detalle(request, slug):
    entrada = get_object_or_404(EntradaBlog.objects.select_related("autor"), slug=slug)
    if not entrada.publicada and not es_admin(request.user):
        raise PermissionDenied
    form = ComentarioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        comentario = form.save(commit=False)
        comentario.entrada = entrada
        comentario.usuario = request.user
        comentario.save()
        messages.success(request, "¡Gracias por comentar!")
        return redirect(f"{entrada.get_absolute_url()}#comentario-{comentario.pk}")
    otras = EntradaBlog.objects.filter(publicada=True).exclude(pk=entrada.pk)[:3]
    return render(request, "actividades/blog_detalle.html", {
        "entrada": entrada,
        "comentarios": entrada.comentarios.select_related("usuario"),
        "form": form,
        "otras": otras,
    })


@login_required
@require_POST
def comentario_eliminar(request, pk):
    comentario = get_object_or_404(Comentario.objects.select_related("entrada"), pk=pk)
    if comentario.usuario_id != request.user.id and not es_admin(request.user):
        raise PermissionDenied
    url = comentario.entrada.get_absolute_url()
    comentario.delete()
    messages.info(request, "Comentario eliminado.")
    return redirect(f"{url}#comentarios")


# --- Chat de la comunidad --------------------------------------------------
def _mensaje_json(mensaje, usuario_actual):
    autor = mensaje.usuario
    nombre = autor.get_full_name() or autor.username
    local = timezone.localtime(mensaje.creado)
    hoy = timezone.localdate()
    return {
        "id": mensaje.pk,
        "autor": nombre,
        "inicial": nombre[:1].upper(),
        "es_mio": autor.pk == usuario_actual.pk,
        "es_admin": autor.is_staff,
        "texto": mensaje.texto,
        "hora": local.strftime("%H:%M"),
        "dia": "Hoy" if local.date() == hoy else local.strftime("%d/%m"),
    }


@login_required
def chat(request):
    recientes = list(MensajeChat.objects.select_related("usuario").order_by("-pk")[:60])[::-1]
    return render(request, "actividades/chat.html", {
        "mensajes_iniciales": [_mensaje_json(m, request.user) for m in recientes],
        "participantes": MensajeChat.objects.values("usuario").distinct().count(),
    })


@login_required
@require_GET
def chat_mensajes(request):
    try:
        despues = int(request.GET.get("despues", 0))
    except ValueError:
        despues = 0
    nuevos = MensajeChat.objects.select_related("usuario").filter(pk__gt=despues).order_by("pk")[:100]
    return JsonResponse({"mensajes": [_mensaje_json(m, request.user) for m in nuevos]})


@login_required
@require_POST
def chat_enviar(request):
    texto = (request.POST.get("texto") or _cargar_json(request).get("texto") or "").strip()
    if not texto:
        return JsonResponse({"error": "Escribe un mensaje."}, status=400)
    if len(texto) > 500:
        return JsonResponse({"error": "El mensaje es demasiado largo (máximo 500 caracteres)."}, status=400)
    mensaje = MensajeChat.objects.create(usuario=request.user, texto=texto)
    return JsonResponse({"mensaje": _mensaje_json(mensaje, request.user)}, status=201)


@admin_requerido
@require_POST
def chat_eliminar(request, pk):
    get_object_or_404(MensajeChat, pk=pk).delete()
    if _es_fetch(request):
        return JsonResponse({"ok": True})
    return redirect("actividades:chat")


# --- Videos ----------------------------------------------------------------
@login_required
def videos(request):
    lista = Video.objects.all()
    nivel = request.GET.get("nivel", "")
    if nivel in dict(Video.NIVELES):
        lista = lista.filter(nivel=nivel)
    return render(request, "actividades/videos.html", {
        "videos": lista,
        "niveles": Video.NIVELES,
        "nivel": nivel,
    })


# --- Encuesta --------------------------------------------------------------
@login_required
def encuesta(request):
    existente = RespuestaEncuesta.objects.filter(usuario=request.user).first()
    form = EncuestaForm(request.POST or None, instance=existente)
    if request.method == "POST" and form.is_valid():
        respuesta = form.save(commit=False)
        respuesta.usuario = request.user
        respuesta.save()
        messages.success(request, "¡Gracias por responder! Tu opinión nos ayuda a tejer mejor.")
        return redirect("actividades:encuesta")

    total = RespuestaEncuesta.objects.count()
    resumen = RespuestaEncuesta.objects.aggregate(
        promedio=Avg("calificacion"),
        recomiendan=Count("pk", filter=Q(recomendaria="si")),
    )
    return render(request, "actividades/encuesta.html", {
        "form": form,
        "existente": existente,
        "total": total,
        "promedio": resumen["promedio"] or 0,
        "porcentaje_recomiendan": round(resumen["recomiendan"] * 100 / total) if total else 0,
    })


# --- Fotos con la cámara ---------------------------------------------------
def _foto_json(foto, usuario):
    return {
        "id": foto.pk,
        "url": foto.imagen.url,
        "descripcion": foto.descripcion,
        "autor": foto.usuario.get_full_name() or foto.usuario.username,
        "fecha": timezone.localtime(foto.creada).strftime("%d/%m/%Y %H:%M"),
        "puede_eliminar": foto.usuario_id == usuario.id or es_admin(usuario),
    }


@login_required
def fotos(request):
    galeria = Foto.objects.select_related("usuario")
    if not es_admin(request.user):
        galeria = galeria.filter(usuario=request.user)
    return render(request, "actividades/fotos.html", {
        "galeria": galeria,
        "form": FotoForm(),
        "limite_mb": settings.FOTO_TAMANO_MAXIMO // (1024 * 1024),
    })


@login_required
@require_POST
def foto_subir(request):
    form = FotoForm(request.POST, request.FILES)
    if form.is_valid():
        foto = form.save(commit=False)
        foto.usuario = request.user
        foto.save()
        if _es_fetch(request):
            return JsonResponse({"foto": _foto_json(foto, request.user)}, status=201)
        messages.success(request, "¡Foto guardada en tu galería!")
        return redirect("actividades:fotos")

    errores = " ".join(e for lista in form.errors.values() for e in lista)
    if _es_fetch(request):
        return JsonResponse({"error": errores or "No se pudo guardar la foto."}, status=400)
    messages.error(request, errores or "No se pudo guardar la foto.")
    return redirect("actividades:fotos")


@login_required
@require_POST
def foto_eliminar(request, pk):
    foto = get_object_or_404(Foto, pk=pk)
    if foto.usuario_id != request.user.id and not es_admin(request.user):
        raise PermissionDenied
    foto.delete()
    if _es_fetch(request):
        return JsonResponse({"ok": True})
    messages.info(request, "Foto eliminada.")
    return redirect("actividades:fotos")
