from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import LoginForm, RegistroForm
from .permisos import ROL_ADMIN, ROL_CLIENTE, es_admin, home_por_rol


def inicio(request):
    """Entrada del sitio: primero el login; después, el home según el rol."""
    if not request.user.is_authenticated:
        return redirect("cuentas:login")
    return redirect(home_por_rol(request.user))


def _destino_seguro(request, usuario):
    siguiente = request.POST.get("next") or request.GET.get("next")
    if siguiente and url_has_allowed_host_and_scheme(
        siguiente, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return siguiente
    return home_por_rol(usuario)


def login_view(request):
    if request.user.is_authenticated:
        return redirect(home_por_rol(request.user))

    rol_inicial = request.GET.get("rol") if request.GET.get("rol") in (ROL_ADMIN, ROL_CLIENTE) else ROL_CLIENTE
    form = LoginForm(request, data=request.POST or None, initial={"rol": rol_inicial})

    if request.method == "POST" and form.is_valid():
        usuario = form.get_user()
        rol = form.cleaned_data["rol"]
        if rol == ROL_ADMIN and not es_admin(usuario):
            form.add_error(None, "Esta cuenta no tiene permisos de administrador. Selecciona «Cliente».")
        elif rol == ROL_CLIENTE and es_admin(usuario):
            form.add_error(None, "Esta es una cuenta de administrador. Selecciona «Administrador».")
        else:
            login(request, usuario)
            if not form.cleaned_data.get("recordarme"):
                request.session.set_expiry(0)  # la sesión termina al cerrar el navegador
            nombre = usuario.first_name or usuario.username
            messages.success(request, f"¡Hola, {nombre}! Qué gusto verte de nuevo.")
            return redirect(_destino_seguro(request, usuario))

    return render(request, "cuentas/login.html", {
        "form": form,
        "next": request.GET.get("next", ""),
        "mostrar_demo": settings.DEBUG,
    })


def registro(request):
    if request.user.is_authenticated:
        return redirect(home_por_rol(request.user))
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, f"¡Bienvenida/o a Ovillito, {usuario.first_name}! Tu cuenta está lista.")
        return redirect("tienda:home")
    return render(request, "cuentas/registro.html", {"form": form})


@require_POST
def salir(request):
    logout(request)
    messages.info(request, "Cerraste sesión. ¡Vuelve pronto!")
    return redirect("cuentas:login")
