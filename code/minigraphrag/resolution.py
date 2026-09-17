"""Entity resolution: deciding that "Okafor", "Mira Okafor" and "Dr. Mira Okafor" are one node.

Extraction works chunk by chunk, so the same real-world thing appears under
many surface forms. If we don't merge them, the graph fragments: Okafor's
facts end up on three disconnected nodes and multi-hop questions fail.

We use a cascade of cheap, explainable rules, from safest to riskiest:
1. normalisation (case, titles like "Dr.", punctuation, possessives)
2. token containment ("OKAFOR" ⊂ "MIRA OKAFOR") with the same type
3. acronyms ("TWI" -> TideWater Institute)
4. fuzzy string similarity (typos) via difflib, or rapidfuzz if installed
5. optional embedding similarity of name + description
A short name is only merged if it matches exactly *one* longer candidate;
ambiguous aliases stay separate (a wrong merge is worse than a missed one).
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher

import numpy as np

from .extraction import Entity

_TITLES = {"DR", "MR", "MRS", "MS", "PROF", "THE"}


def normalize_name(name: str) -> str:
    """Uppercase, drop titles/punctuation/possessives, collapse whitespace."""
    name = re.sub(r"['’]S\b", "", name.upper())
    tokens = re.findall(r"[A-Z0-9]+", name)
    while tokens and tokens[0] in _TITLES:
        tokens = tokens[1:]
    return " ".join(tokens)


def _similarity(a: str, b: str) -> float:
    try:
        from rapidfuzz import fuzz  # optional, faster

        return fuzz.ratio(a, b) / 100
    except ImportError:
        return SequenceMatcher(None, a, b).ratio()


def _is_acronym(short: str, long: str) -> bool:
    """True if `short` is spelled by letters of `long` in order, covering every word's initial.

    "TWI" matches "TIDEWATER INSTITUTE": T(ide)W(ater) I(nstitute).
    """
    if " " in short or len(short) < 2 or len(short) > 6 or " " not in long:
        return False
    words = long.split()
    pos, letters = 0, "".join(words)
    initials = {sum(len(w) for w in words[:i]) for i in range(len(words))}
    matched = []
    for ch in short:
        idx = letters.find(ch, pos)
        if idx == -1:
            return False
        matched.append(idx)
        pos = idx + 1
    return initials <= set(matched) and matched[0] == 0


def resolve_entities(
    entities: list[Entity],
    alias_threshold: float = 0.9,
    embedder=None,
    embedding_threshold: float = 0.95,
) -> dict[str, str]:
    """Return {raw entity name: canonical name} for every name in `entities`."""
    # Group raw names by normalised form; remember the most common type per group.
    groups: dict[str, set[str]] = defaultdict(set)
    types: dict[str, Counter] = defaultdict(Counter)
    descriptions: dict[str, str] = {}
    for e in entities:
        key = normalize_name(e.name) or e.name
        groups[key].add(e.name)
        types[key][e.type] += 1
        descriptions.setdefault(key, e.description)

    def gtype(key: str) -> str:
        return types[key].most_common(1)[0][0] if types[key] else ""

    def compatible(a: str, b: str) -> bool:
        ta, tb = gtype(a), gtype(b)
        return ta == tb or not ta or not tb

    # Longer names first: they become canonical, shorter names try to attach to them.
    keys = sorted(groups, key=lambda k: (-len(k.split()), -len(k), k))
    parent: dict[str, str] = {}
    canon: list[str] = []
    vectors = None
    if embedder is not None:
        vectors = dict(zip(keys, embedder.embed([f"{k}: {descriptions[k]}" for k in keys])))

    for key in keys:
        tokens = set(key.split())
        candidates = []
        for c in canon:
            if not compatible(key, c):
                continue
            if (tokens < set(c.split()) or _is_acronym(key, c)
                    or _similarity(key, c) >= alias_threshold
                    or (vectors is not None and float(np.dot(vectors[key], vectors[c])) >= embedding_threshold)):
                candidates.append(c)
        if len(candidates) == 1:
            parent[key] = candidates[0]
        else:
            canon.append(key)

    mapping = {}
    for key, raws in groups.items():
        root = key
        while root in parent:
            root = parent[root]
        # The canonical display name is the longest raw spelling in the root group.
        display = max(groups[root], key=lambda r: (len(r), r))
        for raw in raws:
            mapping[raw] = display
    return mapping
