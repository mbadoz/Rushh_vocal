from collections import defaultdict
import math


# Counts are normalized before costing. Cached input is a subset of input_tokens.
def cost(usage, prices, fx):
    lines = []
    missing = []
    total = 0
    estimated = False
    for component, counts in usage.items():
        price = prices.get(component, {})
        rates = price.get("rates", {})
        if price.get("status") == "estimate":
            estimated = True
        for unit, quantity in counts.items():
            if unit == "input_tokens":
                quantity = max(
                    0,
                    quantity
                    - counts.get("cached_tokens", 0)
                    - counts.get("cache_creation_tokens", 0),
                )
            if quantity <= 0:
                continue
            rate = rates.get(unit)
            if rate is None:
                missing.append(f"{component}/{unit}")
                continue
            amount = quantity * rate * (fx if price.get("currency") == "USD" else 1)
            lines.append(
                dict(
                    component=component,
                    unit=unit,
                    quantity=quantity,
                    rate=rate,
                    eur=amount,
                )
            )
            total += amount
    return dict(
        eur=total,
        complete=not missing,
        estimated=estimated,
        missing=missing,
        lines=lines,
    )


def percentile(values, p):
    if not values:
        return None
    a = sorted(values)
    index = (len(a) - 1) * p
    lo = math.floor(index)
    hi = math.ceil(index)
    return a[lo] + (a[hi] - a[lo]) * (index - lo)


def compare(runs):
    groups = defaultdict(list)
    for r in runs:
        if r["status"] == "completed":
            groups[r["composition_version"]].append(r)
    result = []
    for version, rows in groups.items():
        duration = sum(r.get("duration", 0) for r in rows)
        latency = [
            t["latency_ms"]
            for r in rows
            for t in r.get("turns", [])
            if t.get("latency_ms") is not None
        ]
        notes = [r["rating"] for r in rows if r.get("rating") is not None]
        result.append(
            dict(
                id=version,
                name=rows[0]["config"]["name"],
                count=len(rows),
                eur_per_min=sum(r["cost"]["eur"] for r in rows) / duration * 60
                if duration
                else None,
                complete=all(r["cost"]["complete"] for r in rows),
                median_ms=percentile(latency, 0.5),
                p95_ms=percentile(latency, 0.95),
                rating=sum(notes) / len(notes) if notes else None,
                run_ids=[r["id"] for r in rows],
            )
        )
    return result
