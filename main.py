"""Forecaster for gta6-trophy-rarity-forecast-01.

Derived from the two example rows the RULES publish — both for a trophy at 1.10%:

    practice  90 min:  0.8974  1.012  1.1  1.1955  1.3477
    final   6510 min:  0.1931  0.5403 1.1  2.2264  6.0088

Both keep the median exactly at the last rate and differ only in spread. In logit
space with logit(1.1%) = -4.50, the 5% quantile moves from -4.70 to -6.25, i.e.
1.75 logit for 6510 min; and 6510/90 = 72.3, sqrt = 8.50. So

    sigma(h) = 0.125 * sqrt(h / 90)

reproduces the house's own row at both horizons (checked by calibrate.py, which
asserts both to 2%). That is the whole model: carry the last rate forward in
logit space and widen symmetrically. It is honest about what a stale page
supports — no drift is invented from reads that never changed.
"""

import json
import math
import os
import sys

NZ = (-1.6448536269514722, -0.6744897501960817, 0.0,
      0.6744897501960817, 1.6448536269514722)
SIGMA_90 = 0.125


def clamp_rate(x):
    return min(99.99, max(0.01, x))


def logit(p):
    p = clamp_rate(p) / 100.0
    return math.log(p / (1.0 - p))


def unlogit(z):
    p = 1.0 / (1.0 + math.exp(-z))
    return min(99.99, max(0.01, p * 100.0))


def last_rate(history, i):
    """The newest rate the page printed for trophy i, or None if never printed."""
    for read in reversed(history):
        rates = read.get("rates") or []
        if i < len(rates) and rates[i] is not None:
            return float(rates[i])
    return None


def forecast(case):
    history = case.get("history") or []
    horizon = float(case.get("horizon_minutes") or 0.0)
    sigma = SIGMA_90 * math.sqrt(max(horizon, 1.0) / 90.0)
    rows = []
    for i, trophy in enumerate(case.get("trophies") or []):
        rate = last_rate(history, i)
        if rate is None:
            # never printed: a trophy nobody tracked has earned. The page clamps
            # at 0.01, and one player appearing would lift it; keep it low.
            q = [0.01, 0.01, 0.01, 0.02, 0.05]
        else:
            centre = logit(rate)
            q = [unlogit(centre + sigma * nz) for nz in NZ]
            # a saturated trophy cannot rise above 100, and the house keeps the
            # 100% one at 100 across a refresh, so hold it.
            if rate >= 99.995:
                q = [99.9, 99.95, 99.99, 99.99, 99.99]
        for k in range(1, 5):
            if q[k] < q[k - 1]:
                q[k] = q[k - 1]
        rows.append({"id": trophy.get("id"), "q": q})
    return {"trophies": rows}


def main():
    src = os.environ.get("MAKEFUN_INPUT_DIR") or "/input"
    dst = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(dst, exist_ok=True)
    names = sorted(f for f in os.listdir(src) if f.endswith(".in"))
    if not names:
        sys.exit("no case files in " + src)
    for name in names:
        with open(os.path.join(src, name), encoding="utf-8") as handle:
            case = json.load(handle)
        out = forecast(case)
        path = os.path.join(dst, name[:-3] + ".out")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(out, handle, separators=(",", ":"))
        if os.path.getsize(path) > 65536:
            sys.exit("output too large: " + path)
    print("wrote %d case(s)" % len(names), file=sys.stderr)


if __name__ == "__main__":
    main()
