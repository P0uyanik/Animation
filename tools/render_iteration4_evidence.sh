#!/usr/bin/env bash
# Renders the iteration-4 evidence set into renders/it4 (run from the repository root).
# Same cameras as iteration 3 where a comparison is wanted. Resumable: an output newer than every
# character file is kept and skipped.
set -u
R=./build/apps/render-cli/plush-render
L=content/scenes/test_lineup.scene.json
O=renders/it4
mkdir -p $O
fresh() { [ -f "$1" ] && [ -z "$(find content/characters -name '*.character.json' -newer "$1" | head -1)" ]; }
still() { local out=$1; shift; if fresh "$out"; then echo "[info] keep $out"; else $R "$@" --out "$out"; fi; }
# Full-body turnaround (all three side by side, same framing as iteration 3) + back view.
still $O/lineup_front_1280x960.png $L --frame 1 --width 1280 --height 960 --spp 96 --adaptive 0.1
still $O/lineup_threequarter_960x720.png $L --frame 2 --width 960 --height 720 --spp 64 --adaptive 0.1
still $O/lineup_side_960x720.png $L --frame 3 --width 960 --height 720 --spp 64 --adaptive 0.1
still $O/lineup_back_960x720.png $L --frame 4 --width 960 --height 720 --spp 64 --adaptive 0.1
# Face close-ups (front) and three-quarter hair close-ups, per character.
for c in "A -0.42" "B 0.0" "C 0.42"; do
  set -- $c; n=$1; x=$2
  still $O/face_${n}_900.png $L --frame 1 --width 900 --height 900 --spp 96 --adaptive 0.1 --camera " $x,0.84,0.62" --target " $x,0.8,0.1" --focal 55 --fstop 0
  still $O/hair_${n}_threequarter_900x700.png $L --frame 1 --width 900 --height 700 --spp 80 --adaptive 0.1 --camera " $(python3 -c "print($x-0.42)"),0.98,0.62" --target " $x,0.86,0.0" --focal 50 --fstop 0
  still $O/hair_${n}_back_900x700.png $L --frame 4 --width 900 --height 700 --spp 80 --adaptive 0.1 --camera " $x,0.95,0.75" --target " $x,0.8,0.0" --focal 45 --fstop 0
done
# Clothing close-ups (iteration-3 cameras).
still $O/cloth_A_dress.png $L --frame 1 --width 800 --height 600 --spp 64 --adaptive 0.1 --camera " -0.42,0.52,0.62" --target " -0.42,0.44,0.0" --focal 45 --fstop 0
still $O/cloth_B_vest_blouse.png $L --frame 1 --width 800 --height 600 --spp 64 --adaptive 0.1 --camera 0.0,0.58,0.48 --target 0.0,0.53,0.0 --focal 50 --fstop 0
still $O/cloth_C_hoodie.png $L --frame 1 --width 800 --height 600 --spp 64 --adaptive 0.1 --camera 0.42,0.56,0.55 --target 0.42,0.5,0.0 --focal 45 --fstop 0
# Expression sheets (10 expressions each).
for a in girl_white_hair girl_brown_glasses boy_dark_hair; do
  mkdir -p $O/expr_$a
  $R content/scenes/test_expressions_$a.scene.json --frames 1-10 --outdir $O/expr_$a --width 360 --height 360 --spp 48 --adaptive 0.1
  (cd $O/expr_$a && ffmpeg -v error -y -i frame_0001.png -i frame_0002.png -i frame_0003.png -i frame_0004.png -i frame_0005.png \
    -i frame_0006.png -i frame_0007.png -i frame_0008.png -i frame_0009.png -i frame_0010.png \
    -filter_complex "[0][1][2][3][4]hstack=5[a];[5][6][7][8][9]hstack=5[b];[a][b]vstack" ../expression_sheet_$a.png)
done
echo "[info] evidence done"
