import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone

from tienda.models import ILUSTRACIONES, Categoria, unique_slug

YOUTUBE_ID = re.compile(
    r"(?:youtube(?:-nocookie)?\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/|live/)|youtu\.be/)([A-Za-z0-9_-]{11})"
)


class Ubicacion(models.Model):
    ORIGENES = [("gps", "GPS del dispositivo"), ("manual", "Marcada en el mapa")]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ubicaciones")
    latitud = models.FloatField(validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitud = models.FloatField(validators=[MinValueValidator(-180), MaxValueValidator(180)])
    precision_m = models.FloatField("precisión (m)", null=True, blank=True)
    distancia_km = models.FloatField("distancia a la tienda (km)")
    origen = models.CharField(max_length=10, choices=ORIGENES, default="gps")
    creada = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-creada"]
        verbose_name = "ubicación"
        verbose_name_plural = "ubicaciones"

    def __str__(self):
        return f"{self.usuario} · {self.distancia_km:.2f} km"


class EntradaBlog(models.Model):
    titulo = models.CharField("título", max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    resumen = models.CharField(max_length=260)
    contenido = models.TextField()
    ilustracion = models.CharField("ilustración", max_length=20, choices=ILUSTRACIONES, default="flores")
    imagen = models.ImageField(upload_to="blog/", blank=True)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="entradas")
    publicada = models.BooleanField(default=True)
    creada = models.DateTimeField(default=timezone.now)
    actualizada = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creada"]
        verbose_name = "entrada del blog"
        verbose_name_plural = "entradas del blog"

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.titulo)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("actividades:blog_detalle", args=[self.slug])

    def imagen_url(self):
        return self.imagen.url if self.imagen else static(f"img/productos/{self.ilustracion}.svg")


class Comentario(models.Model):
    entrada = models.ForeignKey(EntradaBlog, on_delete=models.CASCADE, related_name="comentarios")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comentarios")
    texto = models.TextField(max_length=800)
    creado = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["creado"]

    def __str__(self):
        return f"{self.usuario}: {self.texto[:40]}"


class MensajeChat(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mensajes_chat")
    texto = models.CharField(max_length=500)
    creado = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["creado"]
        verbose_name = "mensaje del chat"
        verbose_name_plural = "mensajes del chat"

    def __str__(self):
        return f"{self.usuario}: {self.texto[:40]}"


class Video(models.Model):
    NIVELES = [
        ("principiante", "Principiante"),
        ("intermedio", "Intermedio"),
        ("avanzado", "Avanzado"),
        ("marca", "Conoce la marca"),
    ]
    titulo = models.CharField("título", max_length=120)
    descripcion = models.TextField("descripción", blank=True)
    nivel = models.CharField(max_length=20, choices=NIVELES, default="principiante")
    url_youtube = models.URLField("enlace de YouTube", blank=True,
                                  help_text="Pega el enlace del video (youtube.com/watch?v=… o youtu.be/…).")
    archivo = models.FileField(
        "archivo de video", upload_to="videos/", blank=True,
        validators=[FileExtensionValidator(["mp4", "webm", "ogg"])],
        help_text="O sube un archivo MP4/WebM.",
    )
    portada = models.ImageField(upload_to="videos/portadas/", blank=True,
                                help_text="Imagen opcional que se muestra antes de reproducir un video subido.")
    duracion = models.CharField("duración", max_length=10, blank=True, help_text="Ejemplo: 4:30")
    creado = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return self.titulo

    def clean(self):
        if not self.url_youtube and not self.archivo:
            raise ValidationError("Agrega un enlace de YouTube o sube un archivo de video.")
        if self.url_youtube and not YOUTUBE_ID.search(self.url_youtube):
            raise ValidationError({"url_youtube": "No se reconoce el enlace como un video de YouTube."})

    @property
    def youtube_id(self):
        if not self.url_youtube:
            return ""
        coincidencia = YOUTUBE_ID.search(self.url_youtube)
        return coincidencia.group(1) if coincidencia else ""


class RespuestaEncuesta(models.Model):
    CALIFICACIONES = [(i, str(i)) for i in range(1, 6)]
    CANALES = [
        ("instagram", "Instagram"),
        ("tiktok", "TikTok"),
        ("amigos", "Recomendación de amigos"),
        ("feria", "Feria o mercado artesanal"),
        ("google", "Búsqueda en Google"),
        ("otro", "Otro"),
    ]
    RECOMENDARIA = [("si", "Sí, seguro"), ("talvez", "Tal vez"), ("no", "No")]

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name="respuesta_encuesta")
    calificacion = models.PositiveSmallIntegerField("calificación", choices=CALIFICACIONES)
    categoria_favorita = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True,
                                           verbose_name="categoría favorita")
    canal = models.CharField("¿cómo nos conociste?", max_length=20, choices=CANALES)
    recomendaria = models.CharField("¿nos recomendarías?", max_length=10, choices=RECOMENDARIA)
    comentario = models.TextField(blank=True, max_length=600)
    creada = models.DateTimeField(default=timezone.now)
    actualizada = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creada"]
        verbose_name = "respuesta de encuesta"
        verbose_name_plural = "respuestas de encuesta"

    def __str__(self):
        return f"{self.usuario} · {self.calificacion}/5"


class Foto(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="fotos")
    imagen = models.ImageField(upload_to="fotos/%Y/%m/")
    descripcion = models.CharField("descripción", max_length=140, blank=True)
    creada = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-creada"]

    def __str__(self):
        return f"Foto de {self.usuario} ({self.creada:%d/%m/%Y})"

    def delete(self, *args, **kwargs):
        almacenamiento, nombre = self.imagen.storage, self.imagen.name
        super().delete(*args, **kwargs)
        if nombre:
            almacenamiento.delete(nombre)
