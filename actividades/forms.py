from django import forms
from django.conf import settings

from .models import Comentario, EntradaBlog, Foto, RespuestaEncuesta, Video


class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ["texto"]
        labels = {"texto": "Tu comentario"}
        widgets = {"texto": forms.Textarea(attrs={
            "rows": 3, "maxlength": 800, "placeholder": "Escribe algo bonito para la comunidad…",
        })}


class EncuestaForm(forms.ModelForm):
    class Meta:
        model = RespuestaEncuesta
        fields = ["calificacion", "categoria_favorita", "canal", "recomendaria", "comentario"]
        labels = {
            "calificacion": "¿Qué tan feliz estás con Ovillito?",
            "categoria_favorita": "¿Qué tipo de tejidos te gustan más?",
            "canal": "¿Cómo nos conociste?",
            "recomendaria": "¿Nos recomendarías a un amigo?",
            "comentario": "¿Algo que quieras contarnos? (opcional)",
        }
        widgets = {
            "calificacion": forms.RadioSelect,
            "canal": forms.RadioSelect,
            "recomendaria": forms.RadioSelect,
            "comentario": forms.Textarea(attrs={"rows": 3, "placeholder": "Ideas, productos que te gustaría ver…"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria_favorita"].empty_label = "Elige una categoría"
        self.fields["categoria_favorita"].required = True
        # Los grupos de botones de opción no necesitan la opción vacía «---------».
        for nombre in ("calificacion", "canal", "recomendaria"):
            campo = self.fields[nombre]
            campo.choices = [c for c in campo.choices if c[0] not in ("", None)]


class FotoForm(forms.ModelForm):
    class Meta:
        model = Foto
        fields = ["imagen", "descripcion"]
        widgets = {"descripcion": forms.TextInput(attrs={"placeholder": "Ej.: Mi primer amigurumi"})}

    def clean_imagen(self):
        imagen = self.cleaned_data["imagen"]
        if imagen and imagen.size > settings.FOTO_TAMANO_MAXIMO:
            limite = settings.FOTO_TAMANO_MAXIMO // (1024 * 1024)
            raise forms.ValidationError(f"La foto pesa demasiado. El máximo es {limite} MB.")
        return imagen


class EntradaBlogForm(forms.ModelForm):
    class Meta:
        model = EntradaBlog
        fields = ["titulo", "resumen", "contenido", "ilustracion", "imagen", "publicada"]
        widgets = {
            "resumen": forms.Textarea(attrs={"rows": 2}),
            "contenido": forms.Textarea(attrs={"rows": 10}),
        }
        help_texts = {
            "contenido": "Separa los párrafos con una línea en blanco.",
            "imagen": "Opcional. Si no subes imagen se usa la ilustración elegida.",
        }


class VideoForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = ["titulo", "descripcion", "nivel", "url_youtube", "archivo", "portada", "duracion"]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}
