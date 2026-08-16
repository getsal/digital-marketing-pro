"""The content-engine run auditor: re-derive, never trust.

Imported from the suite-wide run-audit pattern. Each plant reproduces a
failure class observed on a real run: a scorecard declaring ready past its own
gates, scan JSON embedded in the file authorship.py measures, an authorship
record describing a body that changed after it was written. Stdlib only.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
AUDIT = REPO / "scripts" / "run-audit.py"

HUMANIZED = """Turns out the rollout was not delicate: three services moved in one
weekend and the oldest one broke twice. We measured the queue depth, wrote the
number down, and moved on to the part that actually cost money.

What broke was the queue, not the database. The team shipped the fix on Tuesday
and the backlog cleared in four hours, which is the only statistic this piece
needs.
"""

READY_SCORECARD = """# Quality Scorecard

| Gate | Result |
|---|---|
| brand_voice_match | pass |
| fact_check_clean | pass |
| humanize_passed | pass |
| seo_complete | pass |
| eu_disclosure_if_ai | n/a (no EU market) |

status: ready
"""

PUBLISH_READY = " ".join(["Publish-ready body sentence number %d." % i
                          for i in range(60)])


class Fixture(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.run = Path(self._tmp.name)
        for name, content in [
            ("00-input.md", "# input"), ("01-research.md", "# research"),
            ("02-outline.md", "# outline"), ("03-draft-v1.md", "# draft"),
            ("04-fact-check.md", "# factcheck: 0 unverified claims"),
            ("05-humanize.md", HUMANIZED),
            ("05-scans.json", json.dumps({"surface": {"flagged_paragraph_pct": 0.0},
                                          "structure": {"band": "OK"}})),
            ("06-brand-voice-check.md",
             "formality distance 0.05\nenergy distance 0.08\n"
             "humor distance 0.02\nauthority distance 0.11\n"),
            ("07-seo-checklist.md", "# seo: all placements present"),
            ("08-quality-scorecard.md", READY_SCORECARD),
            ("09-publish-ready.md", PUBLISH_READY),
            ("PLAN.md", "# plan"),
        ]:
            (self.run / name).write_text(content, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def audit(self, *extra):
        proc = subprocess.run(
            [sys.executable, str(AUDIT), "--run-dir", str(self.run), *extra],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            return proc.returncode, json.loads(proc.stdout)
        except json.JSONDecodeError:
            self.fail(f"non-JSON (exit {proc.returncode}): "
                      f"{proc.stdout[:300]} {proc.stderr[:300]}")


class TestCleanRun(Fixture):
    def test_clean_run_is_clean(self):
        code, out = self.audit()
        fails = [c for c in out["checks"] if c["result"] == "FAIL"]
        self.assertEqual(code, 0, fails)
        self.assertEqual(out["verdict"], "CLEAN")
        self.assertTrue(out["declares_ready"])

    def test_result_written_into_run(self):
        self.audit()
        rec = json.loads((self.run / "run-audit.json").read_text(encoding="utf-8"))
        self.assertIn(rec["verdict"], ("CLEAN", "VIOLATIONS"))

    def test_absent_source_draft_is_na_not_pass(self):
        _, out = self.audit()
        na = [c for c in out["checks"] if c["result"] == "N/A"]
        self.assertTrue(any("authorship" in c["name"] for c in na), na)


class TestPlants(Fixture):
    def test_missing_artifact_fails(self):
        (self.run / "04-fact-check.md").unlink()
        code, out = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("04-fact-check.md", str(out["checks"]))

    def test_ready_past_the_voice_gate(self):
        """The scorecard says ready while its own recorded distance is out of
        tolerance — the unfailable-gate disease, from the measuring side."""
        (self.run / "06-brand-voice-check.md").write_text(
            "formality distance 0.05\nenergy distance 0.31\n", encoding="utf-8")
        code, out = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("0.31", str(out["checks"]))

    def test_scan_json_embedded_in_the_measured_file(self):
        """The corruption class that once flipped may_claim_authored."""
        with open(self.run / "05-humanize.md", "a", encoding="utf-8") as fh:
            fh.write('\n{"surface": {"flagged_paragraph_pct": 0.0}}\n')
        code, out = self.audit()
        self.assertEqual(code, 1)
        fails = [c["name"] for c in out["checks"] if c["result"] == "FAIL"]
        self.assertTrue(any("embedded" in n for n in fails), fails)

    def test_orphan_authorship_record(self):
        (self.run / "05-authorship.json").write_text("{}", encoding="utf-8")
        code, out = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("travel together", str(out["checks"]))

    def test_stale_authorship_record(self):
        src = "the queue broke twice and i wrote the number down myself.\n"
        (self.run / "00-source-draft.md").write_text(src, encoding="utf-8")
        (self.run / "05-authorship.json").write_text(
            json.dumps({"author_word_share": 0.9}), encoding="utf-8")
        code, out = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("fresh measurement", str(out["checks"]))

    def test_publish_ready_stub(self):
        (self.run / "09-publish-ready.md").write_text("done.", encoding="utf-8")
        code, out = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("stub", str(out["checks"]))

    def test_placeholder_in_publish_ready(self):
        (self.run / "09-publish-ready.md").write_text(
            PUBLISH_READY + "\n[TODO: add the chart here]\n", encoding="utf-8")
        code, out = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("placeholder", str(out["checks"]).lower())

    def test_not_ready_run_skips_ready_checks(self):
        (self.run / "08-quality-scorecard.md").write_text(
            "status: draft", encoding="utf-8")
        _, out = self.audit()
        self.assertFalse(out["declares_ready"])
        na = [c for c in out["checks"] if c["result"] == "N/A"]
        self.assertTrue(any("ready-state" in c["name"] for c in na), na)


class TestContractWiring(unittest.TestCase):
    def test_content_engine_requires_the_audit_before_ready(self):
        text = (REPO / "skills" / "content-engine" / "SKILL.md")\
            .read_text(encoding="utf-8")
        self.assertIn("run-audit.py", text,
                      "content-engine never runs the auditor, so 'status: "
                      "ready' is still a claim nothing re-derives")


if __name__ == "__main__":
    unittest.main(verbosity=2)
