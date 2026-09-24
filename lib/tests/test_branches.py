import os
import sys
import unittest

LIB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, LIB_DIR)

import branches  # noqa: E402


class TestBranches(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(branches.classify_branch("feature/IR-70"), "feature")
        self.assertEqual(branches.classify_branch("hotfix/x"), "hotfix")
        self.assertEqual(branches.classify_branch("main"), "main")
        self.assertEqual(branches.classify_branch("master"), "main")
        self.assertEqual(branches.classify_branch("development"), "develop")
        self.assertEqual(branches.classify_branch("random-thing"), "other")

    def test_is_feature_branch(self):
        self.assertTrue(branches.is_feature_branch("feature/x"))
        self.assertTrue(branches.is_feature_branch("bugfix/x"))
        self.assertFalse(branches.is_feature_branch("main"))

    def test_requires_clean_tree(self):
        for b in ("main", "master", "develop", "development"):
            self.assertTrue(branches.requires_clean_tree(b))
        self.assertFalse(branches.requires_clean_tree("feature/x"))

    def test_detect_base_branch(self):
        self.assertEqual(branches.detect_base_branch("feature/x", "develop"), "develop")
        self.assertEqual(branches.detect_base_branch("feature/x", ""), "development")
        self.assertEqual(branches.detect_base_branch("feature/x", "", "main"), "main")


if __name__ == "__main__":
    unittest.main()
