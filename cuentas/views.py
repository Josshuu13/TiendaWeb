from django.conf import settings
from django.contrib.auth import login
from django.shortcuts import redirect, render, resolve_url
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import RegistroForm


def _destino_seguro(request):
    """Respeta ?next= solo si apunta a esta misma tienda (evita redirecciones a otros sitios)."""
    destino = request.POST.get("next") or request.GET.get("next") or ""
    if url_has_allowed_host_and_scheme(destino, {request.get_host()}, request.is_secure()):
        return destino
    return resolve_url(settings.LOGIN_REDIRECT_URL)


def registro(request):
    if request.user.is_authenticated:
        return redirect("pedidos:lista")
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        login(request, usuario)
        return redirect(_destino_seguro(request))
    return render(request, "cuentas/registro.html", {"form": form, "next": request.GET.get("next", "")})
