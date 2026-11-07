from django.urls import path

from . import views

app_name = "pedidos"

urlpatterns = [
    path("compra/", views.compra, name="compra"),
    path("pedidos/", views.lista, name="lista"),
    path("pedidos/<str:folio>/", views.detalle, name="detalle"),
    path("pedidos/<str:folio>/pagar/", views.pagar, name="pagar"),
    path("pedidos/<str:folio>/descartar/", views.descartar, name="descartar"),
    path("pedidos/<str:folio>/solicitud/", views.solicitud, name="solicitud"),
    path("pagos/simulado/<str:folio>/", views.pago_simulado, name="pago_simulado"),
    path("pagos/webhook/", views.webhook_stripe, name="webhook"),
]
