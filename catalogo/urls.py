from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("catalogo/", views.lista, name="lista"),
    path("catalogo/<slug:slug>/", views.lista, name="categoria"),
    path("producto/<slug:slug>/", views.detalle, name="producto"),
    path("api/cotizar/", views.api_cotizar, name="api_cotizar"),
]
