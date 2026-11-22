#!/bin/bash
# Renders the 9 head close-ups (3 characters x front / 3/4 / side). Run from the repository root.
O=docs/evaluation/characters/T-202/renders
R="python3 tools/bpy_blender.py -b --factory-startup -P docs/evaluation/characters/T-202/face_views.py --"
A=assets/characters
$R $O $A/boy_yellow_hoodie/versions/2.3.0/boy_yellow_hoodie_master.blend boy_2.3.0 0,0,0.83 0.48 0:6,-35:6,-90:6 --samples 16 --px 1024
$R $O $A/girl_auburn_bun_glasses/versions/0.14.0/girl_auburn_bun_glasses_master.blend girl_0.14.0 0,0,0.83 0.54 0:5,-45:5,90:5 --samples 16 --px 1024
$R $O $A/girl_white_hair_blue_dress/versions/0.1.0/girl_white_hair_blue_dress_master.blend third_0.1.0 0,0,0.80 0.54 0:5,-30:5,-90:5 --samples 16 --px 1024
