"""
Prepara la calceta plana para Blender a partir de la silueta real de los calcetines Santa Claus.

Salida (carpeta indicada), todo al doble del tamaño final (1440 × 1800):
  silueta.npy   0..1 con orilla suave y limpia
  zonas.npy     [3, alto, ancho]: puño, talón, punta (0..1)
  altura.npy    volumen de la calceta en metros (como un cojín plano)
  angulo.npy    dirección de las columnas del tejido (radianes; 0 = vertical)
  jersey.png, resorte.png   relieve del tejido (mosaico sin uniones)
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as nd

AQUI = Path(__file__).parent
SALIDA = Path(sys.argv[1])
SALIDA.mkdir(parents=True, exist_ok=True)

ANCHO, ALTO = 1440, 1800          # doble del lienzo final (720 × 900)
MM_POR_PX = 0.175                 # 0.35 mm por píxel en el lienzo final

foto = np.asarray(Image.open(AQUI / "foto-calcetines-santa.png").convert("RGB"), dtype=np.float64) / 255
vision = np.asarray(Image.open(AQUI / "mascara-foto.png").convert("L"), dtype=np.float64) / 255
H0, W0 = vision.shape
yy, xx = np.mgrid[0:H0, 0:W0].astype(np.float64)

# Calceta de enfrente (misma costura que antes) y orilla superior recta.
COSTURA = [(0, 139), (10, 139), (40, 137), (92, 138), (105, 140), (120, 140), (135, 136), (150, 129),
           (165, 119), (180, 109), (200, 99), (215, 93), (228, 90), (240, 89), (250, 90), (258, 93),
           (263, 97), (267, 103)]
borde = np.interp(yy[:, 0], [p[0] for p in COSTURA], [p[1] for p in COSTURA])
calceta = vision * np.clip(xx - borde[:, None] + 0.5, 0, 1) * np.clip(yy - 11.5, 0, 1)

R, G, B = foto[..., 0], foto[..., 1], foto[..., 2]
peso_rojo = np.clip((R / (R + G + B + 1e-6) - 0.42) / 0.18, 0, 1)
blanco = (peso_rojo < 0.5) & (calceta > 0.5)


def componente(m, punto):
    etiquetas, _ = nd.label(nd.binary_closing(m, iterations=2))
    return nd.binary_fill_holes(etiquetas == etiquetas[punto])


talon = componente(blanco & (xx > 186) & (yy > 112) & (yy < 178), (150, 222)).astype(float)
punta = componente(blanco & (yy > 212), (245, 130)).astype(float)

# ---------------------------------------------------------------- escalar al lienzo
x0, y0, x1, y1 = 86, 11, 247, 266
esc = (ALTO * 0.905) / (y1 - y0)
ancho_c, alto_c = round((x1 - x0) * esc), round((y1 - y0) * esc)
dx, dy = (ANCHO - ancho_c) // 2 + 10, (ALTO - alto_c) // 2 - 20
print(f"escala {esc:.2f} (al doble); calceta de {ancho_c}×{alto_c} en ({dx},{dy})")


def ampliar(m, suavizado):
    img = Image.fromarray((m[y0:y1, x0:x1] * 255).astype(np.uint8)).resize((ancho_c, alto_c), Image.BICUBIC)
    lienzo = np.zeros((ALTO, ANCHO))
    lienzo[dy:dy + alto_c, dx:dx + ancho_c] = np.asarray(img, dtype=np.float64) / 255
    lienzo = nd.gaussian_filter(lienzo, suavizado)
    # Orilla limpia: corte en 0.5 con un degradado de 1.5 px (antialias).
    return np.clip((lienzo - 0.5) / 0.06 + 0.5, 0, 1)


silueta_foto = ampliar(calceta, 9)
Y, X = np.mgrid[0:ALTO, 0:ANCHO].astype(np.float64)


def a_lienzo(xo, yo):
    return dx + (xo - x0) * esc, dy + (yo - y0) * esc


# Pierna limpia: las orillas de una calceta plana son rectas. Se ajusta una recta a cada lado.
filas = np.nonzero(silueta_foto.max(axis=1) > 0.5)[0]
y_arriba = filas[0] + 34
_, y_tobillo = a_lienzo(0, 108)
izq, der, ys = [], [], []
for y in range(int(y_arriba + 60), int(y_tobillo)):
    cols = np.nonzero(silueta_foto[y] > 0.5)[0]
    if len(cols):
        izq.append(cols[0])
        der.append(cols[-1])
        ys.append(y)
ys = np.array(ys, dtype=float)
ai, bi = np.polyfit(ys, izq, 1)
ad, bd = np.polyfit(ys, der, 1)
pierna = (np.clip((X - (ai * Y + bi)) / 1.5 + 0.5, 0, 1) * np.clip(((ad * Y + bd) - X) / 1.5 + 0.5, 0, 1)
          * np.clip((Y - y_arriba) / 1.5 + 0.5, 0, 1))
w = np.clip((Y - (y_tobillo - 150)) / 230, 0, 1)
w = w * w * (3 - 2 * w)
mezcla = pierna * (1 - w) + silueta_foto * w
mezcla = nd.gaussian_filter(mezcla, 7)
silueta = np.clip((mezcla - 0.5) / 0.06 + 0.5, 0, 1)

# Talón: copa redonda en la esquina de atrás. Punta: tapa con orilla curva.
talon_g = ampliar(nd.gaussian_filter(talon, 1.5), 22) * silueta
# Punta: orilla casi horizontal como en la foto, un poco más baja en los lados (tapa redonda).
xa, ya = a_lienzo(88, 229)
xb, yb = a_lienzo(176, 222)
pend = (yb - ya) / (xb - xa)
x_medio = (xa + xb) / 2
linea = ya + pend * (X - xa) + 0.00022 * (X - x_medio) ** 2
punta_g = np.clip((Y - linea) / 1.5 + 0.5, 0, 1) * silueta

# Puño: banda superior con orilla recta.
ALTO_PUNO = 0.145 * alto_c
puno_g = np.clip((y_arriba + ALTO_PUNO - Y) / 1.5 + 0.5, 0, 1) * silueta
talon_g *= 1 - puno_g
punta_g *= 1 - puno_g

# ---------------------------------------------------------------- volumen (cojín)
dentro = silueta > 0.5
d = nd.distance_transform_edt(dentro) * MM_POR_PX / 1000  # metros a la orilla
D, GROSOR = 0.016, 0.0085
perfil = np.sqrt(np.clip(1 - (1 - np.clip(d / D, 0, 1)) ** 2, 0, 1))
rng = np.random.default_rng(11)
ondas = nd.gaussian_filter(rng.normal(0, 1, (ALTO, ANCHO)), 55)
ondas /= ondas.std()
altura = GROSOR * perfil * (1 + 0.07 * ondas)


def pliegue(xa, ya, xb, yb, ancho, alto_m):
    """Pliegue suave a lo largo del segmento (en píxeles del lienzo doble)."""
    vx, vy = xb - xa, yb - ya
    largo2 = vx * vx + vy * vy
    t = np.clip(((X - xa) * vx + (Y - ya) * vy) / largo2, 0, 1)
    dist = np.hypot(X - (xa + t * vx), Y - (ya + t * vy))
    caida = np.sin(np.pi * t) ** 0.8
    return alto_m * np.exp(-(dist / ancho) ** 2) * caida


ax, ay = a_lienzo(139, 118)      # empeine (frente del tobillo)
bx, by = a_lienzo(200, 150)      # hacia el talón
cx, cy = a_lienzo(150, 135)
ex, ey = a_lienzo(205, 120)
altura += pliegue(ax, ay, bx, by, 30, -0.0019) * dentro
altura += pliegue(cx, cy, ex, ey, 22, 0.0013) * dentro
altura += pliegue(*a_lienzo(145, 160), *a_lienzo(190, 175), 34, -0.0012) * dentro
altura += pliegue(*a_lienzo(118, 196), *a_lienzo(170, 206), 30, -0.0009) * dentro
# Talón y punta un poco más abultados; el puño un poco más grueso (resorte).
altura += 0.0011 * nd.gaussian_filter(talon_g, 18) * perfil
altura += 0.0008 * nd.gaussian_filter(punta_g, 18) * perfil
altura += 0.0005 * nd.gaussian_filter(puno_g, 5) * perfil
for zona in (talon_g, punta_g, puno_g):
    orilla = np.abs(nd.gaussian_filter(zona, 2.5) - 0.5) < 0.25
    altura += 0.00045 * nd.gaussian_filter(orilla.astype(float), 2.0) * perfil
altura = nd.gaussian_filter(altura, 1.2) * dentro

# ---------------------------------------------------------------- dirección del tejido
# Pierna: columnas verticales. Pie: a lo largo del pie (del talón a la punta).
tx_, ty_ = a_lienzo(215, 150)
px_, py_ = a_lienzo(125, 245)
ang_pie = math.atan2(-(px_ - tx_), (py_ - ty_))  # ángulo desde la vertical
_, ty_tobillo = a_lienzo(0, 128)
_, ty_pie = a_lienzo(0, 178)
peso_pie = np.clip((Y - ty_tobillo) / (ty_pie - ty_tobillo), 0, 1)
peso_pie = peso_pie * peso_pie * (3 - 2 * peso_pie)
angulo = ang_pie * peso_pie
print(f"ángulo del pie: {math.degrees(ang_pie):.1f}°")

np.save(SALIDA / "silueta.npy", silueta.astype(np.float32))
np.save(SALIDA / "zonas.npy", np.stack([puno_g, talon_g, punta_g]).astype(np.float32))
np.save(SALIDA / "altura.npy", altura.astype(np.float32))
np.save(SALIDA / "angulo.npy", angulo.astype(np.float32))


# ---------------------------------------------------------------- relieve del tejido
def tejido(px=1024, columnas=16, filas=16, resorte=False):
    """Punto jersey: cada puntada son dos 'piernas' de hilo que forman una V, con torsión del hilo."""
    y, x = np.mgrid[0:px, 0:px].astype(np.float64) / px
    h = np.zeros((px, px))
    cw, rh = 1 / columnas, 1 / filas
    azar = np.random.default_rng(9 if resorte else 8)
    var_alto = azar.uniform(0.82, 1.08, (filas, columnas))
    var_ancho = azar.uniform(0.88, 1.12, (filas, columnas))
    var_mov = azar.normal(0, 0.05, (filas, columnas))
    for ox in (-1, 0, 1):
        for oy in (-1, 0, 1):
            ic = ((np.floor(x / cw) + ox) % columnas).astype(int)
            ir = ((np.floor(y / rh) + oy) % filas).astype(int)
            cx = (np.floor(x / cw) + 0.5 + ox + var_mov[ir, ic]) * cw
            cy = (np.floor(y / rh) + 0.5 + oy) * rh
            col = (np.floor(x / cw) + ox) % 2
            for lado in (-1, 1):
                # Pierna de la V: de arriba-afuera hacia abajo-centro.
                ax_, ay_ = cx + lado * cw * 0.30, cy - rh * 0.55
                bx_, by_ = cx + lado * cw * 0.02, cy + rh * 0.50
                vx, vy = bx_ - ax_, by_ - ay_
                l2 = vx * vx + vy * vy
                t = np.clip(((x - ax_) * vx + (y - ay_) * vy) / l2, 0, 1)
                qx, qy = ax_ + t * vx, ay_ + t * vy
                r = np.hypot(x - qx, y - qy) / (cw * 0.24 * var_ancho[ir, ic])
                hilo = np.sqrt(np.clip(1 - r * r, 0, 1))
                # Torsión: rayitas diagonales sobre el hilo.
                torsion = 0.12 * np.sin(2 * np.pi * (t * 7 + lado * (x - qx) / (cw * 0.24) * 0.9))
                curva = np.sin(np.pi * np.clip(t * 0.9 + 0.05, 0, 1)) ** 0.35
                forma = hilo * (0.85 + torsion) * curva * var_alto[ir, ic]
                if resorte:
                    forma = forma * np.where(col == 0, 1.0, 0.55)
                h = np.maximum(h, forma)
    if resorte:
        col = np.floor(x / cw) % 2
        h = h + 0.18 * (col == 0)
    fibra = nd.gaussian_filter(np.random.default_rng(4).normal(0, 1, (px, px)), 1.2, mode="wrap")
    h = h + 0.05 * fibra / fibra.std()
    h = (h - h.min()) / (h.max() - h.min())
    Image.fromarray((h * 65535).astype(np.uint16)).save(SALIDA / ("resorte.png" if resorte else "jersey.png"))


tejido()
tejido(resorte=True)
# Vista previa de la silueta y las zonas.
vista = np.dstack([silueta * 0.3 + puno_g * 0.7, silueta * 0.3 + talon_g * 0.7, silueta * 0.3 + punta_g * 0.7])
Image.fromarray((vista * 255).astype(np.uint8)).resize((720, 900)).save(SALIDA / "zonas-vista.png")
alt = altura / altura.max()
Image.fromarray((alt * 255).astype(np.uint8)).resize((720, 900)).save(SALIDA / "altura-vista.png")
print("listo:", SALIDA)
