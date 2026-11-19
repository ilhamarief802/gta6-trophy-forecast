"""Forecaster for trophy earn rates (make.fun entry).

Reads every *.in case in $MAKEFUN_INPUT_DIR and, for each one, writes
$MAKEFUN_OUTPUT_DIR/<id>.out holding five quantiles per trophy at the case's
target, in percent:

    {"trophies":[{"id":n,"q":[q05,q25,q50,q75,q95]}, ...]}

The model is measured against the two rows the RULES publish for a trophy at
1.10%:

    practice  90 min:  0.8974  1.012  1.1  1.1955  1.3477
    final   6510 min:  0.1931  0.5403 1.1  2.2264  6.0088

Both keep the median exactly at the last printed rate and differ only in the
spread. The reads are usually identical because the source page refreshes on
its own clock, so the newest printed rate is carried forward in logit space and
widened symmetrically by

    sigma(horizon_minutes) = 0.125 * sqrt(horizon / 90)

with z = (-1.6449, -0.6745, 0, 0.6745, 1.6449). That reproduces the house's own
row inside 2% at both horizons. It is honest about what a stale page supports:
no drift is invented from reads that never changed.

Standard library only, no network.
"""

import json
import math
import os
import sys

# z-scores for the 5/25/50/75/95 quantiles of a standard normal.
NZ = (-1.6448536269514722, -0.6744897501960817, 0.0,
      0.6744897501960817, 1.6448536269514722)

# logit-space sigma after 90 minutes; see the docstring for the calibration.
SIGMA_90 = 0.125

# rates below this are treated as saturated at 100% (printed as 100).
SATURATED = 99.995

# never printed anywhere: the page clamps at 0.01, and one player appearing
# would lift it, so keep it low with a narrow spread.
UNSEEN = (0.01, 0.01, 0.01, 0.02, 0.05)


def clamp_rate(x):
    """Clamp a percentage into the printable [0.01, 99.99] band."""
    return min(99.99, max(0.01, x))


def logit(p):
    p = clamp_rate(p) / 100.0
    return math.log(p / (1.0 - p))


def unlogit(z):
    p = 1.0 / (1.0 + math.exp(-z))
    return min(99.99, max(0.01, p * 100.0))


def newest_rate(history, i):
    """The newest rate the page printed for trophy index i, or None."""
    for read in reversed(history):
        rates = read.get("rates") or []
        if i < len(rates) and rates[i] is not None:
            return float(rates[i])
    return None


def sigma_for(horizon_minutes):
    horizon = float(horizon_minutes or 0.0)
    return SIGMA_90 * math.sqrt(max(horizon, 1.0) / 90.0)


def forecast(case):
    history = case.get("history") or []
    sigma = sigma_for(case.get("horizon_minutes"))
    rows = []
    for i, trophy in enumerate(case.get("trophies") or []):
        rate = newest_rate(history, i)
        if rate is None:
            q = list(UNSEEN)
        elif rate >= SATURATED:
            # a finished trophy cannot rise above 100 and the page keeps the
            # 100% row at 100 across a refresh, so hold it there.
            q = [99.9, 99.95, 99.99, 99.99, 99.99]
        else:
            centre = logit(rate)
            q = [unlogit(centre + sigma * nz) for nz in NZ]
        # quantiles must be non-decreasing and lie inside [0, 100].
        for k, value in enumerate(q):
            q[k] = min(100.0, max(0.0, value))
            if k and q[k] < q[k - 1]:
                q[k] = q[k - 1]
        trophy_id = trophy.get("id")
        if trophy_id is None:
            trophy_id = i + 1
        rows.append({"id": trophy_id, "q": q})
    return {"trophies": rows}


def main():
    src = os.environ.get("MAKEFUN_INPUT_DIR") or "/input"
    dst = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(dst, exist_ok=True)

    names = sorted(n for n in os.listdir(src) if n.endswith(".in"))
    if not names:
        sys.exit("no .in cases in " + src)

    for name in names:
        with open(os.path.join(src, name), encoding="utf-8") as handle:
            case = json.load(handle)
        payload = json.dumps(forecast(case), separators=(",", ":"))
        if len(payload) > 65536:
            sys.exit("refusing output over 65536 bytes: " + name)
        out_path = os.path.join(dst, name[:-3] + ".out")
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(payload)

    print("wrote %d case(s) to %s" % (len(names), dst), file=sys.stderr)


if __name__ == "__main__":
    main()
