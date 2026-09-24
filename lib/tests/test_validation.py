"""Unit tests for the quality-gate validation marker (lib/validation.py).

Exercises the record/is_valid round-trip in a throwaway git repo: a fresh stamp
matches HEAD, a new commit invalidates it, and a missing marker reads invalid.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

LIB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, LIB_DIR)

import validation  # noqa: E402


def _git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


class TestValidationMarker(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.prev = os.getcwd()
        _git("init", "-q", cwd=self.tmp)
        _git("config", "user.email", "t@t.t", cwd=self.tmp)
        _git("config", "user.name", "t", cwd=self.tmp)
        (self.tmp / "a.txt").write_text("1", encoding="utf-8")
        _git("add", "-A", cwd=self.tmp)
        _git("commit", "-qm", "c1", cwd=self.tmp)
        (self.tmp / ".specwork" / "_state").mkdir(parents=True)
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self.prev)

    def _commit(self, name):
        (self.tmp / name).write_text("x", encoding="utf-8")
        _git("add", "-A", cwd=self.tmp)
        _git("commit", "-qm", name, cwd=self.tmp)

    def test_record_then_valid(self):
        sha = validation.record("demo")
        self.assertTrue(sha)
        self.assertTrue(validation.is_valid("demo"))

    def test_marker_goes_stale_after_new_commit(self):
        validation.record("demo")
        self.assertTrue(validation.is_valid("demo"))
        self._commit("b.txt")  # HEAD moves
        self.assertFalse(validation.is_valid("demo"))

    def test_missing_marker_is_invalid(self):
        self.assertFalse(validation.is_valid("demo"))

    def test_record_writes_expected_path_and_sha(self):
        import json

        sha = validation.record("demo")
        marker = self.tmp / ".specwork" / "_state" / "demo-validated.json"
        self.assertTrue(marker.is_file())
        data = json.loads(marker.read_text(encoding="utf-8"))
        self.assertEqual(data["sha"], sha)
        self.assertIn("at", data)

    def test_re_record_after_commit_revalidates(self):
        validation.record("demo")
        self._commit("c.txt")
        self.assertFalse(validation.is_valid("demo"))
        validation.record("demo")  # stamp the new HEAD
        self.assertTrue(validation.is_valid("demo"))


if __name__ == "__main__":
    unittest.main()
