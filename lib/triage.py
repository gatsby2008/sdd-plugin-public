#!/usr/bin/env python3
"""
Triage classifier for the SDD pipeline. Reads a spec and classifies the ticket
into one of four advisory complexity tiers, then writes the recommended pipeline
path to .specwork/_state/<slug>-path.json.

Advisory only — no skill blocks on the result. /sdd:start prints the summary and
/sdd:state reads path.json (when present) to pick the first pending step.

Standalone:
  python3 triage.py <slug>                 # reads .specwork/_spec/<slug>-spec.md
  python3 triage.py <slug> --spec-dir DIR  # custom .specwork root
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gates import risk_signals, section_text

# Canonical layers, ordered shallow→deep. Each entry: (name, trigger regex).
LAYERS = [
    ("controller", r"\b(controller|endpoint|rest\s+api|@(get|post|put|patch|delete)mapping|@restcontroller)\b"),
    ("service", r"\b(service|business\s+logic|use\s+case|domain\s+logic)\b"),
    ("repository", r"\b(repository|\bdao\b|persistence|@query|jpa\s+entity|\bentity\b)\b"),
    ("listener", r"\b(listener|consumer|@sqslistener|@kafkalistener|subscriber)\b"),
    ("processor", r"\b(processor|message\s+handler|scheduler|\bjob\b|cron)\b"),
    ("client", r"\b(feign|webclient|resttemplate|external\s+api|http\s+client)\b"),
]

# High-risk triggers beyond gates.risk_signals (async/eventing surface).
ASYNC_EVENT = r"\b(asynchronous|@async|sqs|kafka|message\s+queue|event[- ]driven|publish[- ]subscribe|pub/sub|saga)\b"
TRANSACTIONAL = r"\b(@transactional|distributed\s+transaction|two[- ]phase\s+commit)\b"


def detect_layers(text):
    low = text.lower()
    return [name for name, pat in LAYERS if re.search(pat, low)]


def high_risk_reasons(text):
    """Return ordered, deduped list of high-risk reasons (empty = not high-risk)."""
    low = text.lower()
    reasons = []
    if re.search(ASYNC_EVENT, low):
        reasons.append("async/eventing")
    if re.search(TRANSACTIONAL, low):
        reasons.append("transactional")
    risks = risk_signals(text)
    if "db-migration" in risks:
        reasons.append("db-migration")
    if "auth-security" in risks:
        reasons.append("security")
    if "data-destructive" in risks:
        reasons.append("data-destructive")
    if "concurrency" in risks:
        reasons.append("concurrency")
    return list(dict.fromkeys(reasons))


def estimate_files(num_layers, text):
    """~2 files (impl + test) per layer, but never below explicit file mentions."""
    explicit = len(set(re.findall(r"`[\w/.-]+\.(?:java|kt|kts|sql)`", text)))
    return max(num_layers * 2, explicit, 1)


PATHS = {
    "trivial": ["/sdd:commit", "/sdd:mr"],
    "focused": ["/sdd:implement", "/sdd:commit", "/sdd:mr"],
    "standard": ["/sdd:plan", "/sdd:implement", "/sdd:commit", "/sdd:mr"],
    "high-risk": ["/sdd:plan", "/sdd:implement", "/sdd:test-design", "/sdd:test-impl", "/sdd:commit", "/sdd:mr"],
}
COMPLEXITY = {"trivial": "LOW", "focused": "LOW", "standard": "MEDIUM", "high-risk": "HIGH"}

# Triggers that imply real business logic (distinguishes focused from trivial).
LOGIC = r"\b(validat|calculat|transform|enrich|filter|aggregat|persist|dispatch|orchestrat|retry|fallback)\w*"


def classify(text):
    layers = detect_layers(text)
    risks = high_risk_reasons(text)
    est_files = estimate_files(len(layers), text)

    if risks or len(layers) >= 4 or est_files >= 7:
        ticket_type = "high-risk"
        why = "high-risk (" + ", ".join(risks) + ")" if risks else f"{len(layers)} layer(s) / {est_files} files"
    elif len(layers) >= 2:
        ticket_type = "standard"
        why = f"{len(layers)} layer(s): {', '.join(layers)} · ~{est_files} files expected"
    elif len(layers) == 1 or re.search(LOGIC, text.lower()):
        ticket_type = "focused"
        layer_desc = layers[0] if layers else "logic only"
        why = f"{len(layers)} layer(s): {layer_desc} · ~{est_files} files expected"
    else:
        ticket_type = "trivial"
        why = "no business logic detected · copy/rename change"

    path = PATHS[ticket_type]
    # Plan is REQUIRED (not merely recommended) for high-risk / architectural work:
    # /sdd:implement blocks until a plan exists. Trivial/focused/standard keep the
    # optional vibe-coding path (gap 2 of the Boris-Cherny gist alignment).
    plan_required = ticket_type == "high-risk"
    return {
        "ticket_type": ticket_type,
        "complexity": COMPLEXITY[ticket_type],
        "layers": layers,
        "estimated_files": est_files,
        "high_risk_signals": risks,
        "path": path,
        "plan_required": plan_required,
        "next": path[0],
        "why": why,
    }


def build_path_json(slug, classification):
    return {"schema_version": 1, "id": slug, **classification}


def render_summary(classification):
    plan_line = (
        "Plan:    REQUIRED before /sdd:implement (high-risk)\n"
        if classification.get("plan_required")
        else ""
    )
    return (
        f"Triage:  {classification['ticket_type']} ({classification['complexity']})\n"
        f"Path:    {' → '.join(classification['path'])}\n"
        f"{plan_line}"
        f"Why:     {classification['why']}"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Classify a spec into a pipeline path.")
    parser.add_argument("slug")
    parser.add_argument("--spec-dir", default=".specwork")
    args = parser.parse_args(argv)

    spec_path = Path(args.spec_dir) / "_spec" / f"{args.slug}-spec.md"
    if not spec_path.exists():
        print(f"Spec not found: {spec_path}", file=sys.stderr)
        return 1

    text = spec_path.read_text(encoding="utf-8")
    # Classify on Summary + Behavior when present; fall back to full spec.
    scoped = "\n\n".join(filter(None, [section_text(text, "Summary"), section_text(text, "Behavior")]))
    classification = classify(scoped or text)

    out = Path(args.spec_dir) / "_state" / f"{args.slug}-path.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build_path_json(args.slug, classification), indent=2) + "\n", encoding="utf-8")

    print(render_summary(classification))
    return 0


if __name__ == "__main__":
    sys.exit(main())
