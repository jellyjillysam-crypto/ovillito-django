from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse


class FlujoDeAccesoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("admin", password="Admin12345", is_staff=True)
        cls.cliente = User.objects.create_user("cliente", password="Cliente12345", first_name="Camila")

    def _login(self, usuario, clave, rol):
        return self.client.post(reverse("cuentas:login"), {"username": usuario, "password": clave, "rol": rol})

    def test_la_raiz_lleva_al_catalogo_si_no_hay_sesion(self):
        respuesta = self.client.get("/")
        self.assertRedirects(respuesta, reverse("tienda:home"))

    def test_catalogo_es_publico(self):
        self.assertEqual(self.client.get(reverse("tienda:home")).status_code, 200)

    def test_checkout_sin_sesion_lleva_al_login(self):
        respuesta = self.client.post(reverse("tienda:checkout"))
        self.assertIn(reverse("cuentas:login"), respuesta["Location"])

    def test_las_paginas_internas_exigen_login(self):
        for url in [reverse("actividades:chat"), reverse("panel:dashboard")]:
            respuesta = self.client.get(url)
            self.assertEqual(respuesta.status_code, 302)
            self.assertIn(reverse("cuentas:login"), respuesta["Location"])

    def test_cliente_entra_a_su_home(self):
        respuesta = self._login("cliente", "Cliente12345", "cliente")
        self.assertRedirects(respuesta, reverse("tienda:home"))
        self.assertRedirects(self.client.get("/"), reverse("tienda:home"))

    def test_admin_entra_al_panel_de_metricas(self):
        respuesta = self._login("admin", "Admin12345", "admin")
        self.assertRedirects(respuesta, reverse("panel:dashboard"))

    def test_cliente_no_puede_entrar_como_administrador(self):
        respuesta = self._login("cliente", "Cliente12345", "admin")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "no tiene permisos de administrador")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_admin_debe_elegir_el_rol_administrador(self):
        respuesta = self._login("admin", "Admin12345", "cliente")
        self.assertContains(respuesta, "cuenta de administrador")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_credenciales_incorrectas(self):
        respuesta = self._login("cliente", "mala", "cliente")
        self.assertContains(respuesta, "Usuario o contraseña incorrectos")

    def test_next_externo_es_ignorado(self):
        respuesta = self.client.post(reverse("cuentas:login") + "?next=https://malicioso.com/",
                                     {"username": "cliente", "password": "Cliente12345", "rol": "cliente",
                                      "next": "https://malicioso.com/"})
        self.assertRedirects(respuesta, reverse("tienda:home"))

    def test_registro_crea_un_cliente_y_abre_sesion(self):
        respuesta = self.client.post(reverse("cuentas:registro"), {
            "first_name": "Ana", "username": "ana", "email": "ana@correo.com",
            "password1": "TejerEsLindo2026", "password2": "TejerEsLindo2026",
        })
        self.assertRedirects(respuesta, reverse("tienda:home"))
        nueva = User.objects.get(username="ana")
        self.assertFalse(nueva.is_staff)

    def test_salir_requiere_post(self):
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get(reverse("cuentas:salir")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("cuentas:salir")), reverse("tienda:home"))


@override_settings(ADMIN_EMAILS=["duena@correo.com"])
class CorreosAdminTests(TestCase):
    def _registrar(self, usuario, correo):
        return self.client.post(reverse("cuentas:registro"), {
            "first_name": "X", "username": usuario, "email": correo,
            "password1": "TejerEsLindo2026", "password2": "TejerEsLindo2026",
        })

    def test_correo_de_la_lista_es_admin(self):
        respuesta = self._registrar("duena", "Duena@Correo.com")
        self.assertRedirects(respuesta, reverse("panel:dashboard"))
        self.assertTrue(User.objects.get(username="duena").is_staff)

    def test_otro_correo_es_cliente(self):
        self._registrar("otra", "otra@correo.com")
        self.assertFalse(User.objects.get(username="otra").is_staff)

    def test_login_retira_admin_si_ya_no_esta_en_la_lista(self):
        User.objects.create_user("vieja", email="vieja@correo.com", password="Clave12345", is_staff=True)
        self.client.post(reverse("cuentas:login"), {"username": "vieja", "password": "Clave12345", "rol": "cliente"})
        self.assertFalse(User.objects.get(username="vieja").is_staff)


class PermisosPorRolTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("admin", password="x", is_staff=True)
        cls.cliente = User.objects.create_user("cliente", password="x")

    def test_cliente_recibe_403_en_el_panel(self):
        self.client.force_login(self.cliente)
        for nombre in ["panel:dashboard", "panel:productos", "panel:producto_crear", "panel:pedidos", "panel:encuestas"]:
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 403, nombre)

    def test_admin_ve_el_panel(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("panel:dashboard")).status_code, 200)
