# Ovillito · Tienda de crochet hecha a mano (Django)

> *«Cada puntada, un abrazo.»*

Proyecto web en **Django 5.2** para una tienda de crochet y amigurumis. La estética se basa en el
diseño de referencia (fondo crema, banner amarillo con título manuscrito, menú tipo píldora,
grilla de productos con muestras de color y carrito lateral), adaptada a una marca original.

---

## 1. Instalación y ejecución

Requisitos: Python 3.10 o superior.

```bash
python -m venv venv
```

```bash
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

```bash
pip install -r requirements.txt
```

```bash
python manage.py migrate
```

```bash
python manage.py cargar_demo
```

```bash
python manage.py runserver
```

Abre **http://127.0.0.1:8000/**: siempre se entra primero al login.

| Rol | Usuario | Contraseña | Home después del login |
|---|---|---|---|
| Administrador | `admin` | `Admin12345` | Panel de métricas (`/panel/`) |
| Cliente | `cliente` | `Cliente12345` | Tienda con carrusel (`/tienda/`) |

> En el login hay que elegir **Cliente** o **Administrador**. Si el tipo elegido no coincide con la
> cuenta, el acceso se rechaza con un mensaje claro.

Para reiniciar los datos de actividad (pedidos, chat, encuestas, ubicaciones):
`python manage.py cargar_demo --reiniciar`

Para ejecutar las pruebas automatizadas (51 pruebas):
`python manage.py test`

---

## 2. Correspondencia con la rúbrica

| Punto de la rúbrica | Dónde está | Detalle |
|---|---|---|
| Entrar primero al login y luego a un home distinto por rol | `cuentas/views.py` → `inicio`, `login_view` | `/` redirige al login; tras iniciar sesión, el administrador va a `/panel/` y el cliente a `/tienda/`. |
| Login con 2 tipos de usuario | `cuentas/forms.py`, `cuentas/permisos.py` | Selector Cliente / Administrador. Administrador = `is_staff`. Decorador `admin_requerido` y `AdminRequeridoMixin` devuelven 403 a clientes. |
| Admin con métricas | `panel/views.py` → `dashboard`, `templates/panel/dashboard.html`, `static/js/panel.js` | Ingresos, pedidos, clientes, ticket promedio, ventas por día y por categoría, resultados de la encuesta, mapa de clientes, productos más vendidos y stock bajo. Cada gráfica tiene vista de tabla. |
| Producto / servicio | `tienda/` | Tienda de crochet: catálogo con filtros, detalle, carrito lateral, pedidos. |
| Identidad: logotipo / imagotipo | `static/img/isotipo.svg`, página **Nuestra marca** (`/marca/`) | Isotipo (ovillo con orejas de oso), logotipo e imagotipo en fondo claro y oscuro. |
| Identidad: paleta de colores | `/marca/`, variables en `static/css/ovillito.css` | Chocolate `#4A2812`, Crema `#FFF6DE`, Mantequilla `#FFD966`, Verde bosque `#1F5C3F`, Rosa algodón `#F4B6C2`, Celeste `#A8D5EA`, Caramelo `#C9803A`. |
| Identidad: slogan | `config/settings.py` → `MARCA` | «Cada puntada, un abrazo.» |
| Identidad: tipos de letra | `static/fonts/` (servidas localmente) | **Fraunces** (títulos), **Nunito** (textos), **Gochi Hand** (acentos manuscritos). |
| Menú | `templates/base.html`, `templates/panel/base_panel.html` | Menú tipo píldora con desplegables (Tienda, Comunidad), buscador, cuenta y carrito; versión hamburguesa en móvil. Barra lateral para el administrador. |
| Carrusel en la página principal | `templates/tienda/home.html`, `static/js/carrusel.js` | Autoplay, flechas, puntos, teclado, deslizamiento táctil y botón de pausa. Las diapositivas se administran en Django admin (modelo `Slide`). |
| Capturar la ubicación | `static/js/ubicacion.js`, `actividades/views.py` → `ubicacion_guardar` | API de geolocalización del navegador; se guarda en el modelo `Ubicacion`. Si el GPS falla, se puede marcar la ubicación con un clic en el mapa. |
| Mapa (qué tan cerca estás de la tienda) | `/actividades/ubicacion/`, `actividades/geo.py` | Mapa Leaflet + OpenStreetMap con la tienda, tu ubicación y la línea entre ambas. Distancia por fórmula de Haversine y tiempos estimados caminando, en bici y en carro. |
| CRUD | `panel/views.py` | CRUD completo de **Productos**, **Entradas del blog** y **Videos** (crear, listar, editar, eliminar). Además: cambio de estado de pedidos. |
| Blog (chat) | `/actividades/blog/` y `/actividades/chat/` | Blog con comentarios de los clientes + chat de la comunidad en vivo (actualización automática cada 3 s). |
| Videos | `/actividades/videos/` | Acepta enlaces de YouTube (se incrustan) o archivos MP4/WebM. Incluye dos videos de la marca generados para el proyecto. |
| Encuesta | `/actividades/encuesta/` | 5 preguntas (calificación, categoría favorita, canal, recomendación, comentario). Resultados en el panel. |
| Tomar fotos | `/actividades/fotos/`, `static/js/camara.js` | Cámara del dispositivo (`getUserMedia`): activar, tomar foto, repetir, cambiar cámara y guardar en la galería. Alternativa para subir una imagen. |

---

## 3. Notas importantes

* **Cámara y GPS** solo funcionan en `http://localhost`/`127.0.0.1` o en un sitio con **HTTPS**
  (es una regla de los navegadores). Para probar desde el celular en la misma red se necesita HTTPS.
* **Ubicación de la tienda:** edita `TIENDA` en `config/settings.py` (o las variables de entorno
  `TIENDA_LATITUD`, `TIENDA_LONGITUD`, `TIENDA_DIRECCION`). La dirección de ejemplo es ficticia.
* **Mapas y videos de YouTube** necesitan conexión a internet. Leaflet, Chart.js y las tipografías
  están incluidas en `static/vendor` y `static/fonts`, así que el resto del sitio funciona sin conexión.
* **Pagos:** el checkout crea el pedido y descuenta el stock, pero no realiza cobros reales.
* **Imágenes de productos:** se incluyen ilustraciones SVG originales; desde el CRUD se puede subir
  la foto real de cada producto y reemplaza la ilustración.
* **Producción:** define `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0` y `DJANGO_ALLOWED_HOSTS`, y ejecuta
  `python manage.py collectstatic`.

---

## 4. Estructura

```
ovillito/
├── config/            Configuración (settings, urls)
├── cuentas/           Login con roles, registro, permisos
├── tienda/            Catálogo, carrusel, carrito, pedidos, identidad de marca
├── actividades/       Ubicación y mapa, blog, chat, videos, encuesta, fotos
├── panel/             Home del administrador (métricas) y CRUD
│   ├── management/commands/cargar_demo.py   Datos de demostración
│   └── semilla/videos/                      Videos de la marca
├── templates/         Plantillas HTML
└── static/            CSS, JS, ilustraciones, tipografías y librerías
```

## 5. Créditos de terceros

* [Leaflet](https://leafletjs.com/) 1.9.4 (BSD-2) y mosaicos de © colaboradores de OpenStreetMap.
* [Chart.js](https://www.chartjs.org/) 4.4.1 (MIT).
* Tipografías Fraunces, Nunito y Gochi Hand (SIL Open Font License) vía Fontsource.
* Ilustraciones, logotipo y videos: creados para este proyecto.
