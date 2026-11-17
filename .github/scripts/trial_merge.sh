#!/usr/bin/env bash
# Trial-merge <target> into the checked-out commit without committing (T-041). On a conflict, write a FAIL
# "Merge status" report into <report-dir>/check_all.json so the verdict job shows it. Sets clean=true|false.
set -uo pipefail
target="${1:-}"
out="${2:-build/check-all/trial}"
mkdir -p "$out"
if [ -z "$target" ]; then
  echo "clean=true" >> "$GITHUB_OUTPUT"
  echo "no merge target"
  exit 0
fi
if git -c user.name=ci -c user.email=ci@invalid merge --no-commit --no-ff "$target"; then
  echo "clean=true" >> "$GITHUB_OUTPUT"
  exit 0
fi
files=$(git diff --name-only --diff-filter=U | paste -sd, -)
status="CONFLICT with $target in ${files:-(files unavailable)}"
python3 - "$out/check_all.json" "$status" <<'PY'
import json, sys
path, status = sys.argv[1], sys.argv[2]
json.dump({"schema": "plush.quality-gate/1", "verdict": "FAIL", "platform": "merge",
           "checks": [{"name": "Merge status", "ok": False, "detail": status}],
           "summary": [f"FAIL Merge status: {status}"]}, open(path, "w"), indent=2)
PY
echo "clean=false" >> "$GITHUB_OUTPUT"
echo "$status"
