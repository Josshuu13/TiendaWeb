# Cómo se hizo la calceta del personalizador

La calceta que se ve en `/producto/calcetas-personalizables/` es un render de Blender, no un
dibujo. Se siguió la misma idea que el moño: una imagen en gris por zona que el navegador pinta
con la fusión *multiply* (`static/js/calceta.js`).

1. **Silueta real.** Se tomó la foto de los calcetines Santa Claus del catálogo
   (`foto-calcetines-santa.png`) y se recortó con macOS Vision (`recortar.swift` →
   `mascara-foto.png`). `preparar.py` endereza la pierna, deja recta la orilla del puño y dibuja
   el talón y la punta con formas redondas.
2. **Volumen y tejido.** `preparar.py` calcula el volumen de una calceta acostada (como un cojín
   plano, con pliegues en el tobillo y costuras en el talón y la punta) y genera el relieve del
   punto jersey y del resorte del puño.
3. **Render.** `calceta_plana.py` arma la malla en Blender 5 y la renderiza con Cycles desde
   arriba, con luz de ventana y sombra en el piso.
4. **Capas.** `capas_plana.py` convierte el render en `static/simulador/calceta/cuerpo.png`,
   `detalles.png` y `sombra.png` (720 × 900).

Para volver a generarla (necesita Blender 5 y un entorno de Python con numpy, scipy y Pillow):

```bash
python docs/simulador-calceta/preparar.py /tmp/calceta
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P docs/simulador-calceta/calceta_plana.py -- /tmp/calceta 256 0.3
python docs/simulador-calceta/capas_plana.py /tmp/calceta static/simulador/calceta
```

Si se cambia la silueta, hay que revisar la zona del diseño (`ZONA`) en `static/js/calceta.js`.
