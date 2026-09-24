#!/usr/bin/env python3
"""
spec draft → triage handoff integration test.

Bootstraps a project with start.py's helpers, then simulates /sdd:spec draft
mode by writing spec.md via write_spec_scaffold (start no longer creates the
spec — /sdd:spec does). Verifies the artifacts satisfy the
gates.check_required_artifacts gate, writes a realistic spec for each triage
tier, runs triage.py, and verifies the recommended path includes the correct
pipeline steps (test-design / test-impl only when complexity warrants it).
Does not exercise plan.py discovery or the runtime gates beyond artifact
presence.
"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

LIB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, LIB_DIR)

# Load start.py (hyphen in filename)
_spec = importlib.util.spec_from_file_location("start", Path(LIB_DIR) / "start.py")
_start = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_start)

# Load triage.py and gates.py
import triage
import gates

PATH_JSON_KEYS = {
    "schema_version", "id", "ticket_type", "complexity",
    "layers", "estimated_files", "high_risk_signals", "path", "plan_required", "next", "why",
}


class E2EProjectCase(unittest.TestCase):
    """Sets up a temp directory with a bootstrapped .specwork structure."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.spec_dir = self.root / ".specwork"
        self.slug = "e2e-test"
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.root)

        # Bootstrap all artifacts via start.py's individual functions.
        spec_dir = str(self.spec_dir)
        for sub in ["_spec", "_state", "_progress"]:
            (self.spec_dir / sub).mkdir(parents=True, exist_ok=True)

        state = _start.build_state(
            self.slug, "TICKET-123", "jira", "feature/TICKET-123", "development", spec_dir)
        (self.spec_dir / "_state" / f"{self.slug}-state.json").write_text(
            json.dumps(state, indent=2) + "\n", encoding="utf-8")

        rules = _start.build_rules(self.slug, [])
        (self.spec_dir / "_state" / f"{self.slug}-rules.json").write_text(
            json.dumps(rules, indent=2) + "\n", encoding="utf-8")

        cache = _start.build_cache(self.slug)
        (self.spec_dir / "_state" / f"{self.slug}-implementation-cache.json").write_text(
            json.dumps(cache, indent=2) + "\n", encoding="utf-8")

        _start.write_source_md(self.slug, spec_dir, "TICKET-123", "jira")
        _start.write_spec_scaffold(self.slug, spec_dir, "TICKET-123", "jira")

    def _write_spec(self, body):
        """Overwrite the spec scaffold with a realistic full spec."""
        spec_path = self.spec_dir / "_spec" / f"{self.slug}-spec.md"
        spec_path.write_text(body, encoding="utf-8")

    def _run_triage(self):
        """Run triage.main(), validate the path.json contract, and return it."""
        rc = triage.main([self.slug, "--spec-dir", str(self.spec_dir)])
        self.assertEqual(rc, 0)
        out = self.spec_dir / "_state" / f"{self.slug}-path.json"
        self.assertTrue(out.exists())
        data = json.loads(out.read_text())
        # Full schema shape — status parses this artifact.
        self.assertEqual(set(data), PATH_JSON_KEYS)
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["id"], self.slug)
        # Contract status relies on: Next: is the first step of the path.
        self.assertEqual(data["next"], data["path"][0])
        return data

    def _assert_path_includes(self, data, expected_steps):
        path = data["path"]
        for step in expected_steps:
            self.assertIn(
                step, path,
                f"Expected {step} in path {path} for {data['ticket_type']} ticket"
            )

    def _assert_path_excludes(self, data, unexpected_steps):
        path = data["path"]
        for step in unexpected_steps:
            self.assertNotIn(
                step, path,
                f"Did not expect {step} in path {path} for {data['ticket_type']} ticket"
            )

    # ------------------------------------------------------------------
    # Fixture verification
    # ------------------------------------------------------------------

    def test_bootstrap_creates_all_artifacts(self):
        """start.py creates state.json, rules.json, cache, source.md; /sdd:spec (simulated) creates spec.md."""
        self.assertTrue((self.spec_dir / "_state" / f"{self.slug}-state.json").exists())
        self.assertTrue((self.spec_dir / "_state" / f"{self.slug}-rules.json").exists())
        self.assertTrue((self.spec_dir / "_state" / f"{self.slug}-implementation-cache.json").exists())
        self.assertTrue((self.spec_dir / "_spec" / f"{self.slug}-source.md").exists())
        self.assertTrue((self.spec_dir / "_spec" / f"{self.slug}-spec.md").exists())

    def test_state_contains_path_file_field(self):
        """state.json declares path_file for triage output."""
        state = json.loads((self.spec_dir / "_state" / f"{self.slug}-state.json").read_text())
        self.assertIn("path_file", state)
        self.assertIn("-path.json", state["path_file"])

    def test_bootstrap_satisfies_required_artifacts_gate(self):
        """The bootstrapped artifacts pass gates.check_required_artifacts (no missing)."""
        missing = gates.check_required_artifacts(self.slug, spec_dir=str(self.spec_dir))
        self.assertEqual(missing, [])

    # ------------------------------------------------------------------
    # Pipeline step suggestion by triage tier
    # ------------------------------------------------------------------

    def test_trivial_spec_skips_test_design_and_f_impl(self):
        """A trivial copy-change spec must NOT suggest test-design or test-impl."""
        self._write_spec("""\
# e2e-test — Rename welcome copy

> Source: JIRA: TICKET-123

## Summary

Rename the welcome banner text on the landing page.

## Scope

### In scope
- Change the heading text in landing-page.properties

### Out of scope
- No controller, service, or repository changes

## Behavior

1. Replace "Welcome to our platform" with "Hello again".

## Implementation Context

- Resource bundle: landing-page.properties

## Expected Change Scope
- **Expected files touched**: 1
- **Expected layers**:
- **Avoid touching**:
  - Any Java classes

## Safe Constraints
**Safe**:
- Editing resource bundles

**Unsafe**:
- Editing Java classes
""")
        data = self._run_triage()
        self.assertEqual(data["ticket_type"], "trivial")
        self._assert_path_excludes(data, ["/sdd:test-design", "/sdd:test-impl", "/sdd:implement"])
        self._assert_path_includes(data, ["/sdd:commit", "/sdd:mr"])

    def test_focused_spec_skips_test_design_and_plan(self):
        """A focused 1-layer change must NOT suggest test-design, test-impl, or plan."""
        self._write_spec("""\
# e2e-test — Add validation to login form

> Source: JIRA: TICKET-123

## Summary

Add input validation to the login form to reject empty email.

## Scope

### In scope
- Validate email field is non-empty before calling the backend

### Out of scope
- No UI changes beyond validation

## Behavior

1. Service validates the email is non-empty.
2. Throws ValidationException if empty.

## Implementation Context

- LoginService

## Expected Change Scope
- **Expected files touched**: 1-2
- **Expected layers**: service
- **Avoid touching**:
  - Controllers and repositories

## Safe Constraints
**Safe**:
- Adding input validation

**Unsafe**:
- Changing login logic
""")
        data = self._run_triage()
        self.assertEqual(data["ticket_type"], "focused")
        self._assert_path_excludes(data, ["/sdd:test-design", "/sdd:test-impl", "/sdd:plan"])
        self._assert_path_includes(data, ["/sdd:implement", "/sdd:commit", "/sdd:mr"])

    def test_standard_spec_skips_test_design(self):
        """A standard 3-layer change must NOT suggest test-design or test-impl."""
        self._write_spec("""\
# e2e-test — Add offer listing endpoint

> Source: JIRA: TICKET-123

## Summary

Add a new REST endpoint to list active offers for the current user.

## Scope

### In scope
- New controller endpoint GET /api/v1/offers/active
- New service method to query active offers
- Repository query to filter by active flag

## Behavior

1. Controller receives GET /api/v1/offers/active.
2. Service calls repository to fetch active offers.
3. Returns list of OfferDTO.

## Implementation Context

- OfferController
- OfferService
- OfferRepository

## Expected Change Scope
- **Expected files touched**: 3-6
- **Expected layers**: controller, service, repository
- **Avoid touching**:
  - Auth or security config

## Safe Constraints
**Safe**:
- Adding GET endpoints
- Adding read-only queries

**Unsafe**:
- Changing authentication
""")
        data = self._run_triage()
        self.assertEqual(data["ticket_type"], "standard")
        self._assert_path_excludes(data, ["/sdd:test-design", "/sdd:test-impl"])
        self._assert_path_includes(data, ["/sdd:plan", "/sdd:implement", "/sdd:commit", "/sdd:mr"])

    def test_high_risk_spec_includes_test_design_and_test_impl(self):
        """A high-risk change (async + auth) MUST include test-design and test-impl."""
        self._write_spec("""\
# e2e-test — Add async Kafka event producer with auth

> Source: JIRA: TICKET-123

## Summary

Publish OfferActivated events to Kafka when an offer transitions to active,
with authentication on the producer.

## Scope

### In scope
- New KafkaListener to consume offer state changes
- New event producer service
- Authentication token for the Kafka producer

## Behavior

1. OfferStateChangeEvent is consumed by a listener.
2. Listener calls the async producer service.
3. Producer publishes to the offer-events topic with auth token.

## Implementation Context

- OfferEventListener
- OfferEventProducer
- KafkaConfig

## Expected Change Scope
- **Expected files touched**: 5-8
- **Expected layers**: listener, service, config
- **Avoid touching**:
  - Existing REST endpoints

## Safe Constraints
**Safe**:
- Adding new Kafka consumers and producers

**Unsafe**:
- Changing existing event schemas
""")
        data = self._run_triage()
        self.assertEqual(data["ticket_type"], "high-risk")
        self._assert_path_includes(data, ["/sdd:test-design", "/sdd:test-impl", "/sdd:plan", "/sdd:implement", "/sdd:commit", "/sdd:mr"])

    def test_high_risk_db_migration_includes_test_steps(self):
        """A migration change MUST include test-design and test-impl."""
        self._write_spec("""\
# e2e-test — Add consent column via Flyway migration

> Source: JIRA: TICKET-123

## Summary

Add a consent_given column to the user table via a Flyway migration.

## Scope

### In scope
- New Flyway migration V2025_01_01__add_consent_column.sql
- Update User entity with new field
- Repository method to update consent

## Behavior

1. Flyway migration runs on startup.
2. User entity gets the new column mapping.
3. Service exposes a method to update consent flag.

## Implementation Context

- User entity
- UserRepository
- Flyway migration directory

## Expected Change Scope
- **Expected files touched**: 3-5
- **Expected layers**: repository, service
- **Avoid touching**:
  - Controllers

## Safe Constraints
**Safe**:
- Adding nullable columns with defaults

**Unsafe**:
- Backfilling data
""")
        data = self._run_triage()
        self.assertEqual(data["ticket_type"], "high-risk")
        self._assert_path_includes(data, ["/sdd:test-design", "/sdd:test-impl"])

    def test_high_risk_by_layer_count_without_risk_keywords(self):
        """4+ layers escalates to high-risk even with no async/security/migration keywords."""
        self._write_spec("""\
# e2e-test — Wire offer listing across all layers

> Source: JIRA: TICKET-123

## Summary

Add a read-only offer listing feature spanning every layer, no risky operations.

## Behavior

1. The controller receives the request.
2. The service applies business logic.
3. The repository runs the query.
4. A Feign client enriches the result from an external API.

## Implementation Context

- OfferController
- OfferService
- OfferRepository
- OfferEnrichmentClient
""")
        data = self._run_triage()
        self.assertEqual(data["ticket_type"], "high-risk")
        self.assertEqual(data["high_risk_signals"], [])
        self.assertGreaterEqual(len(data["layers"]), 4)
        self._assert_path_includes(data, ["/sdd:test-design", "/sdd:test-impl"])

    def test_state_and_triage_are_consistent(self):
        """state.json path_file field matches the path.json triage wrote."""
        self._write_spec("""\
# e2e-test — Add service method

> Source: JIRA: TICKET-123

## Summary

Add a service method to compute discounts.

## Implementation Context

- DiscountService

## Expected Change Scope
- **Expected files touched**: 1-2
- **Expected layers**: service
""")
        data = self._run_triage()
        self.assertEqual(data["ticket_type"], "focused")
        state = json.loads((self.spec_dir / "_state" / f"{self.slug}-state.json").read_text())
        expected_path = f".specwork/_state/{self.slug}-path.json"
        self.assertEqual(state["path_file"], expected_path)
        # path_file (relative to cwd) resolves to the file triage actually wrote.
        self.assertTrue((self.root / state["path_file"]).exists())


if __name__ == "__main__":
    unittest.main()
