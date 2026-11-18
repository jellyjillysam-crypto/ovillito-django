from django.urls import path

from . import views

app_name = "tienda"

urlpatterns = [
    path("", views.home, name="home"),
    path("producto/<slug:slug>/", views.producto_detalle, name="producto"),
    path("carrito/", views.carrito_pagina, name="carrito"),
    path("carrito/api/", views.carrito_api, name="carrito_api"),
    path("carrito/api/agregar/<int:producto_id>/", views.carrito_agregar, name="carrito_agregar"),
    path("carrito/api/actualizar/<int:producto_id>/", views.carrito_actualizar, name="carrito_actualizar"),
    path("carrito/api/eliminar/<int:producto_id>/", views.carrito_eliminar, name="carrito_eliminar"),
    path("carrito/api/nota/", views.carrito_nota, name="carrito_nota"),
    path("checkout/", views.checkout, name="checkout"),
    path("pedidos/", views.mis_pedidos, name="mis_pedidos"),
    path("pedidos/<int:pk>/", views.pedido_detalle, name="pedido"),
]
