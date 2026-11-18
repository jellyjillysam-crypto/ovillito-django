from django.urls import path

from . import views

app_name = "cuentas"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("registro/", views.registro, name="registro"),
    path("salir/", views.salir, name="salir"),
]
