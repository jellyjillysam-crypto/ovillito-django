from django.urls import path

from . import views

app_name = "actividades"

urlpatterns = [
    path("ubicacion/", views.ubicacion, name="ubicacion"),
    path("ubicacion/guardar/", views.ubicacion_guardar, name="ubicacion_guardar"),
    path("blog/", views.blog_lista, name="blog"),
    path("blog/<slug:slug>/", views.blog_detalle, name="blog_detalle"),
    path("comentarios/<int:pk>/eliminar/", views.comentario_eliminar, name="comentario_eliminar"),
    path("chat/", views.chat, name="chat"),
    path("chat/mensajes/", views.chat_mensajes, name="chat_mensajes"),
    path("chat/enviar/", views.chat_enviar, name="chat_enviar"),
    path("chat/<int:pk>/eliminar/", views.chat_eliminar, name="chat_eliminar"),
    path("videos/", views.videos, name="videos"),
    path("encuesta/", views.encuesta, name="encuesta"),
    path("fotos/", views.fotos, name="fotos"),
    path("fotos/subir/", views.foto_subir, name="foto_subir"),
    path("fotos/<int:pk>/eliminar/", views.foto_eliminar, name="foto_eliminar"),
]
