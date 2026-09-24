import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Put lib/ on the path so plan's `from gates import ...` resolves.
LIB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, LIB_DIR)

# plan.py can't be imported by name (hyphen in filename).
_mod_spec = importlib.util.spec_from_file_location("plan", Path(LIB_DIR) / "plan.py")
_plan = importlib.util.module_from_spec(_mod_spec)
_mod_spec.loader.exec_module(_plan)


class TestFindHttpStatusInSpec(unittest.TestCase):
    def test_extracts_status_codes(self):
        text = "Return 404 if not found, 403 if forbidden"
        self.assertEqual(sorted(_plan.find_http_status_in_spec(text)), ["403", "404"])

    def test_empty_when_none(self):
        self.assertEqual(_plan.find_http_status_in_spec("no status codes here"), [])


class TestReferenceGrep(unittest.TestCase):
    def test_empty_without_trigger_language(self):
        # Symbols present, but no rename/remove/replace language → no tagging.
        text = "Add a field to `OrderService` and call `/api/v1/orders`."
        self.assertEqual(_plan.reference_grep(text), [])

    def test_empty_with_no_identifiers(self):
        self.assertEqual(_plan.reference_grep("rename things but name nothing concrete"), [])

    def test_finds_real_reference_on_rename(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src" / "main"
            src.mkdir(parents=True)
            (src / "Caller.java").write_text("class Caller { OrderService svc; }")
            cwd = os.getcwd()
            os.chdir(d)
            try:
                refs = _plan.reference_grep("Rename `OrderService` to `NewOrderService`.")
            finally:
                os.chdir(cwd)
            self.assertTrue(any("Caller.java" in r for r in refs))

    def test_skips_symbols_in_safe_constraints_section(self):
        # `@Size` lives under "## Safe Constraints" → must not seed a candidate,
        # even though the line above mentions "remove".
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src" / "main"
            src.mkdir(parents=True)
            (src / "Dto.java").write_text("class Dto { @Size String phoneNumber; }")
            text = (
                "## Behavior\nRemove the duplicate `@AssertTrue` validator.\n\n"
                "## Safe Constraints\nDo not touch the `@Size` constraint on `phoneNumber`.\n"
            )
            cwd = os.getcwd()
            os.chdir(d)
            try:
                refs = _plan.reference_grep(text)
            finally:
                os.chdir(cwd)
            # The only trigger line is inside Safe Constraints / negated → no refs.
            self.assertEqual(refs, [])

    def test_skips_negated_remove_line(self):
        # A negated removal line must not extract its symbol.
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src" / "main"
            src.mkdir(parents=True)
            (src / "Dto.java").write_text("class Dto { @Size String phoneNumber; }")
            text = "## Behavior\nDo NOT remove the `@Size` constraint on `phoneNumber`.\n"
            cwd = os.getcwd()
            os.chdir(d)
            try:
                refs = _plan.reference_grep(text)
            finally:
                os.chdir(cwd)
            self.assertEqual(refs, [])

    def test_hit_cap_skips_generic_symbol(self):
        # `phoneNumber` matches many files (generic) and is dropped; a legit
        # single-file removal of `OrderService` still produces its ref.
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src" / "main"
            src.mkdir(parents=True)
            for i in range(5):
                (src / f"Gen{i}.java").write_text("class Gen { String phoneNumber; }")
            (src / "Caller.java").write_text("class Caller { OrderService svc; String phoneNumber; }")
            text = "Rename `OrderService` to `NewOrderService` and remove `phoneNumber`."
            cwd = os.getcwd()
            os.chdir(d)
            os.environ["CLAUDE_TOOLS_REF_HIT_CAP"] = "3"
            try:
                refs = _plan.reference_grep(text)
            finally:
                os.environ.pop("CLAUDE_TOOLS_REF_HIT_CAP", None)
                os.chdir(cwd)
            # OrderService → 1 file (under cap) kept; phoneNumber → 6 files (over
            # cap) dropped, so Gen*.java never appear.
            self.assertTrue(any("Caller.java" in r for r in refs))
            self.assertFalse(any("Gen" in r for r in refs))


class TestFindMockConsumerTests(unittest.TestCase):
    def test_non_java_stack_returns_empty(self):
        self.assertEqual(_plan.find_mock_consumer_tests("node", [{"path": "src/App.ts"}]), [])

    def test_returns_real_test_paths(self):
        with tempfile.TemporaryDirectory() as d:
            test_dir = Path(d) / "src" / "test"
            test_dir.mkdir(parents=True)
            (test_dir / "OrderServiceTest.java").write_text(
                "class OrderServiceTest { OrderService mock; }")
            cwd = os.getcwd()
            os.chdir(d)
            try:
                tests = _plan.find_mock_consumer_tests(
                    "java", [{"path": "src/main/OrderService.java"}])
            finally:
                os.chdir(cwd)
            self.assertTrue(tests)
            # Real paths only — no placeholder ellipsis.
            self.assertTrue(all("/..." not in t for t in tests))
            self.assertTrue(any("OrderServiceTest.java" in t for t in tests))


class TestGetExistingTests(unittest.TestCase):
    def test_no_tests_when_files_dont_exist(self):
        self.assertEqual(_plan.get_existing_tests("src/main/OrderService.java", "java"), [])

    def test_empty_for_unknown_stack(self):
        self.assertEqual(_plan.get_existing_tests("src/App.ts", "unknown"), [])

    def test_empty_for_node_when_no_test_extension(self):
        # Non-source extension on node stack → skip
        self.assertEqual(_plan.get_existing_tests("README.md", "node"), [])

    def test_finds_node_sibling_tests(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "src").mkdir()
            (root / "src" / "App.ts").write_text("export const x = 1")
            (root / "src" / "App.test.ts").write_text("test('x', () => {})")
            (root / "src" / "App.spec.ts").write_text("describe('x', () => {})")
            old = os.getcwd()
            os.chdir(d)
            try:
                tests = _plan.get_existing_tests("src/App.ts", "node")
            finally:
                os.chdir(old)
            self.assertEqual(len(tests), 2)
            self.assertTrue(any("App.test.ts" in t for t in tests))
            self.assertTrue(any("App.spec.ts" in t for t in tests))

    def test_finds_node_tests_in_tests_dir(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "src").mkdir()
            (root / "src" / "App.tsx").write_text("export const x = 1")
            (root / "src" / "__tests__").mkdir()
            (root / "src" / "__tests__" / "App.test.tsx").write_text("test('x', () => {})")
            old = os.getcwd()
            os.chdir(d)
            try:
                tests = _plan.get_existing_tests("src/App.tsx", "node")
            finally:
                os.chdir(old)
            self.assertEqual(len(tests), 1)
            self.assertIn("__tests__", tests[0])


if __name__ == "__main__":
    unittest.main()
