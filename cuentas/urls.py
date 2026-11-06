"""Usa las vistas de autenticación de Django con plantillas propias."""
from django.conf import settings
from django.contrib.auth import views as auth
from django.urls import path, reverse_lazy

from . import views
from .forms import EntrarForm

app_name = "cuentas"

urlpatterns = [
    path("registro/", views.registro, name="registro"),
    path("entrar/", auth.LoginView.as_view(
        template_name="cuentas/entrar.html", authentication_form=EntrarForm,
        redirect_authenticated_user=True,
    ), name="entrar"),
    path("salir/", auth.LogoutView.as_view(), name="salir"),
    path("recuperar/", auth.PasswordResetView.as_view(
        template_name="cuentas/recuperar.html",
        email_template_name="cuentas/correo_recuperar.txt",
        subject_template_name="cuentas/correo_recuperar_asunto.txt",
        extra_email_context={"nombre_tienda": settings.NOMBRE_TIENDA},
        success_url=reverse_lazy("cuentas:recuperar_enviado"),
    ), name="recuperar"),
    path("recuperar/enviado/", auth.PasswordResetDoneView.as_view(
        template_name="cuentas/recuperar_enviado.html",
    ), name="recuperar_enviado"),
    path("recuperar/<uidb64>/<token>/", auth.PasswordResetConfirmView.as_view(
        template_name="cuentas/recuperar_nueva.html",
        success_url=reverse_lazy("cuentas:recuperar_listo"),
    ), name="recuperar_nueva"),
    path("recuperar/listo/", auth.PasswordResetCompleteView.as_view(
        template_name="cuentas/recuperar_listo.html",
    ), name="recuperar_listo"),
]
