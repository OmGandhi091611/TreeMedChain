# Phase 6: Heuristic attention-shaped relevance ranking (non-learned).
# Ranks visible clinical entries by recency and severity.
from __future__ import annotations

from datetime import datetime
from typing import List, Tuple

from src.tree import MedicalNode

_SEVERITY_WEIGHT = {
    "high":   1.0,
    "medium": 0.6,
    "low":    0.3,
}

_RECENCY_DECAY = 0.1  # score decays per year of age


def _age_years(timestamp: str) -> float:
    try:
        dt = datetime.fromisoformat(timestamp[:10])
        return (datetime.now() - dt).days / 365.25
    except (ValueError, TypeError):
        return 5.0  # default if unparseable


def score(node: MedicalNode, now: datetime | None = None) -> float:
    severity = _SEVERITY_WEIGHT.get(node.sensitivity, 0.3)
    ts = node.timestamps[0] if node.timestamps else ""
    age = _age_years(ts)
    recency = max(0.0, 1.0 - _RECENCY_DECAY * age)
    return severity * recency


def rank_entries(entries: List[MedicalNode]) -> List[Tuple[float, MedicalNode]]:
    scored = [(score(e), e) for e in entries]
    return sorted(scored, key=lambda x: x[0], reverse=True)
