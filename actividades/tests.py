import io
import shutil
import tempfile

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from tienda.models import Categoria

from .geo import haversine_km, resumen_distancia
from .models import Comentario, EntradaBlog, Foto, MensajeChat, RespuestaEncuesta, Ubicacion, Video

MEDIA_TEMPORAL = tempfile.mkdtemp()


def imagen_png(nombre="foto.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (40, 30), "#F4B6C2").save(buffer, "PNG")
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type="image/png")


class GeoTests(TestCase):
    def test_haversine_bogota_medellin(self):
        distancia = haversine_km(4.711, -74.0721, 6.2442, -75.5812)
        self.assertAlmostEqual(distancia, 239.6, delta=2)

    def test_resumen(self):
        resumen = resumen_distancia(0.3)
        self.assertEqual(resumen["nivel"], "muy-cerca")
        self.assertEqual(resumen["distancia_texto"], "300 m")
        self.assertGreaterEqual(resumen["minutos"]["caminando"], 1)


class ActividadesBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cliente = User.objects.create_user("cliente", password="x", first_name="Camila")
        cls.otro = User.objects.create_user("otro", password="x")
        cls.admin = User.objects.create_user("admin", password="x", is_staff=True)

    def setUp(self):
        self.client.force_login(self.cliente)


class UbicacionTests(ActividadesBase):
    def test_guardar_ubicacion_en_la_tienda_da_distancia_cero(self):
        t = settings.TIENDA
        respuesta = self.client.post(reverse("actividades:ubicacion_guardar"),
                                     {"latitud": t["latitud"], "longitud": t["longitud"], "precision": 12},
                                     content_type="application/json")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["distancia_km"], 0)
        self.assertEqual(Ubicacion.objects.get().usuario, self.cliente)

    def test_coordenadas_invalidas(self):
        for datos in ({"latitud": "abc", "longitud": 1}, {"latitud": 95, "longitud": 0}):
            respuesta = self.client.post(reverse("actividades:ubicacion_guardar"), datos,
                                         content_type="application/json")
            self.assertEqual(respuesta.status_code, 400)

    def test_pagina_del_mapa(self):
        self.assertContains(self.client.get(reverse("actividades:ubicacion")), "Capturar mi ubicación")


class ChatTests(ActividadesBase):
    def test_enviar_y_consultar(self):
        respuesta = self.client.post(reverse("actividades:chat_enviar"), {"texto": "<b>Hola</b>"},
                                     content_type="application/json")
        self.assertEqual(respuesta.status_code, 201)
        mensaje = respuesta.json()["mensaje"]
        self.assertTrue(mensaje["es_mio"])
        nuevos = self.client.get(reverse("actividades:chat_mensajes"), {"despues": 0}).json()["mensajes"]
        self.assertEqual(nuevos[0]["texto"], "<b>Hola</b>")  # el texto se pinta con textContent
        vacios = self.client.get(reverse("actividades:chat_mensajes"), {"despues": mensaje["id"]}).json()
        self.assertEqual(vacios["mensajes"], [])

    def test_mensaje_vacio_o_largo(self):
        url = reverse("actividades:chat_enviar")
        self.assertEqual(self.client.post(url, {"texto": "  "}, content_type="application/json").status_code, 400)
        self.assertEqual(self.client.post(url, {"texto": "x" * 501}, content_type="application/json").status_code, 400)

    def test_solo_admin_elimina(self):
        mensaje = MensajeChat.objects.create(usuario=self.otro, texto="hola")
        url = reverse("actividades:chat_eliminar", args=[mensaje.pk])
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.admin)
        self.client.post(url)
        self.assertFalse(MensajeChat.objects.exists())


class BlogTests(ActividadesBase):
    def test_comentar_y_eliminar(self):
        entrada = EntradaBlog.objects.create(titulo="Cuidados", resumen="r", contenido="c", autor=self.admin)
        self.client.post(entrada.get_absolute_url(), {"texto": "¡Gracias!"})
        comentario = Comentario.objects.get()
        self.assertEqual(comentario.usuario, self.cliente)
        self.client.force_login(self.otro)
        url = reverse("actividades:comentario_eliminar", args=[comentario.pk])
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.cliente)
        self.client.post(url)
        self.assertFalse(Comentario.objects.exists())

    def test_borradores_ocultos_para_clientes(self):
        entrada = EntradaBlog.objects.create(titulo="Secreto", resumen="r", contenido="c", publicada=False)
        self.assertNotContains(self.client.get(reverse("actividades:blog")), "Secreto")
        self.assertEqual(self.client.get(entrada.get_absolute_url()).status_code, 403)

    def test_crud_blog_admin(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("panel:blog_crear"), {"titulo": "Nueva", "resumen": "r", "contenido": "c",
                                                       "ilustracion": "oso", "publicada": "on"})
        entrada = EntradaBlog.objects.get(titulo="Nueva")
        self.assertEqual(entrada.autor, self.admin)
        self.client.post(reverse("panel:blog_eliminar", args=[entrada.pk]))
        self.assertFalse(EntradaBlog.objects.exists())


class VideoTests(ActividadesBase):
    def test_extrae_id_de_youtube(self):
        for url in ["https://www.youtube.com/watch?v=abcdefghijk", "https://youtu.be/abcdefghijk",
                    "https://www.youtube.com/shorts/abcdefghijk"]:
            self.assertEqual(Video(titulo="t", url_youtube=url).youtube_id, "abcdefghijk")

    def test_requiere_una_fuente(self):
        with self.assertRaises(ValidationError):
            Video(titulo="Sin fuente").full_clean()

    def test_crud_videos_admin(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("panel:video_crear"), {"titulo": "Anillo mágico", "nivel": "principiante",
                                                        "url_youtube": "https://youtu.be/abcdefghijk"})
        video = Video.objects.get()
        self.assertContains(self.client.get(reverse("actividades:videos")), "youtube-nocookie.com/embed/abcdefghijk")
        self.client.post(reverse("panel:video_eliminar", args=[video.pk]))
        self.assertFalse(Video.objects.exists())


class EncuestaTests(ActividadesBase):
    def test_responder_y_actualizar(self):
        categoria = Categoria.objects.create(nombre="Hogar")
        datos = {"calificacion": 5, "categoria_favorita": categoria.pk, "canal": "instagram", "recomendaria": "si"}
        self.client.post(reverse("actividades:encuesta"), datos)
        self.client.post(reverse("actividades:encuesta"), {**datos, "calificacion": 4})
        respuesta = RespuestaEncuesta.objects.get()
        self.assertEqual(respuesta.calificacion, 4)

    def test_opciones_sin_valor_vacio(self):
        respuesta = self.client.get(reverse("actividades:encuesta"))
        self.assertNotContains(respuesta, "---------")


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class FotoTests(ActividadesBase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def test_subir_foto(self):
        respuesta = self.client.post(reverse("actividades:foto_subir"),
                                     {"imagen": imagen_png(), "descripcion": "Mi osito"},
                                     HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(Foto.objects.get().descripcion, "Mi osito")

    def test_rechaza_archivos_que_no_son_imagen(self):
        falso = SimpleUploadedFile("x.png", b"no soy una imagen", content_type="image/png")
        respuesta = self.client.post(reverse("actividades:foto_subir"), {"imagen": falso},
                                     HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(respuesta.status_code, 400)

    def test_no_se_borran_fotos_ajenas(self):
        foto = Foto.objects.create(usuario=self.otro, imagen=imagen_png())
        self.assertEqual(self.client.post(reverse("actividades:foto_eliminar", args=[foto.pk])).status_code, 403)
