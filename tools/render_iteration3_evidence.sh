#!/usr/bin/env bash
# Renders the iteration-3 evidence set into renders/it3 (run from the repository root).
set -u
R=./build/apps/render-cli/plush-render
L=content/scenes/test_lineup.scene.json
E=content/scenes/test_expressions_girl_white_hair.scene.json
O=renders/it3
mkdir -p $O/expr
$R $E --frames 1-10 --outdir $O/expr --width 400 --height 400 --spp 48 --adaptive 0.1 --overwrite
$R $E --frame 2 --out $O/face_A_happy_1200x900.png --width 1200 --height 900 --spp 128 --adaptive 0.1
$R $L --frame 1 --out $O/face_B_900.png --width 900 --height 900 --spp 96 --adaptive 0.1 --camera 0.0,0.86,0.66 --target 0.0,0.8,0.1 --focal 60 --fstop 0
$R $L --frame 1 --out $O/face_C_900.png --width 900 --height 900 --spp 96 --adaptive 0.1 --camera 0.42,0.86,0.66 --target 0.42,0.8,0.1 --focal 60 --fstop 0
$R $L --frame 1 --out $O/hair_A_closeup_1000x800.png --width 1000 --height 800 --spp 96 --adaptive 0.1 --camera " -0.78,0.95,0.62" --target " -0.42,0.82,0.0" --focal 55 --fstop 0
$R $L --frame 1 --out $O/cloth_A_dress.png --width 800 --height 600 --spp 64 --adaptive 0.1 --camera " -0.42,0.52,0.5" --target " -0.42,0.46,0.0" --focal 50 --fstop 0
$R $L --frame 1 --out $O/cloth_B_vest_blouse.png --width 800 --height 600 --spp 64 --adaptive 0.1 --camera 0.0,0.58,0.48 --target 0.0,0.53,0.0 --focal 50 --fstop 0
$R $L --frame 1 --out $O/cloth_C_hoodie.png --width 800 --height 600 --spp 64 --adaptive 0.1 --camera 0.42,0.58,0.5 --target 0.42,0.53,0.0 --focal 50 --fstop 0
$R $L --frame 1 --out $O/lineup_front_1280x960.png --width 1280 --height 960 --spp 96 --adaptive 0.1
$R $L --frame 2 --out $O/lineup_threequarter_960x720.png --width 960 --height 720 --spp 64 --adaptive 0.1
$R $L --frame 3 --out $O/lineup_side_960x720.png --width 960 --height 720 --spp 64 --adaptive 0.1
$R content/scenes/milestone03_watertable.scene.json --frame 60 --out $O/group_watertable_1280x720.png --width 1280 --height 720 --spp 96 --adaptive 0.1
(cd $O/expr && ffmpeg -v error -y -i frame_0001.png -i frame_0002.png -i frame_0003.png -i frame_0004.png -i frame_0005.png \
  -i frame_0006.png -i frame_0007.png -i frame_0008.png -i frame_0009.png -i frame_0010.png \
  -filter_complex "[0][1][2][3][4]hstack=5[a];[5][6][7][8][9]hstack=5[b];[a][b]vstack" ../expression_sheet_A_10.png)
