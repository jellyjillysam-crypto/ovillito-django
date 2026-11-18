from django.contrib import admin

from .models import Categoria, ItemPedido, Pedido, Producto, Slide


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "slug", "orden")
    prepopulated_fields = {"slug": ("nombre",)}


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "precio", "stock", "destacado", "activo")
    list_filter = ("categoria", "activo", "destacado")
    search_fields = ("nombre", "descripcion")
    list_editable = ("precio", "stock", "activo")


@admin.register(Slide)
class SlideAdmin(admin.ModelAdmin):
    list_display = ("titulo", "color_fondo", "orden", "activo")
    list_editable = ("orden", "activo")


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("__str__", "usuario", "creado", "total", "estado")
    list_filter = ("estado",)
    inlines = [ItemPedidoInline]
