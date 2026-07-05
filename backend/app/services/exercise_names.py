"""Normalize and fuzzy-match exercise names across workouts and cached summaries."""

from __future__ import annotations

import difflib
import re
from collections import Counter

FUZZY_MATCH_THRESHOLD = 0.88
MIN_PREFIX_MATCH_LEN = 4

_PUNCTUATION_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")
_PAREN_RE = re.compile(r"\([^)]*\)")
_BRACKET_RE = re.compile(r"\[[^\]]*\]")


def extract_exercise_base_name(name: str) -> str:
    """Drop inline notes like 'Leg press (machine weight extra)'."""
    if not name:
        return ""
    cleaned = name.strip()
    cleaned = _PAREN_RE.sub("", cleaned)
    cleaned = _BRACKET_RE.sub("", cleaned)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip(" -–—,")
    return cleaned


def normalize_exercise_key(name: str) -> str:
    """Canonical key: lowercase, no punctuation, collapsed whitespace."""
    if not name:
        return ""
    cleaned = extract_exercise_base_name(name)
    cleaned = cleaned.lower().replace("-", " ").replace("_", " ")
    cleaned = _PUNCTUATION_RE.sub("", cleaned)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned


def _fuzzy_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _prefix_equivalent(shorter: str, longer: str) -> bool:
    if len(shorter) < MIN_PREFIX_MATCH_LEN:
        return False
    if not longer.startswith(shorter):
        return False
    if len(longer) == len(shorter):
        return True
    return longer[len(shorter)] == " "


def exercise_similarity(a: str, b: str) -> float:
    """Similarity score in [0, 1] on normalized exercise names."""
    na = normalize_exercise_key(a)
    nb = normalize_exercise_key(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0

    shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
    if _prefix_equivalent(shorter, longer):
        return 1.0

    return _fuzzy_ratio(na, nb)


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


def _canonical_for_cluster_members(
    members: list[str],
    name_counts: Counter,
) -> str:
    return min(
        members,
        key=lambda n: (
            -name_counts.get(n, 0),
            "(" in n or "[" in n,
            len(normalize_exercise_key(n)),
            len(n),
        ),
    )


def cluster_exercise_names(
    names: list[str],
    threshold: float = FUZZY_MATCH_THRESHOLD,
    semantic_mapping: dict[str, str] | None = None,
) -> dict[str, str]:
    """Map each display name to a canonical display name within its cluster."""
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

    semantic_canonicals: dict[str, str] = {}
    if semantic_mapping:
        semantic_groups: dict[str, list[str]] = {}
        for name in unique:
            canonical = semantic_mapping.get(name)
            if not canonical:
                continue
            semantic_groups.setdefault(canonical, []).append(name)
        for group in semantic_groups.values():
            if len(group) < 2:
                continue
            anchor = group[0]
            preferred = semantic_mapping.get(anchor, anchor)
            for member in group:
                semantic_canonicals[member] = preferred
            for other in group[1:]:
                union(anchor, other)

    name_counts = Counter(names)
    clusters: dict[str, list[str]] = {}
    for name in unique:
        clusters.setdefault(find(name), []).append(name)

    mapping: dict[str, str] = {}
    for members in clusters.values():
        semantic_member = next(
            (semantic_canonicals[member] for member in members if member in semantic_canonicals),
            None,
        )
        canonical = semantic_member or _canonical_for_cluster_members(members, name_counts)
        for member in members:
            mapping[member] = canonical
    return mapping


def merge_strength_progression_points(
    points: list[dict[str, str | float]],
    all_exercise_names: list[str] | None = None,
    semantic_mapping: dict[str, str] | None = None,
) -> list[dict[str, str | float]]:
    """
    Merge chart points that share a fuzzy exercise cluster.

    Same exercise logged as "Bench Press" and "Bench press" becomes one series
    with the heaviest weight kept for each session date.
    """
    if not points:
        return []

    names = [str(p["exercise"]) for p in points if p.get("exercise")]
    if all_exercise_names:
        names = list(dict.fromkeys(names + [n for n in all_exercise_names if n]))
    clusters = cluster_exercise_names(names, semantic_mapping=semantic_mapping)

    merged: dict[tuple[str, str], float] = {}
    for point in points:
        exercise = str(point["exercise"])
        canonical = clusters.get(exercise, exercise)
        key = (str(point["date"]), canonical)
        weight = float(point.get("max_weight") or 0)
        merged[key] = max(merged.get(key, 0.0), weight)

    return [
        {"date": session_date, "exercise": exercise, "max_weight": weight}
        for (session_date, exercise), weight in sorted(merged.items())
    ]
