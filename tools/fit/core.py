"""Bounded search and output isolation for reference fitting (plain Python)."""
import json
import math
import random
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def child(root, name):
    """Resolve links/junctions as well as '..' before allowing a file under root."""
    root = Path(root).resolve()
    p = (root / name).resolve()
    if p == root or not p.is_relative_to(root):
        raise ValueError(f"path escapes output directory: {name}")
    return p


def fresh_output(path):
    root = Path(path).resolve()
    if root.is_relative_to((ROOT / "assets").resolve()):
        raise ValueError("refusing output under assets/")
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise ValueError(f"output must be empty: {root}")
    return root


def component(node, token):
    if isinstance(node, list) and token.isascii() and token.isdigit() and int(token) < len(node):
        return int(token)
    if isinstance(node, dict) and token in node:
        return token
    raise ValueError(f"unknown parameter component: {token}")


def start_values(spec, bounds):
    if not isinstance(bounds, dict) or not bounds:
        raise ValueError("expected an object mapping parameter paths to [min, max]")
    values = {}
    for key, interval in sorted(bounds.items()):
        node = spec
        for part in key.split("."):
            node = node[component(node, part)]
        if not isinstance(interval, list) or len(interval) != 2:
            raise ValueError(f"{key}: expected [min, max]")
        lo, hi = interval
        if not all(type(x) in (float, int) and math.isfinite(x) for x in (lo, hi, node)):
            raise ValueError(f"{key}: bounds and starting value must be finite numbers")
        if not lo <= node <= hi:
            raise ValueError(f"{key}: starting value {node} outside {interval}")
        values[key] = node
    return values


def override(values, base=None):
    """The spec merger replaces arrays as units. Preserve their untuned entries."""
    result = {}
    for key, value in values.items():
        node = result
        source = base
        *parts, leaf = key.split(".")
        for part in parts:
            index = component(source, part) if source is not None else part
            source = source[index] if source is not None else None
            if isinstance(node, dict) and index not in node:
                node[index] = deepcopy(source) if isinstance(source, list) else {}
            node = node[index]
        index = component(source, leaf) if source is not None else leaf
        node[index] = value
    return result


def search(start, bounds, seed, budget, evaluate):
    """Count the unmodified start in the budget. Retain the earliest best on ties."""
    if budget < 1:
        raise ValueError("budget must include at least the start")
    rng = random.Random(seed)
    best = dict(start)
    best_score = -math.inf
    best_index = 0
    for i in range(budget):
        trial = dict(best)
        if i:
            for key in sorted(bounds):
                lo, hi = bounds[key]
                if i % 2 == 0:
                    radius = (hi - lo) / (2 + i // 2)
                    lo, hi = max(lo, best[key] - radius), min(hi, best[key] + radius)
                trial[key] = rng.uniform(lo, hi)
        score = evaluate(i, trial)
        if not math.isfinite(score):
            raise ValueError("non-finite candidate score")
        if score > best_score:
            best, best_index, best_score = trial, i, score
        if all(lo == hi for lo, hi in bounds.values()):
            break
    return best_index, best
