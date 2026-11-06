# Cómo trabajamos en equipo

## Reglas

1. Nadie trabaja directo en `main`. Cada tema va en su propia rama.
2. Todo llega a `main` por Pull Request, con la revisión de al menos un compañero.
3. Solo una persona a la vez toca `templates/base.html` y `static/css/tienda.css`.
4. Las contraseñas y llaves van en `.env`, que nunca se sube.

## Recorrido de un cambio

```bash
git switch main
git pull
git switch -c feature/nombre-del-tema
```

Trabaja y guarda seguido:

```bash
git status
git add .
git commit -m "Agrega el filtro por talla"
```

Sube tu rama y pide revisión:

```bash
git push -u origin feature/nombre-del-tema
gh pr create --fill
```

## Probar el trabajo de un compañero

```bash
git fetch
git switch feature/nombre-del-tema
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py cargar_datos_demo
```

## Antes de abrir un Pull Request

```bash
ruff check .
pytest
```

Si cambias un modelo, crea la migración con `python manage.py makemigrations` e inclúyela en
tu commit. Si cambias CSS o JS, sube el valor de `VERSION_ESTATICOS` en `tiendaWeb/settings.py`.
Las imágenes que deban verlas todos van en `static/`, porque `media/` y `db.sqlite3` no se suben.

## Nombres

- Código, modelos y comentarios en español, como el resto del proyecto.
- Ramas: `feature/...` para funciones nuevas y `fix/...` para correcciones.
- Commits en presente y con una idea cada uno: "Agrega", "Corrige", "Actualiza".
