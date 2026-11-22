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


# ---------------------------------------------------------------------------------------------- T-215 (phase P2)
# Band-fit helpers for T-204 measures: z = gap / tolerance, so |z| <= 1 is inside the tolerance band.
UNSCORED_LOSS = 4.0  # a measure that was scored at the start and turns unscored costs as much as |z| = 3


def band_loss(z):
    """Zero pressure inside the band apart from a weak pull to its centre; quadratic outside it."""
    if z is None:
        return UNSCORED_LOSS
    a = abs(z)
    return max(0.0, a - 1.0) ** 2 + 0.02 * a * a


def view_cost(zs_by_view, keys_by_view):
    """Equal view weights (owner D2): mean band loss per view, then the mean over views. keys_by_view fixes the
    measure set (the start's scored rows), so a measure cannot leave the objective by turning unscored."""
    per = {}
    for view, keys in sorted(keys_by_view.items()):
        zs = zs_by_view.get(view, {})
        per[view] = sum(band_loss(zs.get(k)) for k in keys) / max(1, len(keys))
    return sum(per.values()) / max(1, len(per)), per


def edit_penalty(values, start, scales, weight):
    """Large edits cost: weight x sum of squared steps, each in units of its control's scale."""
    return weight * sum(((values[k] - start[k]) / scales[k]) ** 2 for k in start)


def fd_step(start, bounds, step):
    """Forward step inside the bounds; backward where the forward step would leave them."""
    lo, hi = bounds
    if start + step <= hi:
        return step
    if start - step >= lo:
        return -step
    raise ValueError(f"step {step} does not fit inside {bounds} from {start}")


def sensitivity(z0, trials, steps):
    """Finite-difference columns in z per control step: {control: {measure: dz}}. A measure unscored on either side
    is left out of that column."""
    cols = {}
    for name, z in trials.items():
        cols[name] = {k: (z[k] - z0[k]) * (1.0 if steps[name] > 0 else -1.0)
                      for k in z0 if z0.get(k) is not None and z.get(k) is not None}
    return cols


def _cos(a, b):
    keys = sorted(set(a) & set(b))
    na = math.sqrt(sum(a[k] ** 2 for k in keys))
    nb = math.sqrt(sum(b[k] ** 2 for k in keys))
    return 0.0 if not na or not nb else sum(a[k] * b[k] for k in keys) / (na * nb)


def select_controls(cols, measures, min_effect=0.25, max_cos=0.95, noisy=(), coupled=()):
    """Drop controls whose largest |dz| over the fitted measures stays under min_effect (no reach), then drop the
    weaker of every pair whose columns point the same way within max_cos (redundant). `noisy` measures (a ratio over a
    few pixels) still count in the objective but not here. `coupled` = [(measure subset, max_cos)]: the same pair test
    on one trace family, e.g. the front and profile cheek/jaw contours (T-212: coupled cheek and jaw knobs).
    Returns (kept, dropped) with a reason per dropped control."""
    measures = [k for k in measures if k not in set(noisy)]
    norm = {n: math.sqrt(sum(c.get(k, 0.0) ** 2 for k in measures)) for n, c in cols.items()}
    reach = {n: max([abs(c.get(k, 0.0)) for k in measures] or [0.0]) for n, c in cols.items()}
    dropped = {n: f"max |dz| {reach[n]:.3f} < {min_effect}" for n in cols if reach[n] < min_effect}
    live = sorted((n for n in cols if n not in dropped), key=lambda n: (-norm[n], n))
    kept = []
    for subset, limit, label in [(measures, max_cos, "redundant with")] + [(list(m), c, "coupled on " + ",".join(m)
                                                                             + " with") for m, c in coupled]:
        kept = []
        acts = {n for n in live if max(abs(cols[n].get(k, 0.0)) for k in subset) >= min_effect}
        for n in live:  # a control that barely moves this family is not tested on it
            sub = {k: cols[n].get(k, 0.0) for k in subset}
            twin = None if n not in acts else next(
                (m for m in kept if m in acts and abs(_cos(sub, {k: cols[m].get(k, 0.0) for k in subset})) > limit),
                None)
            if twin:
                c = _cos(sub, {k: cols[twin].get(k, 0.0) for k in subset})
                dropped[n] = f"{label} {twin} (cos {c:+.3f})"
            else:
                kept.append(n)
        live = kept
    return sorted(kept), dropped


def linear_z(z0, cols, start, steps, values):
    """First-order prediction of every z at values from the finite-difference columns of the controls in values."""
    z = dict(z0)
    for name in sorted(values):
        col = cols[name]
        t = (values[name] - start[name]) / abs(steps[name])
        for k, dz in col.items():
            if z.get(k) is not None:
                z[k] += dz * t
    return z


def cmaes(start, bounds, seed, budget, evaluate_many, sigma=0.2, popsize=6, mean=None):
    """Seeded separable CMA-ES (diagonal covariance) in bounds-normalised coordinates [0, 1] per control. Candidates
    are clipped to the bounds. evaluate_many(list of (index, values)) returns one cost per candidate (lower is
    better). The first generation evaluates the mean itself plus popsize - 1 samples. Ties keep the earlier trial.
    Returns (best index, best values, best cost)."""
    keys = sorted(bounds)
    n = len(keys)
    rng = random.Random(seed)
    span = {k: (bounds[k][1] - bounds[k][0]) or 1.0 for k in keys}

    def to_unit(v):
        return [(v[k] - bounds[k][0]) / span[k] for k in keys]

    def from_unit(u):
        return {k: min(bounds[k][1], max(bounds[k][0], bounds[k][0] + u[i] * span[k])) for i, k in enumerate(keys)}
    m = to_unit(mean or start)
    mu = max(1, popsize // 2)
    w = [math.log(mu + 0.5) - math.log(i + 1) for i in range(mu)]
    w = [x / sum(w) for x in w]
    mueff = 1.0 / sum(x * x for x in w)
    cs = (mueff + 2) / (n + mueff + 5)
    ds = 1 + 2 * max(0.0, math.sqrt((mueff - 1) / (n + 1)) - 1) + cs
    cc = (4 + mueff / n) / (n + 4 + 2 * mueff / n)
    c1 = 2 / ((n + 1.3) ** 2 + mueff) * (n + 2) / 3  # separable learning rate (Ros & Hansen 2008)
    cmu = min(1 - c1, 2 * (mueff - 2 + 1 / mueff) / ((n + 2) ** 2 + mueff) * (n + 2) / 3)
    chi = math.sqrt(n) * (1 - 1 / (4 * n) + 1 / (21 * n * n))
    diag = [1.0] * n
    ps, pc = [0.0] * n, [0.0] * n
    best = (math.inf, -1, None)
    done = 0
    gen = 0
    while done < budget:
        lam = min(popsize, budget - done)
        zs, us = [], []
        for j in range(lam):
            if gen == 0 and j == 0:
                z = [0.0] * n
            else:
                z = [rng.gauss(0, 1) for _ in range(n)]
            zs.append(z)
            us.append([m[i] + sigma * math.sqrt(diag[i]) * z[i] for i in range(n)])
        cands = [from_unit(u) for u in us]
        costs = list(evaluate_many([(done + j, c) for j, c in enumerate(cands)]))
        if len(costs) != lam or not all(math.isfinite(c) for c in costs):
            raise ValueError("non-finite candidate cost")
        for j, c in enumerate(costs):
            if c < best[0]:
                best = (c, done + j, cands[j])
        done += lam
        gen += 1
        if lam < 2:
            continue
        order = sorted(range(lam), key=lambda j: (costs[j], j))[:min(mu, lam)]
        ww = w[:len(order)]
        ww = [x / sum(ww) for x in ww]
        # selection on the clipped points: steps re-derived from the clipped unit coordinates
        y = [[(to_unit(cands[j])[i] - m[i]) / sigma for i in range(n)] for j in order]
        yw = [sum(ww[r] * y[r][i] for r in range(len(order))) for i in range(n)]
        m = [m[i] + sigma * yw[i] for i in range(n)]
        ps = [(1 - cs) * ps[i] + math.sqrt(cs * (2 - cs) * mueff) * yw[i] / math.sqrt(diag[i]) for i in range(n)]
        pc = [(1 - cc) * pc[i] + math.sqrt(cc * (2 - cc) * mueff) * yw[i] for i in range(n)]
        diag = [max(1e-6, (1 - c1 - cmu) * diag[i] + c1 * pc[i] ** 2 +
                    cmu * sum(ww[r] * y[r][i] ** 2 for r in range(len(order)))) for i in range(n)]
        sigma *= math.exp((cs / ds) * (math.sqrt(sum(x * x for x in ps)) / chi - 1))
        sigma = min(sigma, 0.5)
    return best[1], best[2], best[0]
