import os
import sys
import unittest

LIB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, LIB_DIR)

import titles  # noqa: E402


class TestTitles(unittest.TestCase):
    def test_ticket_from_branch(self):
        self.assertEqual(titles.ticket_from_branch("feature/PROJ-123-foo"), "PROJ-123")
        self.assertEqual(titles.ticket_from_branch("feature/add-thing"), "")

    def test_commit_subject_with_ticket(self):
        self.assertEqual(
            titles.commit_subject("feature/PROJ-123-foo", "feat", "add consent flow"),
            "[PROJ-123] feat: add consent flow",
        )

    def test_commit_subject_no_ticket_uses_placeholder(self):
        self.assertEqual(
            titles.commit_subject("feature/add-thing", "fix", "bug"),
            "[NO-TICKET] fix: bug",
        )

    def test_mr_title_with_ticket(self):
        self.assertEqual(
            titles.mr_title("feature/IR-70", "feat", "do it"),
            "[IR-70] feat: do it",
        )

    def test_mr_title_no_ticket_omits_bracket(self):
        self.assertEqual(
            titles.mr_title("feature/add-thing", "chore", "tidy"),
            "chore: tidy",
        )


if __name__ == "__main__":
    unittest.main()
