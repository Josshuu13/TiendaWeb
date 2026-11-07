from django import forms

from .models import Pedido, SolicitudPosventa

ENTIDADES = [
    "Aguascalientes", "Baja California", "Baja California Sur", "Campeche", "Chiapas",
    "Chihuahua", "Ciudad de México", "Coahuila", "Colima", "Durango", "Estado de México",
    "Guanajuato", "Guerrero", "Hidalgo", "Jalisco", "Michoacán", "Morelos", "Nayarit",
    "Nuevo León", "Oaxaca", "Puebla", "Querétaro", "Quintana Roo", "San Luis Potosí",
    "Sinaloa", "Sonora", "Tabasco", "Tamaulipas", "Tlaxcala", "Veracruz", "Yucatán", "Zacatecas",
]


class DatosEnvioForm(forms.ModelForm):
    """Dirección de entrega. autocomplete permite que el navegador la llene."""

    entidad = forms.ChoiceField(
        label="Estado",
        choices=[("", "Elige tu estado")] + [(e, e) for e in ENTIDADES],
        widget=forms.Select(attrs={"autocomplete": "address-level1"}),
    )

    class Meta:
        model = Pedido
        fields = [
            "nombre_destinatario", "telefono", "calle", "colonia",
            "codigo_postal", "ciudad", "entidad", "referencias",
        ]
        widgets = {
            "nombre_destinatario": forms.TextInput(attrs={"autocomplete": "name"}),
            "telefono": forms.TextInput(attrs={"autocomplete": "tel-national", "inputmode": "numeric"}),
            "calle": forms.TextInput(attrs={"autocomplete": "street-address"}),
            "codigo_postal": forms.TextInput(attrs={"autocomplete": "postal-code", "inputmode": "numeric"}),
            "ciudad": forms.TextInput(attrs={"autocomplete": "address-level2"}),
        }


class SolicitudForm(forms.ModelForm):
    class Meta:
        model = SolicitudPosventa
        fields = ["tipo", "motivo"]
        widgets = {
            "tipo": forms.HiddenInput,
            "motivo": forms.Textarea(attrs={"rows": 3}),
        }
