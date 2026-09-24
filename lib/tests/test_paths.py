import os
import sys
import unittest

LIB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, LIB_DIR)

import paths  # noqa: E402


class TestPaths(unittest.TestCase):
    def test_default_spec_dir_layout(self):
        self.assertEqual(paths.state_file("demo"), ".specwork/_state/demo-state.json")
        self.assertEqual(paths.rules_file("demo"), ".specwork/_state/demo-rules.json")
        self.assertEqual(
            paths.cache_file("demo"), ".specwork/_state/demo-implementation-cache.json"
        )
        self.assertEqual(paths.path_file("demo"), ".specwork/_state/demo-path.json")
        self.assertEqual(paths.spec_file("demo"), ".specwork/_spec/demo-spec.md")
        self.assertEqual(paths.source_file("demo"), ".specwork/_spec/demo-source.md")
        self.assertEqual(paths.plan_file("demo"), ".specwork/_plan/demo-plan.md")
        self.assertEqual(paths.context_file("demo"), ".specwork/_progress/demo-context.md")
        self.assertEqual(
            paths.validated_file("demo"), ".specwork/_state/demo-validated.json"
        )

    def test_validated_file_not_in_all_paths(self):
        # validated_file is created at push time, not by /sdd:start, so it must
        # stay out of the start-time all_paths map (and state.json schema).
        self.assertNotIn("validated_file", paths.all_paths("demo"))

    def test_custom_spec_dir(self):
        self.assertEqual(paths.state_file("x", "work"), "work/_state/x-state.json")

    def test_posix_separators(self):
        # Always forward slashes, even though tests may run on any OS.
        self.assertNotIn("\\", paths.spec_file("demo"))

    def test_all_paths_keys_and_values(self):
        ap = paths.all_paths("demo")
        self.assertEqual(
            set(ap),
            {
                "state_file",
                "rules_file",
                "cache_file",
                "path_file",
                "spec_file",
                "source_file",
                "plan_file",
                "context_file",
            },
        )
        self.assertEqual(ap["rules_file"], paths.rules_file("demo"))


if __name__ == "__main__":
    unittest.main()
