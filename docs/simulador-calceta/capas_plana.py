"""
Convierte el render de Blender en las capas del simulador (720 × 900):
  cuerpo.png    gris + transparencia: luz, sombras y tejido del cuerpo
  detalles.png  gris + transparencia: puño, talón y punta
  sombra.png    sombra suave en el piso
Uso: python capas_plana.py <carpeta del render> <carpeta de salida>
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ORIGEN, DESTINO = Path(sys.argv[1]), Path(sys.argv[2])
DESTINO.mkdir(parents=True, exist_ok=True)
ANCHO, ALTO = 720, 900

render = np.asarray(Image.open(ORIGEN / "belleza.png"), dtype=np.float64)
render /= 65535 if render.max() > 255 else 255
silueta = np.load(ORIGEN / "silueta.npy").astype(np.float64)
puno, talon, punta = np.load(ORIGEN / "zonas.npy").astype(np.float64)

luz = 0.299 * render[..., 0] + 0.587 * render[..., 1] + 0.114 * render[..., 2]
dentro = silueta > 0.98
referencia = np.percentile(luz[dentro], 98.5)
gris = np.clip(luz / referencia * 0.965, 0, 1)
print(f"referencia {referencia:.3f}; gris medio {gris[dentro].mean():.3f}")

# Fuera de la silueta el render puede ser el piso; se extiende el gris de la orilla para que,
# al reducir la imagen, las orillas no se oscurezcan.
from scipy import ndimage as nd  # noqa: E402

# La orilla del render toca el piso y sale oscura: se usa el gris de 4 px más adentro.
nucleo = nd.binary_erosion(dentro, iterations=4)
_, (iy, ix) = nd.distance_transform_edt(~nucleo, return_indices=True)
dentro = nucleo
gris = np.where(dentro, gris, gris[iy, ix])

detalles = np.clip(puno + talon + punta, 0, 1) * silueta
cuerpo = np.clip(silueta - detalles, 0, 1)
# Sombra: junto a la orilla está la malla del render (no es sombra); ahí se copia la sombra
# de unos píxeles más afuera y se suma una sombra de contacto suave.
cerca = nd.binary_dilation(silueta > 0.02, iterations=7)
_, (sy, sx) = nd.distance_transform_edt(cerca, return_indices=True)
alfa = render[..., 3]
sombra = np.where(cerca, alfa[sy, sx], alfa)
contacto = nd.gaussian_filter((silueta > 0.5).astype(float), 3.5) * 0.30
sombra = np.clip((sombra * 1.1 + contacto) * (1 - silueta), 0, 1)
# La sombra se desvanece antes de llegar a la orilla del lienzo (sin bordes rectos).
alto_px, ancho_px = sombra.shape
yy, xx = np.mgrid[0:alto_px, 0:ancho_px]
margen = np.minimum.reduce([xx, yy, ancho_px - 1 - xx, alto_px - 1 - yy]) / 90.0
sombra *= np.clip(margen, 0, 1) ** 1.5


def reducir(arreglo):
    img = Image.fromarray((np.clip(arreglo, 0, 1) * 65535).astype(np.uint16))
    img = img.convert("I").resize((ANCHO, ALTO), Image.LANCZOS)
    return np.clip(np.asarray(img, dtype=np.float64) / 65535, 0, 1)


def guardar(nombre, luz_, alfa):
    luz_ = np.where(alfa > 0, luz_, 0)
    pix = np.stack([np.round(luz_ * 255), np.round(alfa * 255)], axis=-1).astype(np.uint8)
    Image.fromarray(pix, mode="LA").save(DESTINO / nombre, optimize=True)


g = reducir(gris)
guardar("cuerpo.png", g, reducir(cuerpo))
guardar("detalles.png", g, reducir(detalles))
guardar("sombra.png", np.zeros_like(g), reducir(sombra))

# Datos útiles para calceta.js: dónde está la pierna (zona del diseño).
s = reducir(silueta) > 0.5
filas = np.nonzero(s.any(axis=1))[0]
p = reducir(puno) > 0.5
fin_puno = np.nonzero(p.any(axis=1))[0].max()
print("calceta de y", filas[0], "a", filas[-1], "; el puño termina en y", fin_puno)
for y in (fin_puno + 20, fin_puno + 150, fin_puno + 300):
    cols = np.nonzero(s[y])[0]
    print(f"  y={y}: x de {cols[0]} a {cols[-1]}")
print("listo:", DESTINO)
