#!/usr/bin/env bash
# Pasos que ejecuta Render en cada publicación.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Solo para la primera publicación: el plan gratuito no tiene terminal.
# Define CARGAR_DEMO=1 y DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD, publica y luego
# borra esas variables, porque volver a cargar la demo restablece las existencias.
if [ "$CARGAR_DEMO" = "1" ]; then
  python manage.py cargar_datos_demo
  python manage.py createsuperuser --no-input || true
fi
