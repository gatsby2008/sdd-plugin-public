import os
import sys
import unittest

LIB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, LIB_DIR)

import revert  # noqa: E402


class TestRevertStashParsing(unittest.TestCase):
    SAMPLE = (
        "stash@{0} On main: undo: fix-duplicate-leads\n"  # git prepends "On <branch>: "
        "stash@{1} WIP on main: 1234 unrelated\n"
        "stash@{2} On feature/beta: pause: feature/beta\n"
        "stash@{3} On main: undo: fix-duplicate-leads\n"  # older undo, same slug
    )

    def test_parse_undo_stashes_filters_to_f_undo_only(self):
        self.assertEqual(
            revert.parse_undo_stashes(self.SAMPLE),
            [
                ("stash@{0}", "fix-duplicate-leads"),
                ("stash@{3}", "fix-duplicate-leads"),
            ],
        )

    def test_parse_ignores_f_pause_and_manual_stashes(self):
        # The pause and plain WIP entries must never be returned, so /sdd:undo
        # --restore can't pop someone else's paused pipeline or unrelated work.
        refs = [ref for ref, _ in revert.parse_undo_stashes(self.SAMPLE)]
        self.assertNotIn("stash@{1}", refs)
        self.assertNotIn("stash@{2}", refs)

    def test_latest_undo_stash_returns_newest(self):
        self.assertEqual(revert.latest_undo_stash(self.SAMPLE), "stash@{0}")

    def test_latest_undo_stash_none_when_absent(self):
        self.assertIsNone(revert.latest_undo_stash("stash@{0} pause: feature/x\n"))
        self.assertIsNone(revert.latest_undo_stash(""))

    def test_empty_input(self):
        self.assertEqual(revert.parse_undo_stashes(""), [])

    def test_marker_needs_colon(self):
        # A message that mentions "undo" without the "undo: " marker (no
        # colon) is not a match — e.g. an unrelated WIP stash about this helper.
        self.assertEqual(
            revert.parse_undo_stashes("stash@{0} On main: WIP rework undo helper\n"),
            [],
        )

    def test_matches_with_git_on_branch_prefix(self):
        # The real-world shape: git stores "On <branch>: undo: <slug>".
        self.assertEqual(
            revert.parse_undo_stashes("stash@{0} On feature/x: undo: my-slug\n"),
            [("stash@{0}", "my-slug")],
        )


class TestRevertGuards(unittest.TestCase):
    def test_undo_aborts_on_clean_tree(self):
        orig = revert.affected_paths
        revert.affected_paths = lambda: []
        try:
            code, msg = revert.do_undo("any-slug")
        finally:
            revert.affected_paths = orig
        self.assertEqual(code, 1)
        self.assertIn("clean", msg.lower())

    def test_hard_aborts_on_clean_tree(self):
        orig = revert.affected_paths
        revert.affected_paths = lambda: []
        try:
            code, msg = revert.do_hard()
        finally:
            revert.affected_paths = orig
        self.assertEqual(code, 1)

    def test_restore_reports_when_no_undo_stash(self):
        orig = revert._git_stash_list
        revert._git_stash_list = lambda: "stash@{0} pause: feature/x\n"
        try:
            code, msg = revert.do_restore()
        finally:
            revert._git_stash_list = orig
        self.assertEqual(code, 1)
        self.assertIn("No undo stash", msg)


if __name__ == "__main__":
    unittest.main()
