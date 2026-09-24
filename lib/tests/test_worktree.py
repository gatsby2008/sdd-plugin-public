import os
import sys
import unittest
from unittest import mock

LIB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, LIB_DIR)

import worktree  # noqa: E402


class TestParsePorcelain(unittest.TestCase):
    def test_empty_is_clean(self):
        self.assertEqual(worktree.parse_porcelain(""), [])

    def test_changed_files(self):
        out = " M src/A.java\n?? new.txt\nA  staged.txt\n"
        self.assertEqual(
            worktree.parse_porcelain(out), ["src/A.java", "new.txt", "staged.txt"]
        )

    def test_rename_keeps_new_path(self):
        out = "R  old/name.md -> new/name.md\n"
        self.assertEqual(worktree.parse_porcelain(out), ["new/name.md"])

    def test_exclude_agent_files(self):
        out = " M CLAUDE.md\n M AGENTS.md\n M src/Real.java\n"
        self.assertEqual(
            worktree.parse_porcelain(out, exclude_agent_files=True), ["src/Real.java"]
        )

    def test_exclude_agent_files_only_top_level_name(self):
        # An agent-named file is matched by basename regardless of directory.
        out = " M docs/CLAUDE.md\n"
        self.assertEqual(worktree.parse_porcelain(out, exclude_agent_files=True), [])


class TestDirtyFilesAndIsClean(unittest.TestCase):
    def test_dirty_files_parses_git_output(self):
        with mock.patch.object(worktree, "_git_porcelain", return_value=" M src/A.java\n?? new.txt\n"):
            self.assertEqual(worktree.dirty_files(), ["src/A.java", "new.txt"])

    def test_is_clean_true_when_no_changes(self):
        with mock.patch.object(worktree, "_git_porcelain", return_value=""):
            self.assertTrue(worktree.is_clean())

    def test_is_clean_false_when_changes(self):
        with mock.patch.object(worktree, "_git_porcelain", return_value=" M x\n"):
            self.assertFalse(worktree.is_clean())

    def test_dirty_files_excludes_agent_files(self):
        with mock.patch.object(worktree, "_git_porcelain", return_value=" M CLAUDE.md\n M src/R.java\n"):
            self.assertEqual(worktree.dirty_files(exclude_agent_files=True), ["src/R.java"])

    def test_git_missing_degrades_to_clean(self):
        # _git_porcelain catches FileNotFoundError → returns "" → tree reads clean.
        with mock.patch("subprocess.check_output", side_effect=FileNotFoundError):
            self.assertEqual(worktree.dirty_files(), [])
            self.assertTrue(worktree.is_clean())


if __name__ == "__main__":
    unittest.main()
