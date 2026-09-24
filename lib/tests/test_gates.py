import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gates import (
    audit_artifacts,
    base_branch,
    behavioral_change_signals,
    branch_merge_status,
    check_open_questions,
    check_plan_staleness,
    check_required_artifacts,
    count_open_questions,
    detect_stack,
    format_staleness_error,
    get_resolved_oqs,
    merge_cache,
    non_interactive_mode,
    pipeline_branch_status,
    pipeline_inventory,
    plan_required,
    read_plan_fingerprint,
    record_plan_fingerprint,
    require_specwork,
    resolve_slug,
    resolve_slug_for_branch,
    risk_signals,
    section_text,
    spec_consistency,
    spec_fingerprint,
    unresolved_oqs,
    worktree_freshness,
)


class TmpDirCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)


class TestSectionText(unittest.TestCase):
    def test_returns_section_body(self):
        text = "## Open Questions\n- [ ] #1 test\n\n## Behavior\ncode"
        self.assertEqual(section_text(text, "Open Questions"), "- [ ] #1 test")

    def test_returns_empty_when_missing(self):
        self.assertEqual(section_text("no heading here", "Open Questions"), "")


class TestUnresolvedOqs(unittest.TestCase):
    def test_finds_unresolved(self):
        text = "## Open Questions\n- [ ] #1 unresolved\n- [x] #2 resolved\n"
        self.assertEqual(unresolved_oqs(text), ["- [ ] #1 unresolved"])

    def test_empty_when_none(self):
        self.assertEqual(unresolved_oqs("## Open Questions\n- [x] #1 resolved\n"), [])


class TestCheckRequiredArtifacts(TmpDirCase):
    def test_returns_missing_when_none_exist(self):
        missing = check_required_artifacts("test-slug", spec_dir=str(self.tmp))
        self.assertEqual(len(missing), 3)
        self.assertTrue(all("test-slug" in m for m in missing))

    def test_returns_empty_when_all_exist(self):
        (self.tmp / "_state").mkdir(parents=True)
        (self.tmp / "_spec").mkdir(parents=True)
        (self.tmp / "_state" / "test-slug-state.json").write_text("{}")
        (self.tmp / "_state" / "test-slug-rules.json").write_text("{}")
        (self.tmp / "_spec" / "test-slug-spec.md").write_text("# spec")
        self.assertEqual(check_required_artifacts("test-slug", spec_dir=str(self.tmp)), [])


class TestCheckOpenQuestions(TmpDirCase):
    def _write_spec(self, body):
        (self.tmp / "_spec").mkdir(parents=True, exist_ok=True)
        (self.tmp / "_spec" / "s-spec.md").write_text(body)

    def test_blocks_on_unresolved(self):
        self._write_spec("## Open Questions\n- [ ] #1 unresolved\n")
        blockers = check_open_questions("s", spec_dir=str(self.tmp))
        self.assertEqual(len(blockers), 1)

    def test_clean_when_all_resolved(self):
        self._write_spec("## Open Questions\n- [x] #1 done\n")
        self.assertEqual(check_open_questions("s", spec_dir=str(self.tmp)), [])


class TestRiskSignals(unittest.TestCase):
    def test_detects_db_migration(self):
        self.assertIn("db-migration", risk_signals("migration required: alter table consent"))

    def test_detects_auth_security(self):
        self.assertIn("auth-security", risk_signals("needs jwt token validation in SecurityConfig"))

    def test_empty_with_no_risk(self):
        self.assertEqual(risk_signals("simple bugfix, no risky keywords"), {})

    def test_frontend_accessibility(self):
        self.assertIn("accessibility", risk_signals(
            "add aria-label and keyboard navigation for screen readers"))

    def test_frontend_state_management(self):
        self.assertIn("state-management", risk_signals(
            "migrate from Redux to Zustand for the cart store"))

    def test_frontend_routing(self):
        self.assertIn("routing", risk_signals(
            "restructure navigation with react-router nested routes"))

    def test_frontend_data_fetching(self):
        self.assertIn("data-fetching", risk_signals(
            "replace manual fetches with react-query useQuery hooks"))

    def test_frontend_component_api(self):
        self.assertIn("component-api", risk_signals(
            "breaking change in component: rename prop onClose to onDismiss"))

    def test_frontend_ui_migration(self):
        self.assertIn("ui-migration", risk_signals(
            "design system update: migrate from Bootstrap to Tailwind"))

    def test_plain_backend_spec_has_no_frontend_signals(self):
        hits = risk_signals("add a repository method to fetch orders by status")
        for fe in ("component-api", "state-management", "accessibility",
                   "routing", "data-fetching", "ui-migration"):
            self.assertNotIn(fe, hits)


class TestSpecConsistency(unittest.TestCase):
    def test_idempotent_and_side_effect(self):
        text = "## Behavior\nThe endpoint must be idempotent.\n\nLog on each invocation.\n"
        self.assertIn("idempotent + per-call side effect", spec_consistency(text))

    def test_resolver_suppresses_cache_pair(self):
        # "cache + always fresh" has an invalidation resolver; mentioning TTL clears it.
        text = (
            "We add a cache for lookups.\n\n"
            "Reads must return always fresh data.\n\n"
            "A TTL of 30s bounds staleness.\n"
        )
        self.assertEqual(spec_consistency(text), [])

    def test_cache_pair_flagged_without_invalidation(self):
        text = "We add a cache for lookups.\n\nReads must return always fresh data.\n"
        self.assertIn("cache + always fresh", spec_consistency(text))

    def test_same_paragraph_not_flagged(self):
        # Both signals in one paragraph are assumed reconciled inline.
        text = "The endpoint is idempotent and we log on each invocation in the same breath.\n"
        self.assertEqual(spec_consistency(text), [])


class TestDetectStack(TmpDirCase):
    def test_java_gradle(self):
        (self.tmp / "build.gradle").write_text("")
        self.assertEqual(detect_stack(str(self.tmp)), "java")

    def test_node(self):
        (self.tmp / "package.json").write_text("{}")
        self.assertEqual(detect_stack(str(self.tmp)), "node")

    def test_frontend_via_config_file(self):
        (self.tmp / "package.json").write_text("{}")
        (self.tmp / "vite.config.ts").write_text("")
        self.assertEqual(detect_stack(str(self.tmp)), "frontend")

    def test_frontend_via_dependency(self):
        (self.tmp / "package.json").write_text(
            json.dumps({"dependencies": {"react": "^18.0.0"}}))
        self.assertEqual(detect_stack(str(self.tmp)), "frontend")

    def test_backend_node_stays_node(self):
        (self.tmp / "package.json").write_text(
            json.dumps({"dependencies": {"express": "^4.0.0"}}))
        self.assertEqual(detect_stack(str(self.tmp)), "node")

    def test_polyglot_prefers_java(self):
        (self.tmp / "build.gradle").write_text("")
        (self.tmp / "package.json").write_text(
            json.dumps({"dependencies": {"react": "^18.0.0"}}))
        self.assertEqual(detect_stack(str(self.tmp)), "java")

    def test_unknown(self):
        self.assertEqual(detect_stack(str(self.tmp)), "unknown")


class TestDetectStackCLI(TmpDirCase):
    """The `detect-stack` subcommand is what /sdd:spec shells out to for template
    selection; it takes no slug, so it must be handled before the slug guard."""

    def _run(self):
        import subprocess
        gates_py = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "gates.py"
        return subprocess.run(
            [sys.executable, str(gates_py), "detect-stack"],
            cwd=str(self.tmp), capture_output=True, text=True,
        )

    def test_cli_frontend(self):
        (self.tmp / "package.json").write_text("{}")
        (self.tmp / "vite.config.ts").write_text("")
        r = self._run()
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "frontend")

    def test_cli_unknown(self):
        r = self._run()
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "unknown")


class TestMergeCache(TmpDirCase):
    def _cache_path(self, slug="test-slug"):
        (self.tmp / "_state").mkdir(parents=True, exist_ok=True)
        return self.tmp / "_state" / f"{slug}-implementation-cache.json"

    def test_append_only(self):
        cache_file = self._cache_path()
        cache_file.write_text(json.dumps(
            {"repositories": ["ExistingRepo"], "schema_version": 1, "id": "test-slug"}))
        merge_cache("test-slug", {"repositories": ["NewRepo"]}, spec_dir=str(self.tmp))
        cached = json.loads(cache_file.read_text())
        self.assertIn("ExistingRepo", cached["repositories"])
        self.assertIn("NewRepo", cached["repositories"])

    def test_deduplicates(self):
        cache_file = self._cache_path()
        cache_file.write_text(json.dumps(
            {"repositories": ["Repo"], "schema_version": 1, "id": "test-slug"}))
        merge_cache("test-slug", {"repositories": ["Repo", "Repo"]}, spec_dir=str(self.tmp))
        self.assertEqual(json.loads(cache_file.read_text())["repositories"], ["Repo"])

    def test_creates_when_absent(self):
        self.tmp.joinpath("_state").mkdir(parents=True, exist_ok=True)
        merge_cache("fresh", {"patterns": ["uses fallback lookup"]}, spec_dir=str(self.tmp))
        cache_file = self.tmp / "_state" / "fresh-implementation-cache.json"
        self.assertTrue(cache_file.exists())
        self.assertEqual(json.loads(cache_file.read_text())["patterns"], ["uses fallback lookup"])


class TestBehavioralChangeSignals(unittest.TestCase):
    def test_detects_idempotent(self):
        self.assertIn("idempotent", behavioral_change_signals("must be idempotent"))

    def test_detects_no_longer(self):
        self.assertIn("no longer", behavioral_change_signals("no longer needed"))

    def test_empty_with_no_signals(self):
        self.assertEqual(behavioral_change_signals("add new endpoint"), [])

    def test_picks_up_plan_tags(self):
        signals = behavioral_change_signals("add new endpoint", "| `Foo.java` | [infra] |")
        self.assertIn("plan contains [infra] tag", signals)


class TestWorktreeFreshness(TmpDirCase):
    def _plan(self, rows):
        plan = self.tmp / "plan.md"
        plan.write_text("## Target Files\n\n| File | Change |\n|---|---|\n" + rows + "\n")
        return str(plan)

    def test_empty_when_no_plan(self):
        self.assertEqual(worktree_freshness("/nonexistent/path"), [])

    def test_flags_new_but_existing(self):
        existing = self.tmp / "Already.java"
        existing.write_text("x")
        plan = self._plan(f"| `{existing}` | create new file |")
        disc = worktree_freshness(plan)
        self.assertTrue(any("marked new but already exists" in d for d in disc))

    def test_flags_expected_but_missing(self):
        plan = self._plan(f"| `{self.tmp}/Missing.java` | update method |")
        disc = worktree_freshness(plan)
        self.assertTrue(any("expected but not found" in d for d in disc))

    def test_skips_unverified(self):
        plan = self._plan(f"| `{self.tmp}/Ghost.java` | [UNVERIFIED] candidate |")
        self.assertEqual(worktree_freshness(plan), [])


class TestCheckPlanStaleness(TmpDirCase):
    def _make(self, slug, spec_mtime, plan_mtime):
        sw = self.tmp / ".specwork"
        (sw / "_spec").mkdir(parents=True)
        (sw / "_plan").mkdir(parents=True)
        spec = sw / "_spec" / f"{slug}-spec.md"
        spec.write_text("# spec", encoding="utf-8")
        os.utime(spec, (spec_mtime, spec_mtime))
        plan = sw / "_plan" / f"{slug}-plan.md"
        plan.write_text("# plan", encoding="utf-8")
        os.utime(plan, (plan_mtime, plan_mtime))
        return str(sw)

    def test_none_when_no_plan(self):
        self.assertIsNone(check_plan_staleness("no-plan-slug", spec_dir=str(self.tmp)))

    def test_fresh_when_plan_newer_than_spec(self):
        sw = self._make("s", spec_mtime=1000, plan_mtime=1200)
        result = check_plan_staleness("s", spec_dir=sw)
        self.assertEqual(result, {"stale": False})

    def test_stale_when_plan_older_than_spec(self):
        sw = self._make("s", spec_mtime=2000, plan_mtime=1000)
        result = check_plan_staleness("s", spec_dir=sw)
        self.assertTrue(result["stale"])
        self.assertEqual(result["spec_mtime"], 2000)
        self.assertEqual(result["plan_mtime"], 1000)


class TestPlanFingerprint(TmpDirCase):
    def _make(self, spec_body="# spec\n\nbody", plan_body="# plan"):
        sw = self.tmp / ".specwork"
        (sw / "_spec").mkdir(parents=True)
        (sw / "_plan").mkdir(parents=True)
        (sw / "_spec" / "s-spec.md").write_text(spec_body, encoding="utf-8")
        (sw / "_plan" / "s-plan.md").write_text(plan_body, encoding="utf-8")
        return str(sw)

    def _spec(self):
        return self.tmp / ".specwork" / "_spec" / "s-spec.md"

    def _plan(self):
        return self.tmp / ".specwork" / "_plan" / "s-plan.md"

    def test_record_and_read_roundtrip(self):
        sw = self._make()
        self.assertTrue(record_plan_fingerprint("s", spec_dir=sw))
        self.assertEqual(read_plan_fingerprint(self._plan()), spec_fingerprint("s", spec_dir=sw))

    def test_fingerprint_beats_mtime_when_spec_newer(self):
        # The pause/resume hole: spec mtime ends up newer than plan after a
        # git stash round-trip, but the content is unchanged → must stay fresh.
        sw = self._make()
        record_plan_fingerprint("s", spec_dir=sw)
        os.utime(self._plan(), (1000, 1000))
        os.utime(self._spec(), (2000, 2000))
        self.assertEqual(check_plan_staleness("s", spec_dir=sw), {"stale": False})

    def test_stale_when_spec_content_changed(self):
        # Plan mtime newer than spec (mtime gate would say "fresh") but the spec
        # body actually changed → fingerprint catches it.
        sw = self._make()
        record_plan_fingerprint("s", spec_dir=sw)
        self._spec().write_text("# spec\n\nDIFFERENT body", encoding="utf-8")
        os.utime(self._plan(), (3000, 3000))
        os.utime(self._spec(), (1000, 1000))
        result = check_plan_staleness("s", spec_dir=sw)
        self.assertTrue(result["stale"])
        self.assertEqual(result["reason"], "fingerprint")

    def test_touch_or_whitespace_does_not_make_stale(self):
        sw = self._make(spec_body="# spec\n\nbody")
        record_plan_fingerprint("s", spec_dir=sw)
        self._spec().write_text("# spec\n\nbody   \n", encoding="utf-8")
        self.assertEqual(check_plan_staleness("s", spec_dir=sw), {"stale": False})

    def test_record_idempotent_single_marker(self):
        sw = self._make()
        record_plan_fingerprint("s", spec_dir=sw)
        record_plan_fingerprint("s", spec_dir=sw)
        self.assertEqual(self._plan().read_text(encoding="utf-8").count("spec-fingerprint:"), 1)

    def test_record_false_when_no_plan(self):
        sw = self.tmp / ".specwork"
        (sw / "_spec").mkdir(parents=True)
        (sw / "_spec" / "s-spec.md").write_text("# spec", encoding="utf-8")
        self.assertFalse(record_plan_fingerprint("s", spec_dir=str(sw)))


class TestRequireSpecwork(TmpDirCase):
    def _sw(self):
        return str(self.tmp / ".specwork")

    def test_rejects_when_dir_absent(self):
        self.assertIsNotNone(require_specwork(self._sw()))

    def test_rejects_when_uninitialized(self):
        (self.tmp / ".specwork" / "_state").mkdir(parents=True)
        self.assertIsNotNone(require_specwork(self._sw()))

    def test_passes_when_initialized(self):
        state_dir = self.tmp / ".specwork" / "_state"
        state_dir.mkdir(parents=True)
        (state_dir / "x-state.json").write_text("{}", encoding="utf-8")
        self.assertIsNone(require_specwork(self._sw()))


class TestNonInteractiveMode(TmpDirCase):
    def _write_state(self, slug, payload):
        state_dir = self.tmp / ".specwork" / "_state"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / f"{slug}-state.json").write_text(json.dumps(payload), encoding="utf-8")

    def test_false_when_missing(self):
        self.assertFalse(non_interactive_mode("demo", spec_dir=str(self.tmp / ".specwork")))

    def test_reads_true_from_state(self):
        self._write_state("demo", {"id": "demo", "non_interactive": True})
        self.assertTrue(non_interactive_mode("demo", spec_dir=str(self.tmp / ".specwork")))

    def test_reads_false_from_state(self):
        self._write_state("demo", {"id": "demo", "non_interactive": False})
        self.assertFalse(non_interactive_mode("demo", spec_dir=str(self.tmp / ".specwork")))


class TestBaseBranch(TmpDirCase):
    def _write_state(self, slug, payload):
        state_dir = self.tmp / ".specwork" / "_state"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / f"{slug}-state.json").write_text(json.dumps(payload), encoding="utf-8")

    def test_empty_when_missing(self):
        self.assertEqual(base_branch("demo", spec_dir=str(self.tmp / ".specwork")), "")

    def test_reads_base_branch_from_state(self):
        self._write_state("demo", {"id": "demo", "base_branch": "main"})
        self.assertEqual(base_branch("demo", spec_dir=str(self.tmp / ".specwork")), "main")

    def test_empty_when_base_branch_null(self):
        self._write_state("demo", {"id": "demo", "base_branch": None})
        self.assertEqual(base_branch("demo", spec_dir=str(self.tmp / ".specwork")), "")


class TestResolveSlug(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.state = self.tmp / ".specwork" / "_state"
        self.state.mkdir(parents=True)

    def _spec_dir(self):
        return str(self.tmp / ".specwork")

    def _write(self, slug, branch):
        (self.state / f"{slug}-state.json").write_text(
            json.dumps({"id": slug, "branch": branch}), encoding="utf-8"
        )

    def test_empty_when_no_state(self):
        self.assertEqual(resolve_slug(spec_dir=self._spec_dir()), "")

    def test_single_state_file(self):
        self._write("demo", "feature/demo")
        self.assertEqual(resolve_slug(spec_dir=self._spec_dir()), "demo")

    def test_branch_match_among_many(self):
        self._write("alpha", "feature/alpha")
        self._write("bravo", "feature/bravo")
        self.assertEqual(
            resolve_slug(branch="feature/bravo", spec_dir=self._spec_dir()), "bravo"
        )

    def test_falls_back_to_first_when_no_branch_match(self):
        self._write("alpha", "feature/alpha")
        self._write("bravo", "feature/bravo")
        # sorted() → "alpha" is first
        self.assertEqual(
            resolve_slug(branch="feature/nope", spec_dir=self._spec_dir()), "alpha"
        )


class TestResolveSlugForBranch(unittest.TestCase):
    # Regression coverage for the push-gate/coverage-gate false-block bug:
    # .specwork/ is gitignored and survives `git checkout`, so it commonly
    # still holds a *different* branch's leftover pipeline state.
    # resolve_slug_for_branch() must never adopt that unrelated state — unlike
    # resolve_slug(), which intentionally falls back to "the first file found"
    # for skills resuming the current pipeline.
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.state = self.tmp / ".specwork" / "_state"
        self.state.mkdir(parents=True)

    def _spec_dir(self):
        return str(self.tmp / ".specwork")

    def _write(self, slug, branch):
        (self.state / f"{slug}-state.json").write_text(
            json.dumps({"id": slug, "branch": branch}), encoding="utf-8"
        )

    def test_empty_when_no_branch_given(self):
        self._write("alpha", "feature/alpha")
        self.assertEqual(resolve_slug_for_branch("", spec_dir=self._spec_dir()), "")

    def test_empty_when_no_state_dir(self):
        self.assertEqual(
            resolve_slug_for_branch("feature/anything", spec_dir=self._spec_dir()), ""
        )

    def test_exact_match_returned(self):
        self._write("alpha", "feature/alpha")
        self._write("bravo", "feature/bravo")
        self.assertEqual(
            resolve_slug_for_branch("feature/bravo", spec_dir=self._spec_dir()), "bravo"
        )

    def test_no_fallback_when_no_match(self):
        # This is the exact scenario that broke push-gate/coverage-gate: only
        # an unrelated branch's state file exists. resolve_slug() would
        # return "alpha" here (wrong); resolve_slug_for_branch() must not.
        self._write("alpha", "feature/alpha")
        self.assertEqual(
            resolve_slug_for_branch("feature/mybranch", spec_dir=self._spec_dir()), ""
        )

    def test_finds_match_regardless_of_glob_order(self):
        # The matching file is NOT alphabetically first — resolve_slug_for_branch
        # must check every file, not stop at the first one found.
        self._write("z-later", "feature/mybranch")
        self._write("a-earlier", "feature/other-ticket")
        self.assertEqual(
            resolve_slug_for_branch("feature/mybranch", spec_dir=self._spec_dir()),
            "z-later",
        )


class TestPipelineBranchStatus(unittest.TestCase):
    # /sdd:pause and /sdd:close used to decide "is this my pipeline?" via
    # prose alone (no gates.py call backing it), which could stash/delete a
    # *different* branch's pipeline under the current branch's label.
    # pipeline_branch_status() gives both skills one deterministic answer.
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.state = self.tmp / ".specwork" / "_state"
        self.state.mkdir(parents=True)

    def _spec_dir(self):
        return str(self.tmp / ".specwork")

    def _write(self, slug, branch, base_branch=None):
        payload = {"id": slug, "branch": branch}
        if base_branch is not None:
            payload["base_branch"] = base_branch
        (self.state / f"{slug}-state.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    def test_no_pipeline_at_all(self):
        status = pipeline_branch_status("feature/anything", spec_dir=self._spec_dir())
        self.assertEqual(
            status,
            {
                "current_branch": "feature/anything",
                "has_any_pipeline": False,
                "owns_pipeline": False,
                "slug": "",
                "recorded_branch": "",
                "recorded_base_branch": "",
                "is_base_branch": False,
            },
        )

    def test_owns_pipeline_when_branch_matches(self):
        self._write("zzz", "feature/ZZZ", base_branch="development")
        status = pipeline_branch_status("feature/ZZZ", spec_dir=self._spec_dir())
        self.assertTrue(status["owns_pipeline"])
        self.assertEqual(status["slug"], "zzz")
        self.assertEqual(status["recorded_branch"], "feature/ZZZ")
        self.assertEqual(status["recorded_base_branch"], "development")
        self.assertFalse(status["is_base_branch"])

    def test_is_base_branch_when_on_the_recorded_base(self):
        # The "MR merged, back on development, now cleaning up" case that
        # /sdd:close's "safe to run from any branch" is meant to cover.
        self._write("zzz", "feature/ZZZ", base_branch="development")
        status = pipeline_branch_status("development", spec_dir=self._spec_dir())
        self.assertFalse(status["owns_pipeline"])
        self.assertTrue(status["is_base_branch"])
        self.assertEqual(status["slug"], "zzz")
        self.assertEqual(status["recorded_branch"], "feature/ZZZ")

    def test_unrelated_third_branch_is_neither(self):
        # The genuinely dangerous case: a brand-new branch for unrelated work,
        # with only another branch's leftover pipeline on disk. Neither
        # owns_pipeline nor is_base_branch should be true — callers must
        # treat this as "not safe to act here", not silently proceed.
        self._write("zzz", "feature/ZZZ", base_branch="development")
        status = pipeline_branch_status("feature/mybranch", spec_dir=self._spec_dir())
        self.assertFalse(status["owns_pipeline"])
        self.assertFalse(status["is_base_branch"])
        self.assertEqual(status["slug"], "zzz")
        self.assertEqual(status["recorded_branch"], "feature/ZZZ")

    def test_missing_base_branch_defaults_to_empty(self):
        self._write("zzz", "feature/ZZZ")  # no base_branch key at all
        status = pipeline_branch_status("feature/mybranch", spec_dir=self._spec_dir())
        self.assertEqual(status["recorded_base_branch"], "")
        self.assertFalse(status["is_base_branch"])


def fake_git(*, repo=True, branches=(), merged=()):
    """Build a stub git runner for branch_merge_status / pipeline_inventory.

    ``repo=False`` simulates "not a git repo"; ``repo=None`` simulates git being
    absent entirely (rc None). ``branches`` are the refs that resolve;
    ``merged`` are the branches that are ancestors of their base.
    """
    def run(args):
        if args[:2] == ["rev-parse", "--git-dir"]:
            return (None, "") if repo is None else (0 if repo else 128, "")
        if args[:1] == ["rev-parse"]:
            ref = args[-1].replace("refs/heads/", "").replace("^{commit}", "")
            return (0 if ref in branches else 1), ""
        if args[:2] == ["merge-base", "--is-ancestor"]:
            return (0 if args[2] in merged else 1), ""
        return 1, ""
    return run


class TestBranchMergeStatus(unittest.TestCase):
    # Offline, git-only "has this pipeline's work already landed?" — the signal
    # /sdd:start uses to say "close it" instead of "continue it".
    def test_branch_gone_when_ref_missing(self):
        git = fake_git(branches=["development"])
        self.assertEqual(branch_merge_status("feature/ZZZ", "development", git), "branch-gone")

    def test_merged_when_ancestor_of_base(self):
        git = fake_git(branches=["feature/ZZZ", "development"], merged=["feature/ZZZ"])
        self.assertEqual(branch_merge_status("feature/ZZZ", "development", git), "merged")

    def test_open_when_not_ancestor(self):
        git = fake_git(branches=["feature/ZZZ", "development"])
        self.assertEqual(branch_merge_status("feature/ZZZ", "development", git), "open")

    def test_falls_back_to_origin_base(self):
        # Base branch not checked out locally — common on a fresh clone.
        git = fake_git(branches=["feature/ZZZ", "origin/development"], merged=["feature/ZZZ"])
        self.assertEqual(branch_merge_status("feature/ZZZ", "development", git), "merged")

    def test_unknown_when_base_unresolvable(self):
        # Neither `development` nor `origin/development` exists — we cannot say
        # "open", which would read as a confident "still in flight".
        git = fake_git(branches=["feature/ZZZ"])
        self.assertEqual(branch_merge_status("feature/ZZZ", "development", git), "unknown")

    def test_unknown_when_no_base_recorded(self):
        git = fake_git(branches=["feature/ZZZ"])
        self.assertEqual(branch_merge_status("feature/ZZZ", "", git), "unknown")

    def test_unknown_outside_a_git_repo(self):
        # Without the repo probe every rc is nonzero and this would look like
        # "branch-gone" — i.e. a bogus "your work already merged, close it".
        git = fake_git(repo=False)
        self.assertEqual(branch_merge_status("feature/ZZZ", "development", git), "unknown")

    def test_unknown_when_git_unavailable(self):
        self.assertEqual(
            branch_merge_status("feature/ZZZ", "development", fake_git(repo=None)), "unknown"
        )

    def test_unknown_for_empty_branch(self):
        git = fake_git(branches=["development"])
        self.assertEqual(branch_merge_status("", "development", git), "unknown")


class TestPipelineInventory(unittest.TestCase):
    # .specwork/ is gitignored and outlives the branch it belongs to, so a
    # merged-but-never-closed pipeline made /sdd:start refuse new work and
    # point at /sdd:spec to "continue" something that already shipped.
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.state = self.tmp / ".specwork" / "_state"
        self.state.mkdir(parents=True)

    def _spec_dir(self):
        return str(self.tmp / ".specwork")

    def _write(self, slug, branch, base_branch="development"):
        (self.state / f"{slug}-state.json").write_text(
            json.dumps({"id": slug, "branch": branch, "base_branch": base_branch}),
            encoding="utf-8",
        )

    def test_no_pipelines_at_all(self):
        inv = pipeline_inventory("feature/new", spec_dir=self._spec_dir(), git=fake_git())
        self.assertEqual(inv["pipelines"], [])
        self.assertEqual(inv["orphans"], [])
        self.assertEqual(inv["closable"], [])

    def test_current_branch_pipeline_is_active_and_never_closable(self):
        # Even with a git stub that would report it merged, the branch's own
        # pipeline is never probed — "continue it" stays the right advice.
        self._write("zzz", "feature/ZZZ")
        git = fake_git(branches=["feature/ZZZ", "development"], merged=["feature/ZZZ"])
        inv = pipeline_inventory("feature/ZZZ", spec_dir=self._spec_dir(), git=git)
        entry = inv["pipelines"][0]
        self.assertTrue(entry["is_current"])
        self.assertEqual(entry["merge_status"], "active")
        self.assertFalse(entry["closable"])
        self.assertEqual(inv["orphans"], [])
        self.assertEqual(inv["closable"], [])

    def test_merged_orphan_is_closable(self):
        self._write("zzz", "feature/ZZZ")
        git = fake_git(branches=["feature/ZZZ", "development"], merged=["feature/ZZZ"])
        inv = pipeline_inventory("feature/other", spec_dir=self._spec_dir(), git=git)
        self.assertEqual([x["slug"] for x in inv["closable"]], ["zzz"])
        self.assertEqual(inv["closable"][0]["merge_status"], "merged")
        self.assertEqual(inv["closable"][0]["branch"], "feature/ZZZ")

    def test_deleted_branch_orphan_is_closable(self):
        self._write("zzz", "feature/ZZZ")
        git = fake_git(branches=["development"])
        inv = pipeline_inventory("feature/other", spec_dir=self._spec_dir(), git=git)
        self.assertEqual(inv["closable"][0]["merge_status"], "branch-gone")

    def test_open_orphan_is_not_closable(self):
        # Someone else's in-flight pipeline: still an orphan here, but telling
        # the user to /sdd:close it would destroy unmerged work.
        self._write("zzz", "feature/ZZZ")
        git = fake_git(branches=["feature/ZZZ", "development"])
        inv = pipeline_inventory("feature/other", spec_dir=self._spec_dir(), git=git)
        self.assertEqual([x["slug"] for x in inv["orphans"]], ["zzz"])
        self.assertEqual(inv["closable"], [])

    def test_unknown_orphan_is_not_closable(self):
        self._write("zzz", "feature/ZZZ")
        inv = pipeline_inventory("feature/other", spec_dir=self._spec_dir(), git=fake_git(repo=False))
        self.assertEqual(inv["orphans"][0]["merge_status"], "unknown")
        self.assertEqual(inv["closable"], [])

    def test_mixed_pipelines_partition_correctly(self):
        self._write("mine", "feature/mine")
        self._write("done", "feature/done")
        self._write("live", "feature/live")
        git = fake_git(
            branches=["feature/mine", "feature/done", "feature/live", "development"],
            merged=["feature/done"],
        )
        inv = pipeline_inventory("feature/mine", spec_dir=self._spec_dir(), git=git)
        self.assertEqual(len(inv["pipelines"]), 3)
        self.assertEqual(sorted(x["slug"] for x in inv["orphans"]), ["done", "live"])
        self.assertEqual([x["slug"] for x in inv["closable"]], ["done"])

    def test_malformed_state_json_does_not_crash(self):
        (self.state / "bad-state.json").write_text("{not json", encoding="utf-8")
        inv = pipeline_inventory("feature/other", spec_dir=self._spec_dir(), git=fake_git())
        self.assertEqual(inv["pipelines"][0]["slug"], "bad")
        self.assertEqual(inv["pipelines"][0]["merge_status"], "unknown")
        self.assertFalse(inv["pipelines"][0]["closable"])


class TestOpenQuestions(unittest.TestCase):
    SPEC = (
        "## Summary\n\nx\n\n"
        "## Open Questions\n\n"
        "- [ ] Q1 unresolved?\n"
        "- [x] Q2 resolved? — Yes, do it this way.\n"
        "- [X] Q3 no separator answer\n"
        "- not a checkbox line\n\n"
        "## Behavior\n\n- [ ] this is not an OQ (different section)\n"
    )

    def test_count(self):
        self.assertEqual(count_open_questions(self.SPEC), (1, 2))

    def test_count_empty(self):
        self.assertEqual(count_open_questions("no section here"), (0, 0))

    def test_resolved_extraction(self):
        resolved = get_resolved_oqs(self.SPEC)
        self.assertEqual(resolved["Q2 resolved?"], "Yes, do it this way.")
        self.assertEqual(resolved["Q3 no separator answer"], "")
        self.assertNotIn("Q1 unresolved?", resolved)


class TestAuditArtifacts(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / ".specwork" / "_spec").mkdir(parents=True)

    def test_reports_existence(self):
        spec = self.tmp / ".specwork" / "_spec" / "demo-spec.md"
        spec.write_text("x")
        audit = audit_artifacts("demo", spec_dir=str(self.tmp / ".specwork"))
        self.assertTrue(audit["spec_file"]["exists"])
        self.assertIsNotNone(audit["spec_file"]["mtime"])
        self.assertFalse(audit["plan_file"]["exists"])
        self.assertIsNone(audit["plan_file"]["mtime"])
        # every artifact name is present
        self.assertIn("state_file", audit)
        self.assertIn("rules_file", audit)


class TestStalenessMessage(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / ".specwork" / "_spec").mkdir(parents=True)
        (self.tmp / ".specwork" / "_plan").mkdir(parents=True)

    def _spec_dir(self):
        return str(self.tmp / ".specwork")

    def test_empty_when_no_plan(self):
        (self.tmp / ".specwork" / "_spec" / "d-spec.md").write_text("x")
        self.assertEqual(format_staleness_error("d", self._spec_dir()), "")

    def test_message_when_stale(self):
        import os
        import time

        spec = self.tmp / ".specwork" / "_spec" / "d-spec.md"
        plan = self.tmp / ".specwork" / "_plan" / "d-plan.md"
        plan.write_text("old")
        spec.write_text("new")
        # Make plan older than spec.
        old = time.time() - 100
        os.utime(plan, (old, old))
        msg = format_staleness_error("d", self._spec_dir())
        self.assertIn("Plan is stale", msg)
        self.assertIn("/sdd:plan", msg)
        self.assertEqual(check_plan_staleness("d", self._spec_dir())["fix_command"], "/sdd:plan")


class TestPlanRequired(TmpDirCase):
    def _state_dir(self):
        d = self.tmp / "_state"
        d.mkdir(parents=True, exist_ok=True)
        return self.tmp

    def _write_path(self, slug, plan_required_flag):
        sw = self._state_dir()
        (sw / "_state" / f"{slug}-path.json").write_text(
            json.dumps({"id": slug, "plan_required": plan_required_flag})
        )
        return sw

    def test_required_and_no_plan_blocks(self):
        sw = self._write_path("d", True)
        self.assertTrue(plan_required("d", sw))

    def test_required_but_plan_exists_passes(self):
        sw = self._write_path("d", True)
        (sw / "_plan").mkdir()
        (sw / "_plan" / "d-plan.md").write_text("plan")
        self.assertFalse(plan_required("d", sw))

    def test_not_required_passes(self):
        sw = self._write_path("d", False)
        self.assertFalse(plan_required("d", sw))

    def test_missing_path_json_passes(self):
        sw = self._state_dir()
        self.assertFalse(plan_required("d", sw))

    def test_malformed_path_json_passes(self):
        sw = self._state_dir()
        (sw / "_state" / "d-path.json").write_text("{not json")
        self.assertFalse(plan_required("d", sw))


if __name__ == "__main__":
    unittest.main()
