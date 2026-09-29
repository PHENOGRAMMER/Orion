"""
Tests for filesystem path safety.

These cover the cases that actually matter for /graph/browse and /graph/scan:
".." traversal and — the one that is easy to get wrong — symlinks pointing out
of an allowed root. Stdlib only.

    python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.paths import (  # noqa: E402
    PathNotAllowed,
    default_roots,
    is_within_roots,
    parse_roots,
    safe_directory,
)


class TestParseRoots(unittest.TestCase):

    def test_empty_and_none_yield_no_roots(self):
        self.assertEqual(parse_roots(""), [])
        self.assertEqual(parse_roots(None), [])
        self.assertEqual(parse_roots("   "), [])

    def test_single_path(self):
        roots = parse_roots(tempfile.gettempdir())
        self.assertEqual(len(roots), 1)
        self.assertTrue(roots[0].is_absolute())

    def test_comma_separated(self):
        tmp = tempfile.gettempdir()
        self.assertEqual(len(parse_roots(f"{tmp},{tmp}/.")), 1)  # same dir, deduped

    def test_os_separator(self):
        tmp = tempfile.gettempdir()
        home = str(Path.home())
        roots = parse_roots(f"{tmp}{os.pathsep}{home}")
        self.assertEqual(len(roots), 2)

    def test_duplicates_are_removed(self):
        tmp = tempfile.gettempdir()
        self.assertEqual(len(parse_roots(f"{tmp},{tmp},{tmp}")), 1)

    def test_blank_segments_are_skipped(self):
        tmp = tempfile.gettempdir()
        self.assertEqual(len(parse_roots(f"{tmp},,  ,{tmp}")), 1)

    def test_results_are_absolute_and_resolved(self):
        for root in parse_roots(f"{tempfile.gettempdir()}/./"):
            self.assertTrue(root.is_absolute())
            self.assertNotIn("..", root.parts)


class TestRootContainment(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.allowed = base / "allowed"
        self.secret = base / "secret"
        (self.allowed / "sub" / "deep").mkdir(parents=True)
        self.secret.mkdir()
        (self.secret / "keys.txt").write_text("sensitive")
        self.roots = [self.allowed]

    def tearDown(self):
        self.tmp.cleanup()

    # -- allowed ------------------------------------------------------

    def test_root_itself_is_allowed(self):
        self.assertEqual(safe_directory(str(self.allowed), self.roots), self.allowed)

    def test_direct_child_is_allowed(self):
        target = self.allowed / "sub"
        self.assertEqual(safe_directory(str(target), self.roots), target)

    def test_nested_child_is_allowed(self):
        target = self.allowed / "sub" / "deep"
        self.assertEqual(safe_directory(str(target), self.roots), target)

    def test_redundant_segments_normalise_inside_root(self):
        messy = str(self.allowed / "sub" / ".." / "sub" / "deep")
        self.assertEqual(safe_directory(messy, self.roots), self.allowed / "sub" / "deep")

    # -- denied -------------------------------------------------------

    def test_dotdot_traversal_is_denied(self):
        with self.assertRaises(PathNotAllowed):
            safe_directory(str(self.allowed / ".." / "secret"), self.roots)

    def test_sibling_outside_root_is_denied(self):
        with self.assertRaises(PathNotAllowed):
            safe_directory(str(self.secret), self.roots)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unsupported")
    def test_symlink_escape_is_denied(self):
        """
        The case plain ".." stripping misses: a link *inside* the root that
        points outside it. Containment must be checked after resolution.
        """
        link = self.allowed / "escape"
        try:
            link.symlink_to(self.secret, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("cannot create symlink in this environment")

        self.assertTrue(link.exists(), "symlink should resolve to a real dir")
        with self.assertRaises(PathNotAllowed):
            safe_directory(str(link), self.roots)

    def test_nonexistent_path_inside_root_is_denied(self):
        with self.assertRaises(PathNotAllowed):
            safe_directory(str(self.allowed / "nope"), self.roots)

    def test_file_is_rejected_as_not_a_directory(self):
        target = self.allowed / "f.txt"
        target.write_text("x")
        with self.assertRaises(PathNotAllowed):
            safe_directory(str(target), self.roots)

    def test_empty_root_list_denies_everything(self):
        self.assertFalse(is_within_roots(self.allowed, []))
        with self.assertRaises(PathNotAllowed):
            safe_directory(str(self.allowed), [])

    def test_multiple_roots_all_permitted(self):
        roots = [self.allowed, self.secret]
        self.assertEqual(safe_directory(str(self.secret), roots), self.secret)
        self.assertEqual(safe_directory(str(self.allowed), roots), self.allowed)

    def test_sibling_prefix_is_not_treated_as_child(self):
        """'/x/allowed-evil' must not count as inside '/x/allowed'."""
        evil = self.allowed.parent / "allowed-evil"
        evil.mkdir()
        self.assertFalse(is_within_roots(evil, self.roots))
        with self.assertRaises(PathNotAllowed):
            safe_directory(str(evil), self.roots)


class TestDefaultRoots(unittest.TestCase):

    def test_defaults_to_home(self):
        roots = default_roots()
        self.assertEqual(len(roots), 1)
        self.assertEqual(roots[0], Path.home().resolve())

    def test_default_is_narrower_than_filesystem_root(self):
        self.assertNotEqual(default_roots()[0], Path(Path().resolve().anchor))


if __name__ == "__main__":
    unittest.main(verbosity=2)
