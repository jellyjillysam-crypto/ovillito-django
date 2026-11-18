from django import forms

from .models import Producto


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            "nombre", "categoria", "descripcion", "precio", "stock",
            "colores", "imagen", "ilustracion", "destacado", "activo",
        ]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 4}),
            "colores": forms.TextInput(attrs={
                "placeholder": "#F4B6C2, #FFF6DE, #1F5C3F",
                "data-colores": "",
            }),
            "precio": forms.NumberInput(attrs={"min": 0, "step": 500}),
            "stock": forms.NumberInput(attrs={"min": 0}),
        }

    def clean_colores(self):
        colores = [c.strip().upper() for c in self.cleaned_data["colores"].split(",") if c.strip()]
        return ", ".join(colores)


class AgregarCarritoForm(forms.Form):
    cantidad = forms.IntegerField(min_value=1, max_value=99, initial=1)
