from django.urls import path

from . import views

app_name = "panel"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # CRUD de productos
    path("productos/", views.ProductoLista.as_view(), name="productos"),
    path("productos/nuevo/", views.ProductoCrear.as_view(), name="producto_crear"),
    path("productos/<int:pk>/editar/", views.ProductoEditar.as_view(), name="producto_editar"),
    path("productos/<int:pk>/eliminar/", views.ProductoEliminar.as_view(), name="producto_eliminar"),
    # CRUD del blog
    path("blog/", views.EntradaLista.as_view(), name="blog"),
    path("blog/nueva/", views.EntradaCrear.as_view(), name="blog_crear"),
    path("blog/<int:pk>/editar/", views.EntradaEditar.as_view(), name="blog_editar"),
    path("blog/<int:pk>/eliminar/", views.EntradaEliminar.as_view(), name="blog_eliminar"),
    # CRUD de videos
    path("videos/", views.VideoLista.as_view(), name="videos"),
    path("videos/nuevo/", views.VideoCrear.as_view(), name="video_crear"),
    path("videos/<int:pk>/editar/", views.VideoEditar.as_view(), name="video_editar"),
    path("videos/<int:pk>/eliminar/", views.VideoEliminar.as_view(), name="video_eliminar"),
    # Consultas
    path("pedidos/", views.pedidos, name="pedidos"),
    path("pedidos/<int:pk>/estado/", views.pedido_estado, name="pedido_estado"),
    path("clientes/", views.clientes, name="clientes"),
    path("encuestas/", views.encuestas, name="encuestas"),
    path("ubicaciones/", views.ubicaciones, name="ubicaciones"),
]
