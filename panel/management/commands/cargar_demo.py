"""
Carga datos de demostración para Ovillito.

Uso:
    python manage.py cargar_demo             # agrega lo que falte (idempotente)
    python manage.py cargar_demo --reiniciar # borra pedidos, encuestas, chat, etc. y los vuelve a crear
"""
import math
import random
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from actividades.geo import distancia_a_tienda
from actividades.models import (Comentario, EntradaBlog, MensajeChat, RespuestaEncuesta,
                                Ubicacion, Video)
from tienda.models import Categoria, ItemPedido, Pedido, Producto, Slide

SEMILLA = Path(__file__).resolve().parents[2] / "semilla"

CLIENTES = [
    ("cliente", "Camila", "Gómez"),
    ("laura", "Laura", "Martínez"),
    ("mateo", "Mateo", "Rojas"),
    ("sofia", "Sofía", "Herrera"),
    ("daniel", "Daniel", "Castro"),
    ("valentina", "Valentina", "López"),
    ("andres", "Andrés", "Moreno"),
]

CATEGORIAS = [
    ("Amigurumis", "Muñequitos tejidos con el corazón.", 1),
    ("Accesorios", "Bolsos, gorros, bufandas y llaveros.", 2),
    ("Hogar", "Mantas, flores eternas y detalles para tu casa.", 3),
    ("Kits y materiales", "Todo para empezar a tejer.", 4),
]

PRODUCTOS = [
    # nombre, categoría, precio, stock, colores, ilustración, destacado, descripción
    ("Osito Miel", "Amigurumis", 68000, 8, "#D9A066, #F4B6C2, #FFF1D6", "oso", True,
     "Nuestro clásico: un osito de 25 cm tejido en algodón suave, con moño rosado y relleno hipoalergénico. Ideal para regalar a bebés y a los no tan bebés."),
    ("Conejita Algodón", "Amigurumis", 62000, 5, "#FFF8EE, #BFE3C9, #F4B6C2", "conejo", False,
     "Conejita de orejas largas con vestido menta y zanahoria de la suerte. Mide 28 cm con las orejas."),
    ("Pulpo Abrazo", "Amigurumis", 45000, 12, "#C3B1E8, #A8D5EA, #F4B6C2", "pulpo", False,
     "Pulpito de tentáculos rizados que calma a los recién nacidos. Tejido con puntos apretados y ojos de seguridad."),
    ("Llavero Fresita", "Accesorios", 18000, 25, "#EE6F7F, #5FA27A", "fresa", False,
     "Fresa sonriente de 7 cm con argolla metálica. Perfecta para tus llaves o tu mochila."),
    ("Bolso Mercado Rayas", "Accesorios", 95000, 3, "#F6C453, #F4B6C2, #FFF6DE", "bolso", True,
     "Bolso amplio de rayas con asas reforzadas y florecita aplicada. Aguanta las compras del mercado y mucho amor."),
    ("Gorro Pompón Bosque", "Accesorios", 55000, 7, "#6BA583, #FFF6DE, #C9803A", "gorro", False,
     "Gorro de punto acanalado con pompón esponjoso y etiqueta de cuero. Talla única adulto."),
    ("Bufanda Nube Rosa", "Accesorios", 72000, 0, "#F4B6C2, #FFF6DE", "bufanda", False,
     "Bufanda larga a rayas con flecos en las puntas. Suave como una nube. ¡Vuelve pronto!"),
    ("Manta Granny Abuela", "Hogar", 240000, 2, "#F4B6C2, #FFD966, #7BB38C, #A8D5EA", "manta", True,
     "Manta de 120 × 120 cm hecha con 81 cuadros granny en colores pastel. Cada una es irrepetible."),
    ("Ramo Eterno", "Hogar", 58000, 9, "#F4B6C2, #FFD966, #A8D5EA", "flores", False,
     "Ramo de flores tejidas que nunca se marchitan, envuelto en papel kraft y cinta rosada."),
    ("Cactus Feliz", "Hogar", 32000, 14, "#7BB38C, #D9774B, #F4B6C2", "cactus", False,
     "Cactus amigurumi con maceta de terracota tejida. No necesita agua, solo cariño."),
    ("Set Posavasos Arcoíris", "Hogar", 28000, 18, "#F4B6C2, #A8D5EA, #FFD966, #7BB38C", "posavasos", False,
     "Set de 4 posavasos con borde ondulado para proteger tu mesa con estilo."),
    ("Kit Aprende Crochet", "Kits y materiales", 85000, 6, "#F4B6C2, #FFD966, #1F5C3F", "kit", True,
     "Incluye 2 ovillos de algodón, aguja ergonómica de 3,5 mm, marcadores, patrón impreso y acceso a nuestros videos."),
]

ENTRADAS = [
    ("5 consejos para cuidar tus tejidos", "posavasos",
     "Lavado, secado y guardado: así tus piezas de crochet durarán toda la vida.",
     "Los tejidos de algodón son resistentes, pero agradecen un poco de cuidado. Lávalos a mano con agua fría y un jabón suave, sin retorcerlos.\n\n"
     "Para secarlos, extiéndelos en horizontal sobre una toalla y a la sombra: así no se deforman ni pierden color.\n\n"
     "Si un punto se suelta, no lo cortes: escríbenos al chat y te enseñamos a repararlo.\n\n"
     "Guárdalos en un lugar seco, lejos del sol directo, y si quieres que huelan rico agrega una bolsita de lavanda.\n\n"
     "Y el consejo más importante: úsalos mucho. Un tejido guardado no abraza a nadie."),
    ("¿Qué es un amigurumi?", "oso",
     "La técnica japonesa de tejer muñequitos que conquistó al mundo (y a nuestro taller).",
     "Amigurumi viene del japonés «ami» (tejido) y «nuigurumi» (muñeco de peluche). Se teje en espiral con punto bajo, muy apretado, para que el relleno no se asome.\n\n"
     "Todo empieza con un anillo mágico de seis puntos. A partir de ahí se aumenta y se disminuye para dar forma a cabezas, cuerpos y orejitas.\n\n"
     "En Ovillito tardamos entre 6 y 12 horas en tejer cada personaje, y ninguno sale exactamente igual a otro. Por eso decimos que cada uno tiene su propia personalidad."),
    ("Detrás de cada puntada: nuestra historia", "kit",
     "Cómo una aguja heredada de la abuela se convirtió en un taller lleno de color.",
     "Ovillito nació en una mesa de comedor, con una aguja de crochet heredada y muchas ganas de regalar cosas hechas a mano.\n\n"
     "Primero fueron osos para los sobrinos, luego llaveros para las amigas y, sin darnos cuenta, un pequeño taller con pedidos de toda la ciudad.\n\n"
     "Hoy somos una comunidad: compartimos tutoriales, respondemos dudas en el chat y celebramos cada foto que nos mandan de sus tejidos. Gracias por ser parte."),
]

COMENTARIOS = [
    (0, "laura", "¡No sabía lo de la lavanda! Lo voy a probar con mi manta."),
    (0, "admin", "¡Nos cuentas cómo te va, Laura! A nosotras nos encanta el olorcito."),
    (1, "sofia", "Mi primer amigurumi fue un pulpo y quedó un poco chueco, pero lo amo."),
    (1, "mateo", "¿Cuánto relleno le ponen para que quede firme?"),
    (1, "admin", "Mateo, rellenamos poco a poco hasta que al apretar vuelve a su forma. ¡Mejor de más que de menos!"),
    (2, "valentina", "Qué bonita historia. Mi abuela también me enseñó a tejer."),
]

CHAT = [
    ("admin", "¡Bienvenidas y bienvenidos al chat de Ovillito! Aquí pueden preguntar lo que quieran sobre crochet."),
    ("laura", "¡Hola! ¿Hacen amigurumis personalizados? Quiero uno parecido a mi perrito."),
    ("admin", "¡Claro, Laura! Mándanos una foto por aquí y te cotizamos. Tardamos unos 5 días."),
    ("sofia", "¡Acabo de terminar mi primer granny square con el kit!"),
    ("daniel", "¿Qué número de aguja recomiendan para empezar?"),
    ("admin", "Daniel, para algodón mediano la de 3,5 mm es perfecta. Es la que viene en el kit."),
    ("cliente", "¡Me llegó el Osito Miel y es todavía más lindo en persona!"),
]

ENCUESTAS = {
    "cliente": (5, "Amigurumis", "instagram", "si", "Me encantan los colores pastel."),
    "laura": (5, "Hogar", "amigos", "si", "Quiero más mantas en tonos tierra."),
    "mateo": (4, "Kits y materiales", "tiktok", "si", "Los videos del kit me ayudaron mucho."),
    "sofia": (5, "Amigurumis", "instagram", "si", ""),
    "daniel": (3, "Accesorios", "google", "talvez", "El envío podría ser más rápido."),
    "valentina": (4, "Hogar", "feria", "si", "Las conocí en una feria y volví."),
    "andres": (2, "Accesorios", "otro", "no", "El gorro que quería estaba agotado."),
}

# Distancias aproximadas (km) y rumbo (grados) de cada cliente respecto a la tienda.
UBICACIONES = {
    "cliente": (0.4, 40), "laura": (1.8, 160), "mateo": (3.6, 250), "sofia": (0.9, 300),
    "daniel": (6.8, 200), "valentina": (2.5, 80), "andres": (11.0, 120),
}


class Command(BaseCommand):
    help = "Carga usuarios, productos, carrusel, blog, chat, videos, encuestas, ubicaciones y pedidos de demostración."

    def add_arguments(self, parser):
        parser.add_argument("--reiniciar", action="store_true",
                            help="Elimina pedidos, encuestas, chat, comentarios y ubicaciones antes de cargarlos.")

    @transaction.atomic
    def handle(self, *args, **opciones):
        rnd = random.Random(2026)
        if opciones["reiniciar"]:
            for modelo in (ItemPedido, Pedido, RespuestaEncuesta, MensajeChat, Comentario, Ubicacion):
                modelo.objects.all().delete()
            self.stdout.write("Datos de actividad eliminados.")

        usuarios = self._usuarios()
        categorias = self._categorias()
        productos = self._productos(categorias)
        self._carrusel()
        entradas = self._blog(usuarios)
        self._comentarios(entradas, usuarios)
        self._chat(usuarios)
        self._videos()
        self._encuestas(usuarios, categorias)
        self._ubicaciones(usuarios)
        self._pedidos(usuarios, productos, rnd)

        self.stdout.write(self.style.SUCCESS(
            "\nDatos de demostración listos.\n"
            "  Administrador: admin / Admin12345\n"
            "  Cliente:       cliente / Cliente12345\n"
        ))

    # --- Usuarios --------------------------------------------------------------
    def _usuario(self, username, clave, nombre, apellido, staff=False):
        usuario, creado = User.objects.get_or_create(username=username, defaults={
            "first_name": nombre, "last_name": apellido,
            "email": f"{username}@ovillito.test", "is_staff": staff, "is_superuser": staff,
        })
        if creado:
            usuario.set_password(clave)
            usuario.date_joined = timezone.now() - timedelta(days=random.Random(username).randint(3, 60))
            usuario.save()
        return usuario

    def _usuarios(self):
        usuarios = {"admin": self._usuario("admin", "Admin12345", "Valeria", "Ríos", staff=True)}
        for username, nombre, apellido in CLIENTES:
            usuarios[username] = self._usuario(username, "Cliente12345", nombre, apellido)
        self.stdout.write(f"Usuarios: {len(usuarios)}")
        return usuarios

    # --- Tienda ------------------------------------------------------------------
    def _categorias(self):
        resultado = {}
        for nombre, descripcion, orden in CATEGORIAS:
            cat, _ = Categoria.objects.get_or_create(nombre=nombre, defaults={"descripcion": descripcion, "orden": orden})
            resultado[nombre] = cat
        return resultado

    def _productos(self, categorias):
        resultado = []
        ahora = timezone.now()
        for i, (nombre, cat, precio, stock, colores, ilus, destacado, desc) in enumerate(PRODUCTOS):
            producto, _ = Producto.objects.get_or_create(nombre=nombre, defaults={
                "categoria": categorias[cat], "precio": precio, "stock": stock, "colores": colores,
                "ilustracion": ilus, "destacado": destacado, "descripcion": desc,
                "creado": ahora - timedelta(days=len(PRODUCTOS) - i),
            })
            resultado.append(producto)
        self.stdout.write(f"Productos: {len(resultado)}")
        return resultado

    def _carrusel(self):
        if Slide.objects.exists():
            return
        Slide.objects.create(titulo="Ovillito × Otoño", subtitulo="Nueva colección tejida a mano, en colores que abrazan",
                             texto_boton="Ver colección", enlace="#catalogo", color_fondo="mantequilla",
                             figura_izquierda="kit", figura_derecha="oso", orden=1)
        Slide.objects.create(titulo="Amigurumis con alma", subtitulo="Cada muñequito es único, como quien lo recibe",
                             texto_boton="Conocerlos", enlace="?categoria=amigurumis#catalogo", color_fondo="rosa",
                             figura_izquierda="conejo", figura_derecha="pulpo", orden=2)
        Slide.objects.create(titulo="Aprende a tejer", subtitulo="Videos y kits para empezar hoy mismo",
                             texto_boton="Ver videos", enlace=reverse("actividades:videos"), color_fondo="celeste",
                             figura_izquierda="flores", figura_derecha="cactus", orden=3)
        self.stdout.write("Carrusel: 3 diapositivas")

    # --- Actividades -------------------------------------------------------------
    def _blog(self, usuarios):
        resultado = []
        ahora = timezone.now()
        for i, (titulo, ilus, resumen, contenido) in enumerate(ENTRADAS):
            entrada, _ = EntradaBlog.objects.get_or_create(titulo=titulo, defaults={
                "ilustracion": ilus, "resumen": resumen, "contenido": contenido,
                "autor": usuarios["admin"], "creada": ahora - timedelta(days=12 - i * 5),
            })
            resultado.append(entrada)
        return resultado

    def _comentarios(self, entradas, usuarios):
        if Comentario.objects.exists():
            return
        ahora = timezone.now()
        for n, (indice, username, texto) in enumerate(COMENTARIOS):
            Comentario.objects.create(entrada=entradas[indice], usuario=usuarios[username], texto=texto,
                                      creado=ahora - timedelta(days=5 - n * 0.6))

    def _chat(self, usuarios):
        if MensajeChat.objects.exists():
            return
        ahora = timezone.now()
        for n, (username, texto) in enumerate(CHAT):
            MensajeChat.objects.create(usuario=usuarios[username], texto=texto,
                                       creado=ahora - timedelta(minutes=(len(CHAT) - n) * 23))

    def _videos(self):
        datos = [
            ("marca.mp4", "Conoce Ovillito", "marca", "0:09",
             "Un recorrido rápido por nuestros personajes y colecciones tejidas a mano."),
            ("cuidados.mp4", "3 cuidados para tus tejidos", "principiante", "0:12",
             "Cómo lavar, secar y guardar tus piezas de crochet para que duren toda la vida."),
        ]
        for archivo, titulo, nivel, duracion, descripcion in datos:
            ruta = SEMILLA / "videos" / archivo
            if Video.objects.filter(titulo=titulo).exists() or not ruta.exists():
                continue
            video = Video(titulo=titulo, nivel=nivel, duracion=duracion, descripcion=descripcion)
            with ruta.open("rb") as f:
                video.archivo.save(archivo, File(f), save=False)
            portada = ruta.with_suffix(".jpg")
            if portada.exists():
                with portada.open("rb") as f:
                    video.portada.save(portada.name, File(f), save=False)
            video.save()

    def _encuestas(self, usuarios, categorias):
        for username, (calif, cat, canal, recomendaria, comentario) in ENCUESTAS.items():
            RespuestaEncuesta.objects.get_or_create(usuario=usuarios[username], defaults={
                "calificacion": calif, "categoria_favorita": categorias[cat], "canal": canal,
                "recomendaria": recomendaria, "comentario": comentario,
            })

    def _ubicaciones(self, usuarios):
        if Ubicacion.objects.exists():
            return
        lat0, lng0 = settings.TIENDA["latitud"], settings.TIENDA["longitud"]
        for username, (km, rumbo) in UBICACIONES.items():
            dlat = km * math.cos(math.radians(rumbo)) / 111.32
            dlng = km * math.sin(math.radians(rumbo)) / (111.32 * math.cos(math.radians(lat0)))
            lat, lng = lat0 + dlat, lng0 + dlng
            Ubicacion.objects.create(usuario=usuarios[username], latitud=lat, longitud=lng,
                                     precision_m=random.Random(username).randint(8, 40),
                                     distancia_km=distancia_a_tienda(lat, lng), origen="gps")

    def _pedidos(self, usuarios, productos, rnd):
        if Pedido.objects.exists():
            return
        clientes = [usuarios[u] for u, _, _ in CLIENTES]
        disponibles = [p for p in productos]
        pesos = [5, 4, 4, 6, 3, 3, 2, 1, 4, 4, 5, 3]
        ahora = timezone.now()
        umbral = settings.TIENDA["envio_gratis_desde"]
        total = 0
        for dias_atras in range(13, -1, -1):
            # Más pedidos en la semana reciente para que se vea la tendencia.
            n = rnd.choice([0, 1, 1, 2]) if dias_atras > 6 else rnd.choice([1, 2, 2, 3])
            for _ in range(n):
                fecha = ahora - timedelta(days=dias_atras, hours=rnd.randint(0, 9), minutes=rnd.randint(0, 59))
                elegidos = rnd.sample(range(len(disponibles)), k=rnd.choice([1, 1, 2, 3]))
                lineas = [(disponibles[i], rnd.choice([1, 1, 1, 2])) for i in elegidos]
                lineas = [l for l in lineas if rnd.random() < pesos[productos.index(l[0])] / 5 + 0.2] or lineas[:1]
                subtotal = sum(p.precio * c for p, c in lineas)
                envio = 0 if subtotal >= umbral else settings.TIENDA["costo_envio"]
                estado = ("entregado" if dias_atras > 7 else "enviado" if dias_atras > 3
                          else "preparando" if dias_atras > 1 else "pendiente")
                pedido = Pedido.objects.create(usuario=rnd.choice(clientes), creado=fecha, subtotal=subtotal,
                                               envio=envio, total=subtotal + envio, estado=estado)
                for producto, cantidad in lineas:
                    ItemPedido.objects.create(pedido=pedido, producto=producto, nombre=producto.nombre,
                                              precio=producto.precio, cantidad=cantidad)
                total += 1
        self.stdout.write(f"Pedidos: {total}")
