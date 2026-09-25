from decimal import Decimal
from statistics import median


def value_indicator(value: Decimal | None, peers: list[Decimal]) -> dict:
    base = {
        "name": "Contract value relative to peers",
        "algorithm_version": "mad-1.0.0",
        "formula": "value > median + 3 × 1.4826 × MAD",
        "threshold": "3",
        "sample_size": len(peers),
        "minimum_sample": 10,
        "value": str(value) if value is not None else None,
        "comparison_group": "Same CPV division, procedure, currency and conclusion year; target excluded",
        "limitations": "Descriptive comparison within the indexed sample. Not evidence of misconduct.",
    }
    if value is None or len(peers) < 10:
        return {
            **base,
            "status": "insufficient_data",
            "explanation": "At least 10 other comparable contracts and a known value are required.",
        }
    center = median(peers)
    mad = median([abs(p - center) for p in peers])
    if mad == 0:
        return {
            **base,
            "status": "zero_dispersion",
            "median": str(center),
            "mad": "0",
            "explanation": "MAD is zero; no outlier decision is made.",
        }
    threshold = center + Decimal(3) * Decimal("1.4826") * mad
    return {
        **base,
        "status": "above_threshold" if value > threshold else "within_threshold",
        "median": str(center),
        "mad": str(mad),
        "threshold_value": str(threshold),
        "explanation": "Comparison uses the disclosed robust median/MAD rule.",
    }
