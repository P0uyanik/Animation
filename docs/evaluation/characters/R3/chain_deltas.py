"""R3 step 4: one line per stacked change, from the chain builds' strict mesh hashes (chain_build.sh).

Each step is compared with the step before it (which objects' geometry changed, vertex-count deltas), and the final
R3 build with the base. A layer that changes no object, or an object changed by a layer that a later layer resets to
its earlier hash, is flagged. Usage: python3 docs/evaluation/characters/R3/chain_deltas.py <work dir> [<published hash dir>]
Writes docs/evaluation/characters/R3/chain_deltas.json and prints the lines."""
import json, sys
from pathlib import Path

W = Path(sys.argv[1])
PUB = Path(sys.argv[2]) if len(sys.argv) > 2 else None
out, lines = {}, []
for cdir in sorted(p for p in W.iterdir() if p.is_dir()):
    steps = sorted(p for p in cdir.iterdir() if (p / "hash.json").exists() and not p.name.startswith("repeat_"))
    H = [(s.name, json.loads((s / "hash.json").read_text())) for s in steps]
    rows = []
    if PUB and (PUB / f"{cdir.name}.json").exists():
        pub = json.loads((PUB / f"{cdir.name}.json").read_text())
        same = pub == H[0][1]
        lines.append(f"{cdir.name}: base build vs published master: {'identical' if same else 'DIFFERS'}")
        rows.append({"step": "base_vs_published", "identical": same})
    for (pa, a), (pb, b) in zip(H, H[1:]):
        ch = sorted(k for k in set(a) | set(b) if a.get(k, {}).get("sha256") != b.get(k, {}).get("sha256"))
        dv = {k: b.get(k, {}).get("vertices", 0) - a.get(k, {}).get("vertices", 0) for k in ch}
        reverted = [k for k in ch if any(h.get(k, {}).get("sha256") == b.get(k, {}).get("sha256")
                                         for _, h in H[:H.index((pa, a))])]
        rows.append({"step": pb, "changed": ch, "vertex_delta": dv, "reverted_to_earlier": reverted})
        desc = ", ".join(f"{k} ({dv[k]:+d} v)" if dv[k] else k for k in ch) or "NO CHANGE"
        lines.append(f"{cdir.name} {pb}: {len(ch)} objects changed: {desc}" + (f"  REVERTED {reverted}" if reverted else ""))
    a, b = H[0][1], H[-1][1]
    fin = sorted(k for k in set(a) | set(b) if a.get(k, {}).get("sha256") != b.get(k, {}).get("sha256"))
    # every object a layer changed must still differ from base in the final build (no later layer undid it)
    lost = sorted({k for r in rows if "changed" in r for k in r["changed"]} - set(fin))
    lines.append(f"{cdir.name} final vs base: {len(fin)} objects differ; changes lost by later layers: {lost or 'none'}")
    rep = {}
    for name, ref in (("base", steps[0]), ("R3_final", steps[-1])):
        r = cdir / f"repeat_{name}" / "hash.json"
        if r.exists():
            x, y = json.loads((ref / "hash.json").read_text()), json.loads(r.read_text())
            var = sorted(k for k in set(x) | set(y) if x.get(k) != y.get(k))
            rep[name] = var
            lines.append(f"{cdir.name} repeat {name}: {'identical (all objects)' if not var else f'{len(var)} objects vary: {var}'}")
    out[cdir.name] = {"steps": rows, "final_vs_base": fin, "lost": lost, "repeat_varying": rep}
Path("docs/evaluation/characters/R3/chain_deltas.json").write_text(json.dumps(out, indent=1) + "\n")
print("\n".join(lines))
