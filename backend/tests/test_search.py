"""
Tests for the symbol search ranking and index.

Runs on the standard library alone — no pydantic, FastAPI or scanned project
required — which is the whole reason app.scanner.knowledge_graph.search keeps
itself free of third-party imports.

    python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.scanner.knowledge_graph.search import (  # noqa: E402
    TIER_ACRONYM,
    TIER_EXACT_NAME,
    TIER_EXACT_QNAME,
    TIER_PREFIX_NAME,
    TIER_SUBSEQ_QNAME,
    TIER_SUBSTR_NAME,
    TIER_SUBSTR_QNAME,
    SymbolSearchIndex,
    acronym_of,
    score,
    subsequence_penalty,
)


class TestAcronym(unittest.TestCase):

    def test_camel_case(self):
        self.assertEqual(acronym_of("CallGraphBuilder"), "cgb")

    def test_snake_case(self):
        self.assertEqual(acronym_of("resolve_symbol"), "rs")

    def test_capital_run_followed_by_word(self):
        # The "R" of Response starts a word even though "HTTP" is all caps.
        self.assertEqual(acronym_of("HTTPResponse"), "hr")

    def test_single_word(self):
        self.assertEqual(acronym_of("lookup"), "l")

    def test_leading_underscore_is_not_an_initial(self):
        self.assertEqual(acronym_of("_private_helper"), "ph")

    def test_dotted_and_hyphenated(self):
        self.assertEqual(acronym_of("a.b-c d"), "abcd")

    def test_empty(self):
        self.assertEqual(acronym_of(""), "")


class TestSubsequencePenalty(unittest.TestCase):

    def test_contiguous_beats_scattered(self):
        tight = subsequence_penalty("abc", "abcxxxx")
        loose = subsequence_penalty("abc", "axbxcxx")
        self.assertIsNotNone(tight)
        self.assertIsNotNone(loose)
        self.assertLess(tight, loose)

    def test_early_beats_late(self):
        self.assertLess(
            subsequence_penalty("abc", "abcyyyy"),
            subsequence_penalty("abc", "yyyyabc"),
        )

    def test_order_matters(self):
        self.assertIsNone(subsequence_penalty("cba", "abc"))

    def test_missing_character(self):
        self.assertIsNone(subsequence_penalty("abz", "abc"))

    def test_empty_query(self):
        self.assertIsNone(subsequence_penalty("", "abc"))


class TestScoreTiers(unittest.TestCase):
    """Each tier must be reachable, and strictly better than the next."""

    def _tier(self, query, name, qname):
        result = score(query, name, qname)
        self.assertIsNotNone(result, f"{query!r} should match {name!r}")
        return result[0]

    def test_exact_name(self):
        self.assertEqual(self._tier("lookup", "lookup", "a.b.lookup"), TIER_EXACT_NAME)

    def test_exact_qualified_name(self):
        self.assertEqual(self._tier("a.b.lookup", "lookup", "a.b.lookup"), TIER_EXACT_QNAME)

    def test_prefix(self):
        self.assertEqual(self._tier("res", "resolve", "a.resolve"), TIER_PREFIX_NAME)

    def test_acronym(self):
        self.assertEqual(self._tier("cgb", "CallGraphBuilder", "a.CallGraphBuilder"), TIER_ACRONYM)

    def test_substring_of_name(self):
        self.assertEqual(self._tier("solve", "resolve", "a.resolve"), TIER_SUBSTR_NAME)

    def test_substring_of_qualified_name(self):
        self.assertEqual(
            self._tier("resolver.res", "resolve", "app.resolver.resolve"),
            TIER_SUBSTR_QNAME,
        )

    def test_subsequence_of_qualified_name(self):
        self.assertEqual(self._tier("asr", "resolve", "app.scanner.resolve"), TIER_SUBSEQ_QNAME)

    def test_tiers_are_strictly_ordered(self):
        self.assertLess(TIER_EXACT_NAME, TIER_EXACT_QNAME)
        self.assertLess(TIER_EXACT_QNAME, TIER_PREFIX_NAME)
        self.assertLess(TIER_PREFIX_NAME, TIER_ACRONYM)
        self.assertLess(TIER_ACRONYM, TIER_SUBSTR_NAME)
        self.assertLess(TIER_SUBSTR_NAME, TIER_SUBSTR_QNAME)
        self.assertLess(TIER_SUBSTR_QNAME, TIER_SUBSEQ_QNAME)

    def test_no_match(self):
        self.assertIsNone(score("zzzq", "resolve", "a.resolve"))

    def test_blank_query_never_matches(self):
        self.assertIsNone(score("", "resolve", "a.resolve"))
        self.assertIsNone(score("   ", "resolve", "a.resolve"))

    def test_case_insensitive(self):
        self.assertEqual(self._tier("LOOKUP", "lookup", "a.b.lookup"), TIER_EXACT_NAME)
        self.assertEqual(self._tier("lookup", "LOOKUP", "a.b.LOOKUP"), TIER_EXACT_NAME)

    def test_single_char_prefers_prefix_over_acronym(self):
        # A one-letter query would make every same-initial symbol an acronym
        # match, so acronym matching is suppressed below two characters.
        self.assertEqual(self._tier("c", "CallGraphBuilder", "a.CallGraphBuilder"), TIER_PREFIX_NAME)


class TestSymbolSearchIndex(unittest.TestCase):

    SYMBOLS = [
        ("app.scanner.call_graph.resolver.CallResolver.resolve", "resolve", "method"),
        ("app.scanner.import_resolver.resolver.ImportResolver.resolve", "resolve", "method"),
        ("app.scanner.call_graph.builder.CallGraphBuilder", "CallGraphBuilder", "class"),
        ("app.scanner.symbol_index.SymbolIndex.lookup", "lookup", "method"),
        ("app.scanner.scanner.ProjectScanner.scan", "scan", "method"),
        ("app.scanner.filesystem.walk", "walk", "function"),
    ]

    def setUp(self):
        self.index = SymbolSearchIndex()
        for qname, name, kind in self.SYMBOLS:
            self.index.add(f"symbol:{qname}", name, qname, kind)

    def _names(self, *args, **kwargs):
        return [qname for _id, qname, _type in self.index.search(*args, **kwargs)]

    def test_len(self):
        self.assertEqual(len(self.index), len(self.SYMBOLS))

    def test_exact_name_ranks_first(self):
        self.assertEqual(self._names("scan")[0], "app.scanner.scanner.ProjectScanner.scan")

    def test_acronym_finds_class(self):
        self.assertIn("app.scanner.call_graph.builder.CallGraphBuilder", self._names("cgb"))

    def test_limit_is_respected(self):
        self.assertEqual(len(self._names("resolve", limit=1)), 1)

    def test_type_filter(self):
        results = self.index.search("resolve", types={"class"})
        self.assertTrue(all(kind == "class" for _id, _qname, kind in results))

    def test_type_filter_empty_set_matches_nothing(self):
        self.assertEqual(self.index.search("resolve", types=set()), [])

    def test_blank_query_returns_nothing(self):
        self.assertEqual(self.index.search(""), [])
        self.assertEqual(self.index.search("   "), [])
        self.assertEqual(self.index.search(None), [])

    def test_no_match_returns_empty(self):
        self.assertEqual(self.index.search("qqqqzzz"), [])

    def test_ties_are_alphabetically_stable(self):
        # Both resolvers are equal-tier exact name matches; order must be
        # deterministic rather than dependent on insertion or dict order.
        first = self._names("resolve")
        for _ in range(5):
            self.assertEqual(self._names("resolve"), first)
        tied = [n for n in first if n.endswith(".resolve")]
        self.assertEqual(tied, sorted(tied))

    def test_returns_node_ids_that_round_trip(self):
        for node_id, qname, _kind in self.index.search("resolve"):
            self.assertEqual(node_id, f"symbol:{qname}")

    def test_from_graph_indexes_only_symbol_nodes(self):
        class FakeType:
            def __init__(self, value): self.value = value

        class FakeNode:
            def __init__(self, name, qualified_name, value):
                self.name = name
                self.qualified_name = qualified_name
                self.type = FakeType(value)

        class FakeGraph:
            nodes = {
                "symbol:a.b.thing": FakeNode("thing", "a.b.thing", "function"),
                "module:a.b": FakeNode("a.b", "a.b", "module"),
                "file:a/b.py": FakeNode("b.py", None, "file"),
            }

        index = SymbolSearchIndex.from_graph(FakeGraph())
        self.assertEqual(len(index), 1)
        self.assertEqual(index.search("thing")[0][1], "a.b.thing")


if __name__ == "__main__":
    unittest.main(verbosity=2)
