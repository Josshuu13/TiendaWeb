"""
Formularios de cuentas.

El cliente entra con su correo. Django necesita un nombre de usuario, así que se usa
el mismo correo en minúsculas. Se conserva el modelo de usuario estándar de Django.
"""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

Usuario = get_user_model()


class RegistroForm(UserCreationForm):
    first_name = forms.CharField(
        label="Nombre", max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "given-name", "autofocus": True}),
    )
    email = forms.EmailField(
        label="Correo", max_length=150, widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("first_name", "email")

    def clean_email(self):
        correo = self.cleaned_data["email"].strip().lower()
        if Usuario.objects.filter(username=correo).exists():
            raise ValidationError("Ya existe una cuenta con este correo.")
        return correo

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.username = usuario.email
        if commit:
            usuario.save()
        return usuario


class EntrarForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Correo"
        self.fields["username"].widget = forms.EmailInput(
            attrs={"autocomplete": "email", "autofocus": True},
        )

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()
