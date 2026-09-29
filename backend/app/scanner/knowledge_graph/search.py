"""
Symbol search index.

Ranked fuzzy search over the symbol nodes of a KnowledgeGraph.

Ranking is tiered rather than a single blended score, because for code search
the *kind* of match matters more than how many characters happened to line up:
an exact name hit should always beat a lucky subsequence match buried in a long
dotted path, no matter how tight that subsequence is.

Tiers, best to worst:

    0  exact match on the bare symbol name        lookup      -> SymbolIndex.lookup
    1  exact match on the fully-qualified name    a.b.lookup  -> a.b.lookup
    2  prefix match on the bare name              res         -> resolve
    3  camelCase / snake_case acronym             cgb         -> CallGraphBuilder
    4  substring of the bare name                 solve       -> resolve
    5  substring of the qualified name            resolver.re -> a.resolver.resolve
    6  subsequence of the qualified name          asr         -> app.scanner.resolve

This module deliberately has **no third-party imports**. Everything here is
plain stdlib, so the ranking logic can be unit tested without pydantic,
FastAPI, or a real scanned project.
"""

from __future__ import annotations

from typing import Iterable, Sequence

# ----------------------------------------------------------------------
# Ranking tiers — lower sorts first.
# ----------------------------------------------------------------------

TIER_EXACT_NAME = 0
TIER_EXACT_QNAME = 1
TIER_PREFIX_NAME = 2
TIER_ACRONYM = 3
TIER_SUBSTR_NAME = 4
TIER_SUBSTR_QNAME = 5
TIER_SUBSEQ_QNAME = 6

#: Characters treated as word separators when deriving an acronym.
_SEPARATORS = "_-. "

#: Minimum query length before acronym matching kicks in. A single letter
#: would otherwise make every symbol starting with that letter an "acronym"
#: match, drowning out the more meaningful prefix tier.
_MIN_ACRONYM_QUERY = 2


def acronym_of(name: str) -> str:
    """
    Derive a lowercase acronym from a symbol name.

        CallGraphBuilder -> "cgb"
        resolve_symbol   -> "rs"
        HTTPResponse     -> "hr"
        lookup           -> "l"

    A character contributes an initial when it starts the name, follows a
    separator, starts a camelCase hump, or is the final capital of an
    all-caps run that runs into a lowercase word (the "R" in HTTPResponse).
    """
    initials: list[str] = []
    length = len(name)

    for i, char in enumerate(name):
        if char in _SEPARATORS:
            continue

        prev = name[i - 1] if i > 0 else None
        nxt = name[i + 1] if i + 1 < length else None

        at_start = prev is None or prev in _SEPARATORS
        camel_hump = char.isupper() and prev is not None and prev.islower()
        acronym_tail = (
            char.isupper()
            and prev is not None
            and prev.isupper()
            and nxt is not None
            and nxt.islower()
        )

        if at_start or camel_hump or acronym_tail:
            initials.append(char.lower())

    return "".join(initials)


def subsequence_penalty(query: str, text: str) -> int | None:
    """
    If every character of ``query`` appears in ``text`` in order, return a
    penalty where lower means a tighter match. Return None otherwise.

    The penalty sums the gaps between matched characters plus the offset of
    the first match, so matches that start early and stay contiguous win.
    Both arguments are expected to already be lowercase.
    """
    if not query:
        return None

    cursor = 0
    first = -1
    last = -1
    gaps = 0

    for char in query:
        found = text.find(char, cursor)
        if found < 0:
            return None

        if first < 0:
            first = found
        else:
            gaps += found - last - 1

        last = found
        cursor = found + 1

    return gaps + first


def _score(
    query: str,
    name_lower: str,
    qname_lower: str,
    acronym: str,
    name_length: int,
) -> tuple[int, int, int] | None:
    """
    Core ranking. ``query``, ``name_lower``, ``qname_lower`` and ``acronym``
    must all already be lowercase; the index precomputes them so this stays
    allocation-free in the hot loop.

    Returns a ``(tier, penalty, name_length)`` sort key, or None for no match.
    """
    if name_lower == query:
        return (TIER_EXACT_NAME, 0, name_length)

    if qname_lower == query:
        return (TIER_EXACT_QNAME, 0, name_length)

    if name_lower.startswith(query):
        return (TIER_PREFIX_NAME, name_length - len(query), name_length)

    if len(query) >= _MIN_ACRONYM_QUERY and acronym.startswith(query):
        return (TIER_ACRONYM, len(acronym) - len(query), name_length)

    offset = name_lower.find(query)
    if offset >= 0:
        return (TIER_SUBSTR_NAME, offset, name_length)

    offset = qname_lower.find(query)
    if offset >= 0:
        return (TIER_SUBSTR_QNAME, offset, name_length)

    penalty = subsequence_penalty(query, qname_lower)
    if penalty is not None:
        return (TIER_SUBSEQ_QNAME, penalty, name_length)

    return None


def score(query: str, name: str, qualified_name: str) -> tuple[int, int, int] | None:
    """
    Convenience wrapper around :func:`_score` that does its own normalisation.

    Handy for tests and one-off checks; :class:`SymbolSearchIndex` bypasses it
    and calls ``_score`` directly against precomputed fields.
    """
    normalised = (query or "").strip().lower()
    if not normalised:
        return None

    return _score(
        normalised,
        name.lower(),
        qualified_name.lower(),
        acronym_of(name),
        len(name),
    )


class SymbolSearchIndex:
    """
    A flat, precomputed index over the symbol nodes of a KnowledgeGraph.

    Search is a linear scan. That sounds lazy, but the per-entry work is a
    handful of string comparisons against fields that were lowercased once at
    build time, which keeps a 50k-symbol project comfortably inside interactive
    latency. Swapping in a trie or an n-gram index only pays off well past that,
    and would cost the exact-tier ordering that makes results feel right.

    Entries are tuples rather than objects purely to keep the hot loop tight::

        (node_id, name, qualified_name, node_type, name_lower, qname_lower, acronym)
    """

    __slots__ = ("_entries",)

    #: Node-ID prefix identifying symbol nodes in the knowledge graph.
    SYMBOL_PREFIX = "symbol:"

    def __init__(self) -> None:
        self._entries: list[tuple[str, str, str, str, str, str, str]] = []

    def __len__(self) -> int:
        return len(self._entries)

    def add(
        self,
        node_id: str,
        name: str,
        qualified_name: str,
        node_type: str,
    ) -> None:
        """
        Register one symbol, precomputing everything the ranking needs.
        """
        self._entries.append(
            (
                node_id,
                name,
                qualified_name,
                node_type,
                name.lower(),
                qualified_name.lower(),
                acronym_of(name),
            )
        )

    @classmethod
    def from_graph(cls, graph) -> "SymbolSearchIndex":
        """
        Build an index from a KnowledgeGraph.

        Only symbol nodes are indexed — module and file nodes are reachable
        through their own endpoints and would otherwise crowd the results.
        Accessed purely by duck typing (``graph.nodes``) so this module stays
        free of imports from the graph package.
        """
        index = cls()

        for node_id, node in graph.nodes.items():
            if not node_id.startswith(cls.SYMBOL_PREFIX):
                continue

            qualified_name = node.qualified_name or node.name
            if not qualified_name:
                continue

            node_type = getattr(node.type, "value", str(node.type))
            index.add(node_id, node.name, qualified_name, node_type)

        return index

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        types: Iterable[str] | None = None,
    ) -> list[tuple[str, str, str]]:
        """
        Return up to ``limit`` matches, best first.

        Each result is ``(node_id, qualified_name, node_type)``. ``types``
        optionally restricts results to the given node type values, e.g.
        ``{"function", "method"}``.
        """
        normalised = (query or "").strip().lower()
        if not normalised:
            return []

        allowed = set(types) if types is not None else None

        scored: list[tuple[tuple[int, int, int], str, str, str]] = []

        for (
            node_id,
            _name,
            qualified_name,
            node_type,
            name_lower,
            qname_lower,
            acronym,
        ) in self._entries:

            if allowed is not None and node_type not in allowed:
                continue

            key = _score(
                normalised,
                name_lower,
                qname_lower,
                acronym,
                len(name_lower),
            )

            if key is None:
                continue

            scored.append((key, qualified_name, node_id, node_type))

        # Qualified name is the final tie-breaker so equally-ranked results
        # come back in a stable, alphabetical order instead of dict order.
        scored.sort(key=lambda item: (item[0], item[1]))

        return [
            (node_id, qualified_name, node_type)
            for _key, qualified_name, node_id, node_type in scored[:limit]
        ]
