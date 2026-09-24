import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

LIB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, LIB_DIR)

import state as state_mod  # noqa: E402


class TestState(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.path = self.tmp / "demo-state.json"
        self.path.write_text(
            json.dumps(
                {
                    "id": "old-slug",
                    "branch": "feature/old-slug",
                    "ticket": None,
                    "input_type": "freetext",
                    "spec_file": ".specwork/_spec/old-slug-spec.md",
                    "source_title": "keep me",
                }
            ),
            encoding="utf-8",
        )

    def test_load_and_update_field(self):
        d = state_mod.update_state_field(str(self.path), "branch", "feature/new")
        self.assertEqual(d["branch"], "feature/new")
        self.assertEqual(state_mod.load_state(str(self.path))["branch"], "feature/new")

    def test_rename_slug_rewrites_paths_and_sets_fields(self):
        d = state_mod.rename_slug(
            str(self.path), "ir-70-new", "old-slug", "feature/IR-70-new", "IR-70", "jira"
        )
        self.assertEqual(d["id"], "ir-70-new")
        self.assertEqual(d["branch"], "feature/IR-70-new")
        self.assertEqual(d["ticket"], "IR-70")
        self.assertEqual(d["input_type"], "jira")
        self.assertEqual(d["spec_file"], ".specwork/_spec/ir-70-new-spec.md")
        # source_title is left untouched.
        self.assertEqual(d["source_title"], "keep me")

    def test_rename_slug_no_double_up_when_new_contains_old(self):
        # old slug "consent" → new "ir-70-consent" must not become "ir-70-ir-70-consent".
        self.path.write_text(
            json.dumps({"id": "consent", "spec_file": ".specwork/_spec/consent-spec.md"}),
            encoding="utf-8",
        )
        d = state_mod.rename_slug(
            str(self.path), "ir-70-consent", "consent", "feature/IR-70-consent", "IR-70", "jira"
        )
        self.assertEqual(d["spec_file"], ".specwork/_spec/ir-70-consent-spec.md")


if __name__ == "__main__":
    unittest.main()
