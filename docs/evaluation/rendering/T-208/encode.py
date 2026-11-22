"""Encode a rendered 48-frame PNG sequence in Blender at its baked 24 fps."""
from pathlib import Path
import sys

import bpy

source = Path(sys.argv[-2]).resolve()
destination = Path(sys.argv[-1]).resolve()
images = sorted(source.glob("frame_*.png"))
assert len(images) == 48
scene = bpy.context.scene
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
scene.render.resolution_percentage = 100
scene.render.fps = 24
scene.frame_start, scene.frame_end = 1, len(images)
strip = scene.sequence_editor_create().strips.new_image("Shot", str(images[0]), 1, 1)
for image in images[1:]:
    strip.elements.append(image.name)
strip.frame_final_duration = len(images)
scene.view_settings.view_transform = "Standard"
scene.render.image_settings.media_type = "VIDEO"
scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "HIGH"
scene.render.filepath = str(destination)
bpy.ops.render.render(animation=True)

