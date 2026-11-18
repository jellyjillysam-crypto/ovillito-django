from django.contrib import admin

from .models import Comentario, EntradaBlog, Foto, MensajeChat, RespuestaEncuesta, Ubicacion, Video


@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ("usuario", "latitud", "longitud", "distancia_km", "origen", "creada")
    list_filter = ("origen",)


class ComentarioInline(admin.TabularInline):
    model = Comentario
    extra = 0


@admin.register(EntradaBlog)
class EntradaBlogAdmin(admin.ModelAdmin):
    list_display = ("titulo", "autor", "publicada", "creada")
    prepopulated_fields = {"slug": ("titulo",)}
    inlines = [ComentarioInline]


@admin.register(MensajeChat)
class MensajeChatAdmin(admin.ModelAdmin):
    list_display = ("usuario", "texto", "creado")


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "nivel", "duracion", "creado")


@admin.register(RespuestaEncuesta)
class RespuestaEncuestaAdmin(admin.ModelAdmin):
    list_display = ("usuario", "calificacion", "categoria_favorita", "canal", "recomendaria", "creada")
    list_filter = ("calificacion", "canal", "recomendaria")


@admin.register(Foto)
class FotoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "descripcion", "creada")
