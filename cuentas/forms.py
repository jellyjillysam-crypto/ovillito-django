from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .permisos import ROL_ADMIN, ROL_CLIENTE


class LoginForm(AuthenticationForm):
    """Login con selector de tipo de usuario (cliente / administrador)."""

    rol = forms.ChoiceField(
        choices=[(ROL_CLIENTE, "Cliente"), (ROL_ADMIN, "Administrador")],
        initial=ROL_CLIENTE,
        widget=forms.RadioSelect,
        label="Ingresar como",
    )
    recordarme = forms.BooleanField(required=False, initial=True, label="Recordarme")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Usuario"
        self.fields["username"].widget.attrs.update(
            {"placeholder": "Tu nombre de usuario", "autocomplete": "username"}
        )
        self.fields["password"].label = "Contraseña"
        self.fields["password"].widget.attrs.update(
            {"placeholder": "••••••••", "autocomplete": "current-password"}
        )

    error_messages = {
        "invalid_login": "Usuario o contraseña incorrectos. Revisa los datos e inténtalo de nuevo.",
        "inactive": "Esta cuenta está desactivada.",
    }


class RegistroForm(UserCreationForm):
    """Registro de clientes. Los administradores se crean desde el panel o la consola."""

    first_name = forms.CharField(label="Nombre", max_length=60)
    email = forms.EmailField(label="Correo electrónico")

    class Meta:
        model = User
        fields = ("first_name", "username", "email")
        labels = {"username": "Usuario"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            "first_name": "¿Cómo te llamas?",
            "username": "Elige un usuario",
            "email": "tu@correo.com",
            "password1": "Mínimo 8 caracteres",
            "password2": "Repite la contraseña",
        }
        for nombre, texto in placeholders.items():
            self.fields[nombre].widget.attrs["placeholder"] = texto
        self.fields["password1"].label = "Contraseña"
        self.fields["password2"].label = "Confirmar contraseña"
        self.fields["username"].help_text = "Letras, números y @ . + - _"
        self.fields["password1"].help_text = ""

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo.")
        return email
