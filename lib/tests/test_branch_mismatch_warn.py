"""Unit tests for the PreToolUse(Edit|Write) branch-mismatch warning hook.

Covers the three .specwork/ ownership states, the once-per-session dedup and
what re-arms it, the non-edit-tool short circuit, and the stale-marker sweep.
The hook lives in hooks/ (not a package), loaded by path; it reuses gates from
lib, so tests run inside a temp git repo with a temp .specwork tree.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SDD_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # lib/tests -> lib -> sdd
LIB = os.path.join(SDD_DIR, "lib")
sys.path.insert(0, LIB)

_HOOK_PATH = os.path.join(SDD_DIR, "hooks", "branch-mismatch-warn.py")
_spec = importlib.util.spec_from_file_location("branch_mismatch_warn", _HOOK_PATH)
bmw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bmw)


def _git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


class HookCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.data = Path(tempfile.mkdtemp())  # stands in for $CLAUDE_PLUGIN_DATA
        _git("init", "-q", "-b", "feature/mine", cwd=self.tmp)
        _git("config", "user.email", "t@t.t", cwd=self.tmp)
        _git("config", "user.name", "t", cwd=self.tmp)
        (self.tmp / "a.txt").write_text("1", encoding="utf-8")
        _git("add", "-A", cwd=self.tmp)
        _git("commit", "-qm", "c1", cwd=self.tmp)
        (self.tmp / ".specwork" / "_state").mkdir(parents=True)

    def _pipeline(self, slug, branch, base_branch=None):
        payload = {"id": slug, "branch": branch}
        if base_branch is not None:
            payload["base_branch"] = base_branch
        (self.tmp / ".specwork" / "_state" / f"{slug}-state.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    def _run(self, tool_name="Edit", session_id="sess-1"):
        payload = json.dumps(
            {
                "session_id": session_id,
                "tool_name": tool_name,
                "tool_input": {"file_path": str(self.tmp / "a.txt")},
                "cwd": str(self.tmp),
            }
        )
        env = dict(os.environ, CLAUDE_PLUGIN_DATA=str(self.data))
        proc = subprocess.run(
            ["python3", _HOOK_PATH],
            input=payload,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout.strip()


class TestOwnershipStates(HookCase):
    def test_warns_when_pipeline_belongs_to_another_branch(self):
        self._pipeline("other", "feature/other")
        out = self._run()
        msg = json.loads(out)["systemMessage"]
        self.assertIn("feature/mine", msg)
        self.assertIn("feature/other", msg)
        self.assertIn("/sdd:pause", msg)
        self.assertIn("/sdd:close", msg)

    def test_silent_when_pipeline_is_ours(self):
        self._pipeline("mine", "feature/mine")
        self.assertEqual(self._run(), "")

    def test_silent_on_the_pipelines_base_branch(self):
        # Post-merge cleanup: /sdd:close is meant to run from here.
        self._pipeline("other", "feature/other", base_branch="feature/mine")
        self.assertEqual(self._run(), "")

    def test_silent_with_no_pipeline_on_disk(self):
        self.assertEqual(self._run(), "")

    def test_never_blocks(self):
        # Exit code 0 even when warning — exit 2 would deny the edit.
        self._pipeline("other", "feature/other")
        self.assertTrue(self._run())  # warned, and _run asserts returncode == 0


class TestDedup(HookCase):
    def test_warns_once_per_session(self):
        self._pipeline("other", "feature/other")
        self.assertTrue(self._run())
        self.assertEqual(self._run(), "")
        self.assertEqual(self._run(), "")

    def test_new_session_warns_again(self):
        self._pipeline("other", "feature/other")
        self.assertTrue(self._run(session_id="sess-1"))
        self.assertTrue(self._run(session_id="sess-2"))

    def test_branch_change_rearms(self):
        self._pipeline("other", "feature/other")
        self.assertTrue(self._run())
        _git("checkout", "-q", "-b", "feature/third", cwd=self.tmp)
        self.assertTrue(self._run())  # different branch → its own warning

    def test_different_pipeline_rearms(self):
        self._pipeline("other", "feature/other")
        self.assertTrue(self._run())
        os.remove(self.tmp / ".specwork" / "_state" / "other-state.json")
        self._pipeline("third", "feature/third")
        self.assertTrue(self._run())


class TestToolFilter(HookCase):
    def test_ignores_non_edit_tools(self):
        self._pipeline("other", "feature/other")
        self.assertEqual(self._run(tool_name="Bash"), "")
        self.assertEqual(self._run(tool_name="Read"), "")

    def test_covers_every_edit_tool(self):
        self._pipeline("other", "feature/other")
        for i, tool in enumerate(("Edit", "Write", "MultiEdit", "NotebookEdit")):
            # A fresh session id per tool so dedup does not mask the check.
            self.assertTrue(
                self._run(tool_name=tool, session_id="sess-{}".format(i)), tool
            )


class TestMarkerSweep(unittest.TestCase):
    def setUp(self):
        self.data = Path(tempfile.mkdtemp())
        self._prev = os.environ.get("CLAUDE_PLUGIN_DATA")
        os.environ["CLAUDE_PLUGIN_DATA"] = str(self.data)
        self.addCleanup(self._restore)

    def _restore(self):
        if self._prev is None:
            os.environ.pop("CLAUDE_PLUGIN_DATA", None)
        else:
            os.environ["CLAUDE_PLUGIN_DATA"] = self._prev

    def test_sweep_removes_only_expired_markers(self):
        fresh = Path(bmw.marker_path("s1", "/repo", "feature/a", "a"))
        stale = Path(bmw.marker_path("s2", "/repo", "feature/b", "b"))
        bmw.record_warned(str(fresh))
        bmw.record_warned(str(stale))
        old = time.time() - bmw.MARKER_TTL_SECONDS - 60
        os.utime(stale, (old, old))
        bmw.sweep_stale_markers()
        self.assertTrue(fresh.exists())
        self.assertFalse(stale.exists())

    def test_sweep_on_missing_dir_is_a_noop(self):
        bmw.sweep_stale_markers()  # never created — must not raise

    def test_marker_dir_never_touches_claude_home(self):
        self.assertNotIn(os.path.join(".claude", ""), bmw.marker_dir() + os.sep)


if __name__ == "__main__":
    unittest.main()
