"""Blender mask producer for the pinned T-094 e907 shot."""

import argparse
import json
import sys
from pathlib import Path

import bpy


def material(eyes):
    """A flat byte ID for the cup and each front-facing procedural pupil."""
    mat = bpy.data.materials.new("Readability IDs")
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()

    def math_node(operation, a, b):
        node = tree.nodes.new("ShaderNodeMath")
        node.operation = operation
        for slot, value in zip(node.inputs, (a, b)):
            if isinstance(value, (float, int)):
                slot.default_value = value
            else:
                tree.links.new(value, slot)
        return node.outputs[0]

    label = tree.nodes.new("ShaderNodeObjectInfo").outputs["Object Index"]
    coords = tree.nodes.new("ShaderNodeTexCoord")
    xyz = tree.nodes.new("ShaderNodeSeparateXYZ")
    tree.links.new(coords.outputs["Generated"], xyz.inputs[0])
    x = math_node("SUBTRACT", xyz.outputs["X"], 0.5)
    z = math_node("SUBTRACT", xyz.outputs["Z"], 0.5)
    front = math_node("LESS_THAN", xyz.outputs["Y"], 0.5)
    # eye_material_felt uses the layered iris ramp, optionally corrected for eye scale.
    # In Generated coordinates the authored unit-sphere radius is halved.
    keep = math_node("GREATER_THAN", label, 254.5)
    for ids, config in eyes:
        radius = config["iris"]["pupil"] / 2
        sx, _, sz = config["scale"]
        eye_x = math_node("MULTIPLY", x, sx / sz) if config["felt"].get("round_iris") else x
        rho_sq = math_node("ADD", math_node("MULTIPLY", eye_x, eye_x), math_node("MULTIPLY", z, z))
        disc = math_node("LESS_THAN", rho_sq, radius * radius)
        member = math_node("MAXIMUM", *(math_node("COMPARE", label, i) for i in ids))
        pupil = math_node("MULTIPLY", member, math_node("MULTIPLY", disc, front))
        keep = math_node("MAXIMUM", keep, pupil)
    byte = math_node("DIVIDE", math_node("MULTIPLY", label, keep), 255)
    emission = tree.nodes.new("ShaderNodeEmission")
    tree.links.new(byte, emission.inputs["Color"])
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(emission.outputs[0], out.inputs["Surface"])
    return mat


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cast", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--frames", nargs=2, type=int)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    cast = json.loads(args.cast.read_text(encoding="utf-8"))
    scene = bpy.context.scene
    assert scene.camera.name == "shot_camera"
    cup = scene.objects["prop.cup"]
    for obj in scene.objects:
        if obj.pass_index:
            obj.pass_index = 0
    cup.pass_index = 255
    eyes = []
    for character, labels in (("boy", (51, 102)), ("girl", (153, 204))):
        entry = cast[character]
        spec_path = Path(entry["master"]).with_name("spec.resolved.json")
        config = json.loads(spec_path.read_text(encoding="utf-8"))["face"]["eyes"]
        assert config["shader"] == "felt/1"
        eyes.append((labels, config))
        root = next(c for c in scene.collection.children if c.override_library and
                    c.override_library.reference.name == entry["character_id"])
        objects = {o.override_library.reference.name if o.override_library else o.name: o
                   for o in root.all_objects}
        for side, label in zip(("L", "R"), labels):
            objects[f"eye.{side}"].pass_index = label
        if character == "girl":
            objects["glasses_lens"].hide_render = True

    scene.view_layers[0].material_override = material(eyes)
    scene.world = bpy.data.worlds.new("Black background")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes.get("Background").inputs["Strength"].default_value = 0
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 1
    scene.cycles.device = "CPU"
    scene.cycles.max_bounces = 0
    scene.cycles.use_denoising = False
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.pixel_filter_type = "BOX"
    scene.cycles.seed = 0
    scene.camera.data.dof.use_dof = False
    scene.render.use_motion_blur = False
    scene.render.use_persistent_data = True
    scene.render.film_transparent = False
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "Raw"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    scene.render.dither_intensity = 0
    image = scene.render.image_settings
    image.file_format, image.color_mode, image.color_depth = "PNG", "BW", "8"
    if args.frames:
        first, last = args.frames
        assert scene.frame_start <= first <= last <= scene.frame_end
        scene.frame_start, scene.frame_end = first, last
    for group in ("visible", "cup_only"):
        if group == "cup_only":
            for obj in scene.objects:
                if obj.type not in ("CAMERA", "EMPTY", "ARMATURE") and obj != cup:
                    obj.hide_render = True
        folder = args.out.resolve() / group
        folder.mkdir(parents=True, exist_ok=True)
        scene.render.filepath = str(folder / "frame_")
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
