import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from tienda.models import Pedido

MEDIA_TEMPORAL = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("cargar_demo", verbosity=0, stdout=open("/dev/null", "w"))

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def setUp(self):
        self.client.force_login(User.objects.get(username="admin"))

    def test_dashboard_con_metricas(self):
        respuesta = self.client.get(reverse("panel:dashboard"))
        self.assertEqual(respuesta.status_code, 200)
        kpi = respuesta.context["kpi"]
        self.assertEqual(kpi["pedidos"], Pedido.objects.count())
        self.assertEqual(kpi["clientes"], 7)
        self.assertEqual(len(respuesta.context["graficas"]["dias"]), 14)
        self.assertContains(respuesta, 'id="datos-graficas"')

    def test_paginas_del_panel(self):
        for nombre in ["panel:productos", "panel:blog", "panel:videos", "panel:pedidos", "panel:clientes",
                       "panel:encuestas", "panel:ubicaciones", "panel:producto_crear"]:
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 200, nombre)

    def test_cambiar_estado_de_pedido(self):
        pedido = Pedido.objects.first()
        self.client.post(reverse("panel:pedido_estado", args=[pedido.pk]),
                         {"estado": "entregado", "volver": "https://malicioso.com/"})
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "entregado")

    def test_cargar_demo_es_idempotente(self):
        antes = Pedido.objects.count()
        call_command("cargar_demo", verbosity=0, stdout=open("/dev/null", "w"))
        self.assertEqual(Pedido.objects.count(), antes)

    def test_paginas_de_cliente_renderizan(self):
        self.client.force_login(User.objects.get(username="cliente"))
        for nombre in ["tienda:home", "tienda:carrito", "tienda:mis_pedidos", "identidad", "actividades:ubicacion",
                       "actividades:blog", "actividades:chat", "actividades:videos", "actividades:encuesta",
                       "actividades:fotos"]:
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 200, nombre)
