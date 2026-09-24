"""Unit tests for the PreToolUse coverage-gate hook's command detection.

The gate logic itself (which classes lack a test) is covered by test_coverage.py;
this file covers the part the hook *adds*: deciding whether a Bash command runs
`git commit`. The hook lives in hooks/ (not a package), so it is loaded by path.
"""
import importlib.util
import os
import unittest

SDD_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # lib/tests -> lib -> sdd
_HOOK_PATH = os.path.join(SDD_DIR, "hooks", "coverage-gate.py")

_spec = importlib.util.spec_from_file_location("coverage_gate", _HOOK_PATH)
cg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cg)


class TestCommandCommits(unittest.TestCase):
    def _assert(self, cmd, expected):
        self.assertEqual(cg.command_commits(cmd), expected, cmd)

    def test_plain_commit(self):
        self._assert("git commit -m 'x'", True)

    def test_commit_amend_no_verify(self):
        # The whole point: --no-verify must not let it slip past.
        self._assert("git commit --amend --no-verify", True)

    def test_commit_with_dash_C_path(self):
        self._assert("git -C /repo commit -m y", True)

    def test_commit_with_dash_c_config(self):
        self._assert("git -c user.name=Z commit -m y", True)

    def test_commit_in_and_chain(self):
        self._assert("git add . && git commit -m y", True)

    def test_commit_after_semicolon(self):
        self._assert("echo hi; git commit -m y", True)

    def test_commit_after_pipe(self):
        self._assert("true | git commit -m y", True)

    def test_status_is_not_commit(self):
        self._assert("git status", False)

    def test_log_grep_commit_is_not_commit(self):
        # 'commit' appears as an option value, not the subcommand.
        self._assert("git log --grep=commit", False)

    def test_show_is_not_commit(self):
        self._assert("git show HEAD --stat", False)

    def test_push_is_not_commit(self):
        self._assert("git push origin main", False)

    def test_unrelated_tool_with_commit_word(self):
        self._assert("npm run commit-lint", False)

    def test_empty_command(self):
        self._assert("", False)


if __name__ == "__main__":
    unittest.main()
