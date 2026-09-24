"""Unit tests for the SessionStart pipeline-status hook.

Covers the next-step logic across the early-gate states (no spec, open OQs,
no plan, stale plan, ready-to-implement) and the silent-outside-pipeline
behavior. The hook lives in hooks/ (not a package), loaded by path; it reuses
gates/paths from lib, so tests run inside a temp .specwork tree.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SDD_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # lib/tests -> lib -> sdd
LIB = os.path.join(SDD_DIR, "lib")
sys.path.insert(0, LIB)
import gates  # noqa: E402
import paths  # noqa: E402

_HOOK_PATH = os.path.join(SDD_DIR, "hooks", "pipeline-status.py")
_spec = importlib.util.spec_from_file_location("pipeline_status", _HOOK_PATH)
ps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ps)


SPEC_NO_OQ = """# Spec\n\n## Summary\nDo a thing.\n\n## Open Questions\n\n(none)\n"""
SPEC_OPEN_OQ = """# Spec\n\n## Open Questions\n- [ ] unresolved?\n- [x] resolved? — yes\n"""
SPEC_RESOLVED = """# Spec\n\n## Open Questions\n- [x] resolved? — yes\n"""


class TestComputeStatus(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.prev = os.getcwd()
        os.chdir(self.tmp)
        (self.tmp / ".specwork" / "_spec").mkdir(parents=True)
        (self.tmp / ".specwork" / "_plan").mkdir(parents=True)
        (self.tmp / ".specwork" / "_state").mkdir(parents=True)

    def tearDown(self):
        os.chdir(self.prev)

    def _spec(self, body):
        Path(paths.spec_file("demo")).write_text(body, encoding="utf-8")

    def _plan(self, fingerprint_ok=True):
        # Stamp the spec fingerprint so a fresh plan reads non-stale.
        text = "# Plan\n"
        if fingerprint_ok:
            fp = gates.spec_fingerprint("demo")
            text += "\n<!-- {} {} -->\n".format(gates.FINGERPRINT_MARKER, fp)
        Path(paths.plan_file("demo")).write_text(text, encoding="utf-8")

    def test_no_spec_next_is_spec(self):
        st = ps.compute_status("demo", gates, paths)
        self.assertEqual(st["next"], "/sdd:spec")
        self.assertFalse(st["spec_exists"])

    def test_open_oqs_next_is_spec_resolve(self):
        self._spec(SPEC_OPEN_OQ)
        st = ps.compute_status("demo", gates, paths)
        self.assertEqual(st["next"], "/sdd:spec")
        self.assertIn("resolve 1 open question", st["hint"])
        self.assertEqual(st["open"], 1)
        self.assertEqual(st["resolved"], 1)

    def test_spec_ok_no_plan_next_is_plan(self):
        self._spec(SPEC_RESOLVED)
        st = ps.compute_status("demo", gates, paths)
        self.assertEqual(st["next"], "/sdd:plan")
        self.assertFalse(st["plan_exists"])

    def test_fresh_plan_next_is_implement(self):
        self._spec(SPEC_RESOLVED)
        self._plan(fingerprint_ok=True)
        st = ps.compute_status("demo", gates, paths)
        self.assertEqual(st["next"], "/sdd:implement")
        self.assertFalse(st["stale"])

    def test_stale_plan_next_is_plan(self):
        self._spec(SPEC_RESOLVED)
        self._plan(fingerprint_ok=True)
        # Mutate the spec so the recorded fingerprint no longer matches.
        self._spec(SPEC_RESOLVED + "\n## Behavior\nchanged\n")
        st = ps.compute_status("demo", gates, paths)
        self.assertEqual(st["next"], "/sdd:plan")
        self.assertTrue(st["stale"])

    def test_render_contains_branch_slug_and_next(self):
        self._spec(SPEC_RESOLVED)
        st = ps.compute_status("demo", gates, paths)
        out = ps.render("feature/demo", "demo", st)
        self.assertIn("feature/demo", out)
        self.assertIn("slug: demo", out)
        self.assertIn("/sdd:state", out)


class TestSilentOutsidePipeline(unittest.TestCase):
    def test_no_specwork_prints_nothing(self):
        tmp = Path(tempfile.mkdtemp())
        payload = json.dumps({"source": "startup", "cwd": str(tmp)})
        proc = subprocess.run(
            ["python3", _HOOK_PATH], input=payload, capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
