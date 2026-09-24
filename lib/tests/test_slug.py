import os
import sys
import unittest

LIB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, LIB_DIR)

import slug as slug_mod  # noqa: E402


class TestSlug(unittest.TestCase):
    def test_strip_prefix(self):
        self.assertEqual(slug_mod.strip_branch_prefix("feature/IR-70"), "IR-70")
        self.assertEqual(slug_mod.strip_branch_prefix("hotfix/PROJ-1"), "PROJ-1")
        self.assertEqual(slug_mod.strip_branch_prefix("IR-70"), "IR-70")  # no prefix

    def test_normalize_slug(self):
        self.assertEqual(slug_mod.normalize_slug("Add Consent Flow"), "add-consent-flow")
        self.assertEqual(slug_mod.normalize_slug("--A__b  c--"), "a-b-c")

    def test_slug_from_branch(self):
        self.assertEqual(slug_mod.slug_from_branch("feature/IR-70"), "ir-70")
        self.assertEqual(
            slug_mod.slug_from_branch("feature/add-consent-flow"), "add-consent-flow"
        )

    def test_ticket_strict_jira(self):
        self.assertEqual(slug_mod.ticket_from_branch("feature/IR-70"), ("IR-70", "jira"))
        self.assertEqual(
            slug_mod.ticket_from_branch("feature/PROJ-1234-extra"), ("PROJ-1234", "jira")
        )

    def test_ticket_loose_dotted_is_freetext(self):
        self.assertEqual(slug_mod.ticket_from_branch("feature/IR-70.1"), ("IR-70.1", "freetext"))

    def test_ticket_none(self):
        self.assertEqual(
            slug_mod.ticket_from_branch("feature/add-consent-flow"), ("", "freetext")
        )

    def test_lowercase_branch_ticket_uppercased(self):
        self.assertEqual(slug_mod.ticket_from_branch("feature/ir-70"), ("IR-70", "jira"))

    def test_resolve_branch(self):
        self.assertEqual(
            slug_mod.resolve_branch("feature/IR-70"),
            {
                "branch": "feature/IR-70",
                "unprefixed": "IR-70",
                "slug": "ir-70",
                "ticket": "IR-70",
                "input_type": "jira",
            },
        )


class TestSlugCli(unittest.TestCase):
    def test_cli_prints_json_for_given_branch(self):
        import json
        import subprocess

        result = subprocess.run(
            ["python3", os.path.join(LIB_DIR, "slug.py"), "feature/IR-70"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        self.assertEqual(data["slug"], "ir-70")
        self.assertEqual(data["ticket"], "IR-70")
        self.assertEqual(data["input_type"], "jira")


if __name__ == "__main__":
    unittest.main()
