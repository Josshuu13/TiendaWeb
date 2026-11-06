from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("catalogo/", views.lista, name="lista"),
    path("catalogo/<slug:slug>/", views.lista, name="categoria"),
    path("producto/<slug:slug>/", views.detalle, name="producto"),
    path("temporada/<slug:slug>/", views.temporada, name="temporada"),
    path("ayuda/", views.ayuda, name="ayuda"),
    path("privacidad/", views.privacidad, name="privacidad"),
    path("terminos/", views.terminos, name="terminos"),
    path("robots.txt", views.robots, name="robots"),
    path("salud/", views.salud, name="salud"),
    path("api/cotizar/", views.api_cotizar, name="api_cotizar"),
]
