"""Pruebas de registro e inicio de sesión."""
import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse

pytestmark = pytest.mark.django_db
DATOS = {
    "first_name": "Ana", "email": "Ana@Example.com",
    "password1": "clave-de-prueba-123", "password2": "clave-de-prueba-123",
}


def test_registro_crea_cuenta_e_inicia_sesion(client):
    r = client.post(reverse("cuentas:registro"), DATOS)
    assert r.status_code == 302
    usuario = get_user_model().objects.get()
    assert usuario.username == usuario.email == "ana@example.com"
    assert usuario.check_password("clave-de-prueba-123")
    assert "_auth_user_id" in client.session


def test_correo_repetido_se_rechaza_sin_importar_mayusculas(client, usuario):
    r = client.post(reverse("cuentas:registro"), DATOS)
    assert r.status_code == 200
    assert "Ya existe una cuenta" in r.content.decode()


def test_contrasena_debil_se_rechaza(client):
    r = client.post(reverse("cuentas:registro"), {**DATOS, "password1": "1234", "password2": "1234"})
    assert r.status_code == 200
    assert get_user_model().objects.count() == 0


def test_entrar_con_correo_en_mayusculas(client, usuario):
    r = client.post(reverse("cuentas:entrar"), {"username": "ANA@example.com", "password": "clave-de-prueba-123"})
    assert r.status_code == 302


def test_contrasena_incorrecta_no_entra(client, usuario):
    r = client.post(reverse("cuentas:entrar"), {"username": "ana@example.com", "password": "mala"})
    assert r.status_code == 200
    assert "_auth_user_id" not in client.session


def test_registro_no_redirige_a_otros_sitios(client):
    r = client.post(reverse("cuentas:registro") + "?next=https://sitio-malo.example/", {
        **DATOS, "next": "https://sitio-malo.example/",
    })
    assert r.url == reverse("pedidos:lista")


def test_salir_exige_post(client, usuario):
    client.force_login(usuario)
    assert client.get(reverse("cuentas:salir")).status_code == 405
    client.post(reverse("cuentas:salir"))
    assert "_auth_user_id" not in client.session


def test_recuperar_contrasena_envia_enlace(client, usuario):
    client.post(reverse("cuentas:recuperar"), {"email": "ana@example.com"})
    assert len(mail.outbox) == 1
    assert "/cuentas/recuperar/" in mail.outbox[0].body


@pytest.mark.parametrize("nombre", [
    "cuentas:entrar", "cuentas:registro", "cuentas:recuperar", "cuentas:recuperar_enviado", "cuentas:recuperar_listo",
])
def test_paginas_de_cuenta_cargan(client, nombre):
    assert client.get(reverse(nombre)).status_code == 200
