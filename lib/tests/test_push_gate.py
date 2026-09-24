"""Unit tests for the PreToolUse push-gate hook's command detection.

The marker logic (whether HEAD passed check.sh) is covered by test_validation.py;
this file covers the part the hook *adds*: deciding whether a Bash command runs a
code-bearing `git push`. The hook lives in hooks/ (not a package), loaded by path.
"""
import importlib.util
import os
import unittest

SDD_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # lib/tests -> lib -> sdd
_HOOK_PATH = os.path.join(SDD_DIR, "hooks", "push-gate.py")

_spec = importlib.util.spec_from_file_location("push_gate", _HOOK_PATH)
pg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pg)


class TestCommandPushes(unittest.TestCase):
    def _assert(self, cmd, expected):
        self.assertEqual(pg.command_pushes(cmd), expected, cmd)

    def test_plain_push(self):
        self._assert("git push", True)

    def test_push_with_remote_and_branch(self):
        self._assert("git push origin HEAD", True)

    def test_push_set_upstream(self):
        self._assert("git push -u origin HEAD", True)

    def test_push_with_dash_C_path(self):
        self._assert("git -C /repo push origin main", True)

    def test_push_with_dash_c_config(self):
        self._assert("git -c user.name=Z push", True)

    def test_push_in_and_chain(self):
        self._assert("git add . && git push origin HEAD", True)

    def test_push_after_semicolon(self):
        self._assert("echo hi; git push", True)

    def test_delete_is_not_gated(self):
        # Deleting a remote branch sends no code to validate.
        self._assert("git push origin --delete feature/x", False)
        self._assert("git push -d origin feature/x", False)

    def test_dry_run_is_not_gated(self):
        self._assert("git push --dry-run origin HEAD", False)

    def test_tags_only_is_not_gated(self):
        self._assert("git push --tags", False)

    def test_status_is_not_push(self):
        self._assert("git status", False)

    def test_commit_is_not_push(self):
        self._assert("git commit -m 'push it'", False)

    def test_log_grep_push_is_not_push(self):
        self._assert("git log --grep=push", False)

    def test_unrelated_tool_with_push_word(self):
        self._assert("npm run pushpin", False)

    def test_empty_command(self):
        self._assert("", False)


if __name__ == "__main__":
    unittest.main()
