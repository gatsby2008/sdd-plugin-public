"""Unit tests for the PostToolUse resync-reminder hook.

Two parts: the pure command classifier (`branch_change_flavor`) and the
mismatch decision wired through a throwaway git repo (record a pipeline for one
branch, switch/rename, and assert the reminder fires only when .specwork/ is
keyed to a branch other than HEAD). The hook lives in hooks/ (not a package),
loaded by path.
"""
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SDD_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # lib/tests -> lib -> sdd
_HOOK_PATH = os.path.join(SDD_DIR, "hooks", "resync-reminder.py")

_spec = importlib.util.spec_from_file_location("resync_reminder", _HOOK_PATH)
rr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rr)


class TestBranchChangeFlavor(unittest.TestCase):
    def _assert(self, cmd, expected):
        self.assertEqual(rr.branch_change_flavor(cmd), expected, cmd)

    def test_checkout_branch(self):
        self._assert("git checkout feature/x", "switch")

    def test_switch_branch(self):
        self._assert("git switch main", "switch")

    def test_checkout_new_branch(self):
        self._assert("git checkout -b feature/new", "switch")

    def test_switch_create(self):
        self._assert("git switch -c feature/new", "switch")

    def test_checkout_with_dash_C(self):
        self._assert("git -C /repo checkout main", "switch")

    def test_branch_rename_lower_m(self):
        self._assert("git branch -m new-name", "rename")

    def test_branch_rename_upper_M(self):
        self._assert("git branch -M main", "rename")

    def test_branch_rename_long_flag(self):
        self._assert("git branch --move old new", "rename")

    def test_branch_delete_is_not_a_change(self):
        self._assert("git branch -d feature/x", None)

    def test_branch_list_is_not_a_change(self):
        self._assert("git branch", None)

    def test_checkout_file_path_is_still_switch_flavor(self):
        # Verb-only classification; the sync check below is what suppresses the
        # reminder when HEAD did not actually move.
        self._assert("git checkout -- file.txt", "switch")

    def test_status_is_none(self):
        self._assert("git status", None)

    def test_non_git_is_none(self):
        self._assert("npm run switch-theme", None)

    def test_empty_is_none(self):
        self._assert("", None)


def _git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


class TestMismatchDecision(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.prev = os.getcwd()
        _git("init", "-q", "-b", "feature/foo", cwd=self.tmp)
        _git("config", "user.email", "t@t.t", cwd=self.tmp)
        _git("config", "user.name", "t", cwd=self.tmp)
        (self.tmp / "a.txt").write_text("1", encoding="utf-8")
        _git("add", "-A", cwd=self.tmp)
        _git("commit", "-qm", "c1", cwd=self.tmp)
        state = self.tmp / ".specwork" / "_state"
        state.mkdir(parents=True)
        (state / "foo-state.json").write_text(
            json.dumps({"id": "foo", "branch": "feature/foo"}), encoding="utf-8"
        )
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self.prev)

    def _run(self, cmd):
        payload = json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": str(self.tmp)}
        )
        proc = subprocess.run(
            ["python3", _HOOK_PATH], input=payload, capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout.strip()

    def test_same_branch_no_reminder(self):
        # state.branch == current branch → silent.
        self.assertEqual(self._run("git checkout -- a.txt"), "")

    def test_switch_to_other_branch_reminds(self):
        _git("checkout", "-q", "-b", "feature/bar", cwd=self.tmp)
        out = self._run("git checkout feature/bar")
        self.assertTrue(out)
        msg = json.loads(out)["systemMessage"]
        self.assertIn("feature/foo", msg)
        self.assertIn("/sdd:restore", msg)

    def test_rename_reminds_with_resync_first(self):
        _git("branch", "-m", "feature/foo-renamed", cwd=self.tmp)
        out = self._run("git branch -m feature/foo-renamed")
        msg = json.loads(out)["systemMessage"]
        # rename flavor leads with /sdd:resync.
        self.assertLess(msg.index("/sdd:resync"), msg.index("/sdd:restore"))

    def test_non_branch_command_silent(self):
        self.assertEqual(self._run("git status"), "")

    def test_no_specwork_silent(self):
        import shutil

        shutil.rmtree(self.tmp / ".specwork")
        _git("checkout", "-q", "-b", "feature/bar", cwd=self.tmp)
        self.assertEqual(self._run("git checkout feature/bar"), "")


if __name__ == "__main__":
    unittest.main()
