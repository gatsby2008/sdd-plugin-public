import os
import sys
import unittest
from unittest import mock

LIB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, LIB_DIR)

import stash  # noqa: E402


class TestStash(unittest.TestCase):
    SAMPLE = (
        "stash@{0} pause: feature/alpha\n"
        "stash@{1} WIP on main: 1234 unrelated\n"
        "stash@{2} pause: feature/beta\n"
        "stash@{3} pause: feature/alpha\n"  # older duplicate of alpha
    )

    def test_pipeline_stashes_filters_and_extracts_branch(self):
        self.assertEqual(
            stash.pipeline_stashes(self.SAMPLE),
            [
                ("stash@{0}", "feature/alpha"),
                ("stash@{2}", "feature/beta"),
                ("stash@{3}", "feature/alpha"),
            ],
        )

    def test_deduplicate_keeps_newest_per_branch(self):
        kept, stale = stash.deduplicate(stash.pipeline_stashes(self.SAMPLE))
        self.assertEqual(kept, [("stash@{0}", "feature/alpha"), ("stash@{2}", "feature/beta")])
        self.assertEqual(stale, [("stash@{3}", "feature/alpha")])

    def test_empty(self):
        self.assertEqual(stash.pipeline_stashes(""), [])
        self.assertEqual(stash.deduplicate([]), ([], []))

    def test_git_missing_degrades_to_empty(self):
        # _git_stash_list catches FileNotFoundError → "" → no kept/stale stashes.
        with mock.patch("subprocess.check_output", side_effect=FileNotFoundError):
            self.assertEqual(stash._git_stash_list(), "")
            self.assertEqual(
                stash.deduplicate(stash.pipeline_stashes(stash._git_stash_list())),
                ([], []),
            )


if __name__ == "__main__":
    unittest.main()
