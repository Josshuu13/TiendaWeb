from django.urls import path

from . import views

app_name = "carrito"

urlpatterns = [
    path("", views.ver, name="ver"),
    path("agregar/", views.agregar, name="agregar"),
    path("contador/", views.contador, name="contador"),
    path("linea/<str:linea_id>/", views.actualizar, name="actualizar"),
    path("linea/<str:linea_id>/quitar/", views.quitar, name="quitar"),
]
