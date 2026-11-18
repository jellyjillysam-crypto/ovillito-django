"""Carrito de compras guardado en la sesión del usuario."""
from django.conf import settings

from .models import Producto
from .templatetags.tienda_extras import pesos

CLAVE_SESION = "carrito"
CLAVE_NOTA = "carrito_nota"


class Carrito:
    def __init__(self, request):
        self.session = request.session
        datos = self.session.get(CLAVE_SESION)
        self.datos = datos if isinstance(datos, dict) else {}

    # --- Operaciones -------------------------------------------------------
    def _guardar(self):
        self.session[CLAVE_SESION] = self.datos
        self.session.modified = True

    def agregar(self, producto, cantidad=1):
        clave = str(producto.pk)
        actual = int(self.datos.get(clave, 0))
        self.datos[clave] = max(0, min(actual + int(cantidad), producto.stock))
        if self.datos[clave] == 0:
            self.datos.pop(clave, None)
        self._guardar()
        return self.datos.get(clave, 0)

    def actualizar(self, producto, cantidad):
        clave = str(producto.pk)
        cantidad = max(0, min(int(cantidad), producto.stock))
        if cantidad == 0:
            self.datos.pop(clave, None)
        else:
            self.datos[clave] = cantidad
        self._guardar()
        return cantidad

    def eliminar(self, producto_id):
        self.datos.pop(str(producto_id), None)
        self._guardar()

    def limpiar(self):
        self.datos = {}
        self.session.pop(CLAVE_NOTA, None)
        self._guardar()

    @property
    def nota(self):
        return self.session.get(CLAVE_NOTA, "")

    @nota.setter
    def nota(self, texto):
        self.session[CLAVE_NOTA] = (texto or "")[:500]

    # --- Consultas ---------------------------------------------------------
    def items(self):
        ids = [int(k) for k in self.datos.keys() if str(k).isdigit()]
        productos = {p.pk: p for p in Producto.objects.filter(pk__in=ids, activo=True)}
        resultado = []
        for clave, cantidad in self.datos.items():
            producto = productos.get(int(clave)) if str(clave).isdigit() else None
            if producto is None:
                continue
            resultado.append({
                "producto": producto,
                "cantidad": int(cantidad),
                "subtotal": producto.precio * int(cantidad),
            })
        return resultado

    def __len__(self):
        return sum(int(c) for c in self.datos.values())

    def subtotal(self, items=None):
        items = items if items is not None else self.items()
        return sum(i["subtotal"] for i in items)

    def envio(self, subtotal):
        if subtotal == 0 or subtotal >= settings.TIENDA["envio_gratis_desde"]:
            return 0
        return settings.TIENDA["costo_envio"]

    def como_json(self):
        items = self.items()
        subtotal = self.subtotal(items)
        umbral = settings.TIENDA["envio_gratis_desde"]
        falta = max(0, umbral - subtotal)
        return {
            "items": [
                {
                    "id": i["producto"].pk,
                    "nombre": i["producto"].nombre,
                    "url": i["producto"].get_absolute_url(),
                    "imagen": i["producto"].imagen_url(),
                    "precio": i["producto"].precio,
                    "precio_fmt": pesos(i["producto"].precio),
                    "cantidad": i["cantidad"],
                    "stock": i["producto"].stock,
                    "subtotal": i["subtotal"],
                    "subtotal_fmt": pesos(i["subtotal"]),
                }
                for i in items
            ],
            "cantidad": sum(i["cantidad"] for i in items),
            "subtotal": subtotal,
            "subtotal_fmt": pesos(subtotal),
            "envio_gratis_desde": umbral,
            "envio_gratis_fmt": pesos(umbral),
            "falta_envio_gratis": falta,
            "falta_fmt": pesos(falta),
            "progreso_envio": 100 if umbral == 0 else min(100, round(subtotal * 100 / umbral)),
            "nota": self.nota,
        }
