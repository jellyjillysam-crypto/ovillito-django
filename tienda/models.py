import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")

# Ilustraciones incluidas en static/img (se usan si el producto no tiene foto).
ILUSTRACIONES = [
    ("oso", "Oso amigurumi"),
    ("conejo", "Conejo amigurumi"),
    ("pulpo", "Pulpo amigurumi"),
    ("fresa", "Llavero de fresa"),
    ("bolso", "Bolso tejido"),
    ("gorro", "Gorro con pompón"),
    ("bufanda", "Bufanda"),
    ("manta", "Manta granny"),
    ("flores", "Ramo de flores"),
    ("cactus", "Cactus en maceta"),
    ("posavasos", "Posavasos"),
    ("kit", "Kit de crochet"),
]


def unique_slug(instancia, texto, campo="slug"):
    base = slugify(texto)[:60] or "item"
    slug, n = base, 2
    modelo = type(instancia)
    while modelo.objects.filter(**{campo: slug}).exclude(pk=instancia.pk).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


def validar_colores(valor):
    for color in [c.strip() for c in valor.split(",") if c.strip()]:
        if not HEX_COLOR.match(color):
            raise ValidationError(f"«{color}» no es un color válido. Usa el formato #RRGGBB.")


class Categoria(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, blank=True)
    descripcion = models.TextField(blank=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "categoría"
        verbose_name_plural = "categorías"

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.nombre)
        super().save(*args, **kwargs)


class ProductoQuerySet(models.QuerySet):
    def activos(self):
        return self.filter(activo=True)

    def con_ventas(self):
        return self.annotate(
            unidades_vendidas=models.functions.Coalesce(
                models.Sum("items_pedido__cantidad"), 0
            )
        )


class Producto(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="productos")
    nombre = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    descripcion = models.TextField("descripción")
    precio = models.PositiveIntegerField(help_text="Precio en pesos, sin puntos ni decimales.")
    stock = models.PositiveIntegerField(default=0)
    colores = models.CharField(
        max_length=200, blank=True, validators=[validar_colores],
        help_text="Colores disponibles en formato #RRGGBB separados por comas.",
    )
    imagen = models.ImageField(upload_to="productos/", blank=True,
                               help_text="Foto del producto. Si no hay foto se usa la ilustración.")
    ilustracion = models.CharField("ilustración", max_length=20, choices=ILUSTRACIONES, default="oso")
    destacado = models.BooleanField(default=False, help_text="Se muestra con tarjeta grande en el catálogo.")
    activo = models.BooleanField(default=True, help_text="Desmárcalo para ocultarlo de la tienda.")
    creado = models.DateTimeField(default=timezone.now)
    actualizado = models.DateTimeField(auto_now=True)

    objects = ProductoQuerySet.as_manager()

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.nombre)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("tienda:producto", args=[self.slug])

    @property
    def disponible(self):
        return self.stock > 0

    @property
    def stock_bajo(self):
        return 0 < self.stock <= 3

    def lista_colores(self):
        return [c.strip() for c in self.colores.split(",") if HEX_COLOR.match(c.strip())]

    def imagen_url(self):
        if self.imagen:
            return self.imagen.url
        return static(f"img/productos/{self.ilustracion}.svg")


class Slide(models.Model):
    """Diapositiva del carrusel del home de clientes."""

    COLORES = [
        ("mantequilla", "Amarillo mantequilla"),
        ("rosa", "Rosa algodón"),
        ("celeste", "Celeste cielo"),
        ("menta", "Verde menta"),
    ]
    titulo = models.CharField("título", max_length=80)
    subtitulo = models.CharField("subtítulo", max_length=140, blank=True)
    texto_boton = models.CharField(max_length=40, default="Ver colección")
    enlace = models.CharField(max_length=200, default="#catalogo")
    color_fondo = models.CharField(max_length=20, choices=COLORES, default="mantequilla")
    figura_izquierda = models.CharField(max_length=20, choices=ILUSTRACIONES, default="kit")
    figura_derecha = models.CharField(max_length=20, choices=ILUSTRACIONES, default="oso")
    imagen = models.ImageField(upload_to="carrusel/", blank=True,
                               help_text="Opcional: imagen panorámica que reemplaza las figuras.")
    orden = models.PositiveSmallIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "diapositiva del carrusel"
        verbose_name_plural = "carrusel"

    def __str__(self):
        return self.titulo


class Pedido(models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("preparando", "Tejiendo / preparando"),
        ("enviado", "Enviado"),
        ("entregado", "Entregado"),
    ]
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pedidos")
    creado = models.DateTimeField(default=timezone.now)
    subtotal = models.PositiveIntegerField(default=0)
    envio = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    nota = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return f"Pedido #{self.pk:05d}"

    @property
    def numero(self):
        return f"OV-{self.pk:05d}"


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True, related_name="items_pedido")
    nombre = models.CharField(max_length=120)
    precio = models.PositiveIntegerField()
    cantidad = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.cantidad} × {self.nombre}"

    @property
    def subtotal(self):
        return self.precio * self.cantidad
