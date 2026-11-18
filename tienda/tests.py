import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Categoria, Pedido, Producto
from .templatetags.tienda_extras import km, pesos


def crear_producto(**extra):
    categoria, _ = Categoria.objects.get_or_create(nombre="Amigurumis")
    datos = {"categoria": categoria, "nombre": "Osito", "descripcion": "Tierno", "precio": 50000, "stock": 5,
             "colores": "#FFFFFF, #000000"}
    datos.update(extra)
    return Producto.objects.create(**datos)


class FiltrosTests(TestCase):
    def test_pesos(self):
        self.assertEqual(pesos(1234567), "$1.234.567")
        self.assertEqual(pesos(0), "$0")

    def test_km(self):
        self.assertEqual(km(0.42), "420 m")
        self.assertEqual(km(3.456), "3,5 km")


class CatalogoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = User.objects.create_user("cliente", password="x")
        cls.osito = crear_producto(nombre="Osito", precio=68000)
        cls.llavero = crear_producto(nombre="Llavero", precio=18000)
        cls.oculto = crear_producto(nombre="Oculto", activo=False)

    def setUp(self):
        self.client.force_login(self.usuario)

    def test_home_lista_solo_productos_activos(self):
        respuesta = self.client.get(reverse("tienda:home"))
        self.assertContains(respuesta, "Osito")
        self.assertNotContains(respuesta, "Oculto")

    def test_filtro_por_precio_y_busqueda(self):
        respuesta = self.client.get(reverse("tienda:home"), {"precio": "hasta-30"})
        self.assertEqual(list(respuesta.context["productos"]), [self.llavero])
        respuesta = self.client.get(reverse("tienda:home"), {"q": "osi"})
        self.assertEqual(list(respuesta.context["productos"]), [self.osito])

    def test_colores_invalidos_no_se_muestran(self):
        self.osito.colores = "#FFFFFF, red;background:url(x)"
        self.assertEqual(self.osito.lista_colores(), ["#FFFFFF"])

    def test_detalle(self):
        self.assertContains(self.client.get(self.osito.get_absolute_url()), "$68.000")


class CarritoYPedidoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = User.objects.create_user("cliente", password="x")
        cls.otro = User.objects.create_user("otro", password="x")

    def setUp(self):
        self.client.force_login(self.usuario)
        self.producto = crear_producto(precio=80000, stock=3)

    def _post(self, nombre, *args, **datos):
        return self.client.post(reverse(nombre, args=args), datos, HTTP_X_REQUESTED_WITH="fetch")

    def test_agregar_actualizar_y_eliminar(self):
        datos = self._post("tienda:carrito_agregar", self.producto.pk, cantidad=2).json()
        self.assertEqual(datos["cantidad"], 2)
        self.assertEqual(datos["subtotal"], 160000)
        self.assertEqual(datos["falta_envio_gratis"], 0)

        datos = self._post("tienda:carrito_actualizar", self.producto.pk, cantidad=10).json()
        self.assertEqual(datos["cantidad"], 3, "no puede superar el stock")

        datos = self._post("tienda:carrito_eliminar", self.producto.pk).json()
        self.assertEqual(datos["cantidad"], 0)

    def test_producto_agotado_responde_409(self):
        self.producto.stock = 0
        self.producto.save()
        respuesta = self._post("tienda:carrito_agregar", self.producto.pk)
        self.assertEqual(respuesta.status_code, 409)

    def test_checkout_crea_pedido_y_descuenta_stock(self):
        self._post("tienda:carrito_agregar", self.producto.pk, cantidad=1)
        respuesta = self.client.post(reverse("tienda:checkout"), {"nota": "Es un regalo"})
        pedido = Pedido.objects.get()
        self.assertRedirects(respuesta, reverse("tienda:pedido", args=[pedido.pk]))
        self.assertEqual(pedido.subtotal, 80000)
        self.assertEqual(pedido.envio, 12000)  # no alcanza el envío gratis
        self.assertEqual(pedido.total, 92000)
        self.assertEqual(pedido.nota, "Es un regalo")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 2)
        self.assertEqual(self.client.get(reverse("tienda:carrito_api")).json()["cantidad"], 0)

    def test_checkout_rechaza_si_el_stock_cambio(self):
        self._post("tienda:carrito_agregar", self.producto.pk, cantidad=3)
        Producto.objects.filter(pk=self.producto.pk).update(stock=1)
        self.client.post(reverse("tienda:checkout"))
        self.assertFalse(Pedido.objects.exists())

    def test_un_cliente_no_ve_pedidos_ajenos(self):
        pedido = Pedido.objects.create(usuario=self.otro, total=1000)
        self.assertEqual(self.client.get(reverse("tienda:pedido", args=[pedido.pk])).status_code, 403)

    def test_nota_del_carrito(self):
        respuesta = self.client.post(reverse("tienda:carrito_nota"), {"nota": "Color rosa"})
        self.assertEqual(json.loads(respuesta.content)["nota"], "Color rosa")


class CrudProductosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("admin", password="x", is_staff=True)
        cls.cliente = User.objects.create_user("cliente", password="x")
        cls.categoria = Categoria.objects.create(nombre="Hogar")

    def _datos(self, **extra):
        datos = {"nombre": "Manta", "categoria": self.categoria.pk, "descripcion": "Abrigada", "precio": 200000,
                 "stock": 2, "colores": "#f4b6c2, #FFD966", "ilustracion": "manta", "activo": "on"}
        datos.update(extra)
        return datos

    def test_crear_editar_eliminar(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(reverse("panel:producto_crear"), self._datos())
        self.assertRedirects(respuesta, reverse("panel:productos"))
        producto = Producto.objects.get(nombre="Manta")
        self.assertEqual(producto.colores, "#F4B6C2, #FFD966")

        self.client.post(reverse("panel:producto_editar", args=[producto.pk]), self._datos(precio=210000))
        producto.refresh_from_db()
        self.assertEqual(producto.precio, 210000)

        self.client.post(reverse("panel:producto_eliminar", args=[producto.pk]))
        self.assertFalse(Producto.objects.filter(pk=producto.pk).exists())

    def test_color_invalido(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(reverse("panel:producto_crear"), self._datos(colores="rojo"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Producto.objects.exists())

    def test_cliente_no_puede_crear(self):
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.post(reverse("panel:producto_crear"), self._datos()).status_code, 403)
        self.assertFalse(Producto.objects.exists())
