# Verbatim-move check (T-085): every line removed from tests/test_engine.cpp appears, block by block and in order,
# in tests/test_render.cpp; nothing was added to test_engine.cpp. Blank separator lines at the end of a removed
# block are ignored. Then classify the ANSI `git diff --color-moved=plain` output (git default colours:
# moved-old = bold magenta 1;35, moved-new = bold cyan 1;36).
import re, subprocess, sys
A, B, ansi_path = sys.argv[1:4]
diff = subprocess.run(["git", "diff", "-U0", A, B, "--", "tests/test_engine.cpp"], capture_output=True, text=True).stdout
blocks, cur, added = [], [], 0
for l in diff.splitlines():
    if l.startswith("@@"):
        if cur: blocks.append(cur); cur = []
    elif l.startswith("-") and not l.startswith("---"): cur.append(l[1:])
    elif l.startswith("+") and not l.startswith("+++"): added += 1
if cur: blocks.append(cur)
removed = sum(len(b) for b in blocks)
print(f"tests/test_engine.cpp ({A}..{B}): {removed} lines removed in {len(blocks)} blocks, {added} lines added")
new = subprocess.run(["git", "show", f"{B}:tests/test_render.cpp"], capture_output=True, text=True).stdout.splitlines()
moved = []
for b in blocks:
    while b and not b[-1].strip(): b = b[:-1]
    moved.append(b)
flat = [l for b in moved for l in b + [""]][:-1]
header = new[:len(new) - len(flat)]
print(f"tests/test_render.cpp: {len(new)} lines = {len(header)} new header lines + {len(flat)} moved lines")
for i, b in enumerate(moved, 1):
    print(f"  block {i}: {len(b)} lines starting {b[0]!r}")
print(f"moved part of test_render.cpp identical to the removed blocks (joined by one blank line): {new[len(header):] == flat}")
print("new header lines (the only lines not moved):")
for h in header: print("  | " + h)
strip = lambda s: re.sub(r"\x1b\[[0-9;]*m", "", s)
counts = {"moved-old": 0, "moved-new": 0, "plain-removed": 0, "plain-added": 0}
for l in open(ansi_path, encoding="utf-8").read().splitlines():
    t = strip(l)
    if t.startswith(("---", "+++")): continue
    if t.startswith("-"): counts["moved-old" if "\x1b[1;35m" in l else "plain-removed"] += 1
    elif t.startswith("+"): counts["moved-new" if "\x1b[1;36m" in l else "plain-added"] += 1
print("git diff --color-moved=plain line classes:", counts)
