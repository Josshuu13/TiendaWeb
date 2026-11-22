"""
Render de la calceta plana (vista desde arriba) en Blender 5 con Cycles.

Uso: Blender -b --factory-startup -P calceta_plana.py -- <carpeta de preparar.py> <muestras> [energia]
Salida: belleza.png (1440 × 1800, RGBA 16 bits): calceta blanca de tejido con su sombra.
"""
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
CARPETA = Path(args[0])
MUESTRAS = int(args[1]) if len(args) > 1 else 64
ENERGIA = float(args[2]) if len(args) > 2 else 1.0
RELIEVE = float(args[3]) if len(args) > 3 else 1.0

bpy.ops.wm.read_factory_settings(use_empty=True)
escena = bpy.context.scene

silueta = np.load(CARPETA / "silueta.npy")
altura = np.load(CARPETA / "altura.npy")
angulo = np.load(CARPETA / "angulo.npy")
zonas = np.load(CARPETA / "zonas.npy")
ALTO, ANCHO = silueta.shape
M_POR_PX = 0.000175  # metros por píxel del lienzo doble

# ------------------------------------------------------------------ malla (una celda por 2 px)
paso = 2
sil = silueta[::paso, ::paso]
alt = altura[::paso, ::paso]
ang = angulo[::paso, ::paso]
puno = zonas[0][::paso, ::paso]
h, w = sil.shape
dentro = sil > 0.02
# Un borde extra de celdas para que la malla cubra toda la orilla suave.
from_mask = dentro.copy()
for _ in range(2):
    m = from_mask.copy()
    m[1:, :] |= from_mask[:-1, :]
    m[:-1, :] |= from_mask[1:, :]
    m[:, 1:] |= from_mask[:, :-1]
    m[:, :-1] |= from_mask[:, 1:]
    from_mask = m
usar = from_mask
indice = -np.ones((h, w), dtype=np.int64)
filas, cols = np.nonzero(usar)
indice[filas, cols] = np.arange(len(filas))
x = (cols * paso - ANCHO / 2) * M_POR_PX
y = (ALTO / 2 - filas * paso) * M_POR_PX
z = alt[filas, cols]
verts = np.column_stack([x, y, z])

a = usar[:-1, :-1] & usar[:-1, 1:] & usar[1:, :-1] & usar[1:, 1:]
f_r, f_c = np.nonzero(a)
caras = np.column_stack([
    indice[f_r, f_c], indice[f_r + 1, f_c], indice[f_r + 1, f_c + 1], indice[f_r, f_c + 1],
])
malla = bpy.data.meshes.new("calceta")
malla.vertices.add(len(verts))
malla.vertices.foreach_set("co", verts.astype(np.float32).ravel())
malla.loops.add(caras.size)
malla.loops.foreach_set("vertex_index", caras.ravel().astype(np.int32))
malla.polygons.add(len(caras))
malla.polygons.foreach_set("loop_start", (np.arange(len(caras)) * 4).astype(np.int32))
malla.polygons.foreach_set("loop_total", np.full(len(caras), 4, dtype=np.int32))
malla.update(calc_edges=True)
malla.validate()
malla.polygons.foreach_set("use_smooth", np.ones(len(caras), dtype=bool))
print("malla:", len(verts), "vértices,", len(caras), "caras")

# UV del tejido: columnas a lo largo de la calceta (vertical en la pierna, a lo largo del pie).
a_v = ang[filas, cols]
dcol = np.column_stack([-np.sin(a_v), -np.cos(a_v)])
dperp = np.column_stack([np.cos(a_v), -np.sin(a_v)])
pos = np.column_stack([x, y])
ANCHO_TILE, ALTO_TILE = 16 * 0.0022, 16 * 0.0020   # 16 × 16 puntadas por mosaico
u = (pos * dperp).sum(1) / ANCHO_TILE
v = (pos * dcol).sum(1) / ALTO_TILE
lazos = caras.ravel()
uv = malla.uv_layers.new(name="tejido")
uv.data.foreach_set("uv", np.column_stack([u[lazos], v[lazos]]).astype(np.float32).ravel())
at = malla.attributes.new("puno", "FLOAT", "POINT")
at.data.foreach_set("value", puno[filas, cols].astype(np.float32))

calceta = bpy.data.objects.new("calceta", malla)
escena.collection.objects.link(calceta)

# ------------------------------------------------------------------ material de tejido
mat = bpy.data.materials.new("tejido")
mat.use_nodes = True
nt = mat.node_tree
N, L = nt.nodes, nt.links
N.clear()


def nodo(tipo, **props):
    n = N.new(tipo)
    for k, val in props.items():
        setattr(n, k, val)
    return n


def textura(nombre):
    img = bpy.data.images.load(str(CARPETA / nombre))
    img.colorspace_settings.name = "Non-Color"
    t = nodo("ShaderNodeTexImage", image=img, interpolation="Cubic")
    return t


uvn = nodo("ShaderNodeUVMap", uv_map="tejido")
tj, tr = textura("jersey.png"), textura("resorte.png")
tension = nodo("ShaderNodeTexNoise")
tension.inputs["Scale"].default_value = 45.0
tension.inputs["Detail"].default_value = 2.0
centrar = nodo("ShaderNodeVectorMath", operation="SUBTRACT")
L.new(tension.outputs["Color"], centrar.inputs[0])
centrar.inputs[1].default_value = (0.5, 0.5, 0.5)
escala = nodo("ShaderNodeVectorMath", operation="SCALE")
L.new(centrar.outputs["Vector"], escala.inputs[0])
escala.inputs["Scale"].default_value = 0.035
uv_ondulado = nodo("ShaderNodeVectorMath", operation="ADD")
L.new(uvn.outputs["UV"], uv_ondulado.inputs[0])
L.new(escala.outputs["Vector"], uv_ondulado.inputs[1])
L.new(uv_ondulado.outputs["Vector"], tj.inputs["Vector"])
L.new(uv_ondulado.outputs["Vector"], tr.inputs["Vector"])
attr = nodo("ShaderNodeAttribute", attribute_name="puno")
mezcla = nodo("ShaderNodeMix", data_type="FLOAT")
L.new(attr.outputs["Fac"], mezcla.inputs["Factor"])
L.new(tj.outputs["Color"], mezcla.inputs["A"])
L.new(tr.outputs["Color"], mezcla.inputs["B"])

pelusa = nodo("ShaderNodeTexNoise")
pelusa.inputs["Scale"].default_value = 2600.0
pelusa.inputs["Detail"].default_value = 4.0
alto_total = nodo("ShaderNodeMath", operation="MULTIPLY_ADD")
L.new(pelusa.outputs["Fac"], alto_total.inputs[0])
alto_total.inputs[1].default_value = 0.18
L.new(mezcla.outputs["Result"], alto_total.inputs[2])
bump = nodo("ShaderNodeBump")
bump.inputs["Strength"].default_value = 0.85 * RELIEVE
bump.inputs["Distance"].default_value = 0.0007
L.new(alto_total.outputs["Value"], bump.inputs["Height"])

# Las hendiduras entre puntadas quedan un poco más oscuras (oclusión del hilo).
tono = nodo("ShaderNodeMapRange")
tono.inputs["To Min"].default_value = 0.50
tono.inputs["To Max"].default_value = 0.84
L.new(mezcla.outputs["Result"], tono.inputs["Value"])
bsdf = nodo("ShaderNodeBsdfPrincipled")
L.new(tono.outputs["Result"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.95
bsdf.inputs["Sheen Weight"].default_value = 0.6
bsdf.inputs["Sheen Roughness"].default_value = 0.5
bsdf.inputs["Subsurface Weight"].default_value = 0.12
bsdf.inputs["Subsurface Radius"].default_value = (0.0015, 0.0015, 0.0015)
L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
out = nodo("ShaderNodeOutputMaterial")
L.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
calceta.data.materials.append(mat)

# ------------------------------------------------------------------ piso, luces y cámara
bpy.ops.mesh.primitive_plane_add(size=3.0, location=(0, 0, -0.0002))
piso = bpy.context.active_object
piso.is_shadow_catcher = True

mundo = bpy.data.worlds.new("estudio")
mundo.use_nodes = True
fondo = mundo.node_tree.nodes["Background"]
fondo.inputs["Color"].default_value = (1, 1, 1, 1)
fondo.inputs["Strength"].default_value = 0.22
escena.world = mundo


def luz(nombre, pos, energia, tamano):
    datos = bpy.data.lights.new(nombre, "AREA")
    datos.energy, datos.size = energia * ENERGIA, tamano
    obj = bpy.data.objects.new(nombre, datos)
    obj.location = pos
    obj.rotation_euler = (Vector((0, 0, 0)) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    escena.collection.objects.link(obj)


luz("ventana", (-0.75, 0.55, 0.42), 34, 0.9)      # luz principal, rasante, arriba a la izquierda
luz("relleno", (0.6, -0.35, 0.9), 5, 1.2)
luz("cenital", (0.0, 0.0, 1.2), 6, 1.5)

cam = bpy.data.cameras.new("camara")
cam.type = "ORTHO"
cam.ortho_scale = ALTO * M_POR_PX
camara = bpy.data.objects.new("camara", cam)
camara.location = (0, 0, 1.0)
escena.collection.objects.link(camara)
escena.camera = camara

# ------------------------------------------------------------------ render
escena.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "METAL"
prefs.get_devices()
for d in prefs.devices:
    d.use = True
escena.cycles.device = "GPU"
escena.cycles.samples = MUESTRAS
escena.cycles.use_denoising = True
escena.render.resolution_x, escena.render.resolution_y = ANCHO, ALTO
escena.render.film_transparent = True
escena.view_settings.view_transform = "Standard"
escena.view_settings.look = "None"
escena.render.image_settings.file_format = "PNG"
escena.render.image_settings.color_mode = "RGBA"
escena.render.image_settings.color_depth = "16"
escena.render.filepath = str(CARPETA / "belleza.png")
bpy.ops.render.render(write_still=True)
print("render listo")
