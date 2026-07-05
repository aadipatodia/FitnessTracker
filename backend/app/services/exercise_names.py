"""Normalize and fuzzy-match exercise names across workouts and cached summaries."""

from __future__ import annotations

import difflib
import re
from collections import Counter

FUZZY_MATCH_THRESHOLD = 0.88

_PUNCTUATION_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_exercise_key(name: str) -> str:
    """Canonical key: lowercase, no punctuation, collapsed whitespace."""
    if not name:
        return ""
    cleaned = name.strip().lower().replace("-", " ").replace("_", " ")
    cleaned = _PUNCTUATION_RE.sub("", cleaned)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned


def exercise_similarity(a: str, b: str) -> float:
    """Similarity score in [0, 1] on normalized exercise names."""
    na = normalize_exercise_key(a)
    nb = normalize_exercise_key(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return difflib.SequenceMatcher(None, na, nb).ratio()


def exercise_names_equivalent(
    a: str,
    b: str,
    threshold: float = FUZZY_MATCH_THRESHOLD,
) -> bool:
    return exercise_similarity(a, b) >= threshold


def find_best_exercise_match(
    name: str,
    candidates: list[str],
    *,
    threshold: float = FUZZY_MATCH_THRESHOLD,
    exclude: set[str] | None = None,
) -> str | None:
    """Return the best matching candidate name, or None."""
    exclude = exclude or set()
    best_name: str | None = None
    best_score = threshold
    for candidate in candidates:
        if candidate in exclude:
            continue
        score = exercise_similarity(name, candidate)
        if score >= best_score:
            best_score = score
            best_name = candidate
    return best_name


def cluster_exercise_names(
    names: list[str],
    threshold: float = FUZZY_MATCH_THRESHOLD,
) -> dict[str, str]:
    """Map each display name to a canonical display name within its fuzzy cluster."""
    unique = list(dict.fromkeys(n.strip() for n in names if n and n.strip()))
    if not unique:
        return {}

    parent = {name: name for name in unique}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(a: str, b: str) -> None:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    for i, left in enumerate(unique):
        for right in unique[i + 1 :]:
            if exercise_names_equivalent(left, right, threshold):
                union(left, right)

    name_counts = Counter(names)
    clusters: dict[str, list[str]] = {}
    for name in unique:
        clusters.setdefault(find(name), []).append(name)

    mapping: dict[str, str] = {}
    for members in clusters.values():
        canonical = max(members, key=lambda n: (name_counts.get(n, 0), len(n)))
        for member in members:
            mapping[member] = canonical
    return mapping
