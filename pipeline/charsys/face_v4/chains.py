"""In-between chain completion (face_generic/4, T-216; T-213 finding "chain gap", option b).

The engine expands an in-between chain by morph NAME for every mesh (engine/model/character.cpp expandInbetweens,
mirrored in face_parity.expand_inbetweens): below the last stop the base block gets weight 0 and only the "<X>@NN"
blocks carry the motion. A mesh that has the base key <X> but none of its stop keys therefore stays at rest in the
engine until the last stop, while Blender drives it linearly. complete() gives such a mesh linear stop keys
(<X>@NN = Basis + NN/100 x (<X> - Basis), same relative key and vertex group as <X>), so with the hat drivers of
face_generic.add_inbetween_drivers both Blender and the engine move it by w x the base delta at every weight.
Meshes with at least one stop key of the chain are left as they are (their chain is already consistent).

Pure bpy, character-independent: chains are found by key names only."""

STOP_SEP = "@"


def chain_stops(names_per_object):
    """{base: sorted stop percentages} over all meshes; names_per_object: iterable of key-name collections."""
    stops = {}
    for names in names_per_object:
        for n in names:
            if STOP_SEP not in n:
                continue
            base, pct = n.rsplit(STOP_SEP, 1)
            if pct.isdigit() and 0 < int(pct) < 100:
                stops.setdefault(base, set()).add(int(pct))
    return {b: sorted(p) for b, p in stops.items()}


def gaps(names_by_object, stops):
    """[(object name, base)] for objects that carry a chained base key and none of its stop keys."""
    out = []
    for ob, names in sorted(names_by_object.items()):
        for base, pcts in sorted(stops.items()):
            if base in names and not any(f"{base}{STOP_SEP}{p:02d}" in names for p in pcts):
                out.append((ob, base))
    return out


def complete(objs):
    """Adds the linear stop keys (module docstring). Returns {base: [object names]} of the completed meshes."""
    import numpy as np
    keyed, seen = {}, set()
    for o in sorted((o for o in objs if o.type == "MESH" and o.data.shape_keys), key=lambda o: o.name):
        if o.data.shape_keys.name in seen:  # meshes that share one mesh / Key datablock are completed once
            continue
        seen.add(o.data.shape_keys.name)
        keyed[o.name] = o
    names = {n: {k.name for k in o.data.shape_keys.key_blocks} for n, o in keyed.items()}
    stops = chain_stops(names.values())
    done = {}
    for obname, base in gaps(names, stops):
        ob = keyed[obname]
        kb = ob.data.shape_keys.key_blocks
        src = kb[base]
        ref = src.relative_key
        n = len(ob.data.vertices)
        a = np.empty(3 * n)
        b = np.empty(3 * n)
        ref.data.foreach_get("co", a)
        src.data.foreach_get("co", b)
        for p in stops[base]:
            k = ob.shape_key_add(name=f"{base}{STOP_SEP}{p:02d}", from_mix=False)
            k.relative_key = ref
            k.vertex_group = src.vertex_group
            k.slider_min, k.slider_max = src.slider_min, src.slider_max
            k.data.foreach_set("co", a + (p / 100.0) * (b - a))
            k.value = 0.0
        done.setdefault(base, []).append(obname)
    return {b: sorted(v) for b, v in sorted(done.items())}
