"""Runs INSIDE Blender (headless): builds one validated 3D scene template and renders it to a PNG sequence.

    blender -b --factory-startup --python blender_scene.py -- params.json

Only this file is executed. It reads plain data (template id, short texts, colours, duration, size, an optional image
path the worker placed next to it) and never evaluates anything from the parameters. Writes done.json (or error.json).
"""

import json
import math
import sys
import traceback
from pathlib import Path

import bpy  # provided by Blender at run time

ARGS = json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text(encoding="utf-8"))
OUT = Path(ARGS["out_dir"])


def rgb(hex_color: str, a: float = 1.0):
    h = hex_color.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return (*[c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb], a)


def material(name: str, color, metallic=0.0, rough=0.4, emission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = color
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    if emission:
        b.inputs["Emission Color"].default_value = color
        b.inputs["Emission Strength"].default_value = emission
    return m


def setup(fps: int, frames: int, w: int, h: int, bg):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = engine
            break
        except TypeError:
            continue
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
    sc.render.fps, sc.frame_start, sc.frame_end = fps, 1, frames
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = str(OUT / "f_")
    world = bpy.data.worlds.new("w")
    sc.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = bg
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    sc.view_settings.view_transform = "Standard"
    try:
        sc.eevee.taa_render_samples = 32
    except AttributeError:
        pass
    return sc


def camera(sc, frames: int, orbit_deg: float, dist: float, height: float):
    bpy.ops.object.empty_add(location=(0, 0, 0))
    pivot = bpy.context.object
    bpy.ops.object.camera_add(location=(0, -dist, height))
    cam = bpy.context.object
    cam.data.lens = 50
    cam.parent = pivot
    c = cam.constraints.new("TRACK_TO")
    c.target, c.track_axis, c.up_axis = pivot, "TRACK_NEGATIVE_Z", "UP_Y"
    sc.camera = cam
    pivot.rotation_euler = (0, 0, math.radians(-orbit_deg / 2))
    pivot.keyframe_insert("rotation_euler", frame=1)
    pivot.rotation_euler = (0, 0, math.radians(orbit_deg / 2))
    pivot.keyframe_insert("rotation_euler", frame=frames)
    cam.location.y = -dist * 1.25
    cam.keyframe_insert("location", frame=1)
    cam.location.y = -dist
    cam.keyframe_insert("location", frame=frames)
    return cam


def lights(accent):
    """Key (front-left), fill (front-right, soft) and an accent rim from behind, all aimed at the subject."""
    bpy.ops.object.empty_add(location=(0, 0, 0))
    target = bpy.context.object
    out = []
    for loc, energy, size, color in (((-4, -5, 4), 1800, 4, (1, 1, 1)), ((5, -4, 1.5), 600, 6, (1, 1, 1)),
                                     ((2, 5, 3), 1500, 3, accent[:3])):
        bpy.ops.object.light_add(type="AREA", location=loc)
        lamp = bpy.context.object
        lamp.data.energy, lamp.data.size, lamp.data.color = energy, size, color
        c = lamp.constraints.new("TRACK_TO")
        c.target, c.track_axis, c.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
        out.append(lamp)
    return out


def text_3d(sc, a, frames):
    accent, text_c = rgb(a["accent"]), rgb(a["text_color"])
    bpy.ops.object.text_add(location=(0, 0, 0))
    t = bpy.context.object
    t.data.body = a["text"]
    t.data.align_x, t.data.align_y = "CENTER", "CENTER"
    t.data.extrude, t.data.bevel_depth, t.data.bevel_resolution = 0.12, 0.025, 4
    t.data.size = 1.0
    t.rotation_euler = (math.radians(90), 0, 0)
    t.data.materials.append(material("type", text_c, metallic=0.6, rough=0.25))
    bpy.context.view_layer.update()
    width = max(t.dimensions.x, 0.1)
    frame_w = 2.3 if ARGS["height"] > ARGS["width"] else 4.2  # portrait frames are narrow: keep the title inside
    t.scale = (min(frame_w / width, 1.6),) * 3
    # rise and settle
    t.location.z = -2.5
    t.keyframe_insert("location", frame=1)
    t.location.z = 0
    t.keyframe_insert("location", frame=max(2, int(frames * 0.35)))
    if a.get("subtitle"):
        bpy.ops.object.text_add(location=(0, 0, -0.9))
        s = bpy.context.object
        s.data.body = a["subtitle"]
        s.data.align_x = "CENTER"
        s.data.size, s.data.extrude = 0.28, 0.02
        s.rotation_euler = (math.radians(90), 0, 0)
        s.data.materials.append(material("sub", accent, emission=2.0))
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -1.6))
    bpy.context.object.data.materials.append(material("floor", rgb(a["background"]), metallic=0.3, rough=0.15))
    lights(accent)
    camera(sc, frames, a["orbit"], 7.5, 1.2)


def product_turntable(sc, a, frames):
    accent = rgb(a["accent"])
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    card = bpy.context.object
    card.scale = (1.6, 0.08, 2.4) if a.get("portrait", True) else (2.4, 0.08, 1.6)
    bpy.ops.object.modifier_add(type="BEVEL")
    card.modifiers[0].width, card.modifiers[0].segments = 0.06, 6
    card.data.materials.append(material("body", rgb("#1a1a1a"), metallic=0.7, rough=0.25))
    # the image sits on its own plane just in front of the card (a plane's UVs cover the whole image exactly)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -0.085, 0), rotation=(math.radians(90), 0, 0))
    face = bpy.context.object
    face.scale = (card.scale.x * 0.94, card.scale.z * 0.94, 1)
    face.parent = card
    face.matrix_parent_inverse = card.matrix_world.inverted()
    m = material("face", rgb("#ffffff"), rough=0.3)
    if a.get("image"):  # the screenshot/product image glows slightly, like a lit screen or a backlit print
        tex = m.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(a["image"])
        bsdf = m.node_tree.nodes["Principled BSDF"]
        m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 0.6
    face.data.materials.append(m)
    card.rotation_euler = (0, 0, math.radians(-25))
    card.keyframe_insert("rotation_euler", frame=1)
    card.rotation_euler = (0, 0, math.radians(25))
    card.keyframe_insert("rotation_euler", frame=frames)
    bpy.ops.mesh.primitive_cylinder_add(radius=2.2, depth=0.25, location=(0, 0, -1.4 if a.get("portrait", True) else -1.0))
    bpy.context.object.data.materials.append(material("plinth", rgb(a["background"]), metallic=0.5, rough=0.2))
    bpy.ops.mesh.primitive_torus_add(major_radius=2.25, minor_radius=0.03, location=(0, 0, -1.27 if a.get("portrait", True) else -0.87))
    bpy.context.object.data.materials.append(material("ring", accent, emission=6.0))
    lights(accent)
    camera(sc, frames, a["orbit"], 6.2, 0.8)


TEMPLATES = {"text_3d": text_3d, "product_turntable": product_turntable}

try:
    OUT.mkdir(parents=True, exist_ok=True)
    frames = int(round(ARGS["duration"] * ARGS["fps"]))
    scene = setup(ARGS["fps"], frames, ARGS["width"], ARGS["height"], rgb(ARGS["background"]))
    TEMPLATES[ARGS["template"]](scene, ARGS, frames)
    bpy.ops.render.render(animation=True)
    (OUT / "done.json").write_text(json.dumps({"frames": frames, "engine": scene.render.engine, "blender": bpy.app.version_string}))
except Exception:  # noqa: BLE001 — the worker reads this file; Blender has no other channel back
    (OUT / "error.json").write_text(json.dumps({"error": traceback.format_exc()[-3000:]}))
