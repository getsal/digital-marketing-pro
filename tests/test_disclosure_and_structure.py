"""DMP mirror of the CF v3.22.0 provenance layer: disclosure + structural tier.

Pins: the surface classifier's uncertain⇒disclose fail-safe, the vendor-neutral
author-optional default wording, the structural scan firing on an AI-shaped
fixture and staying quiet on a human-shaped one, advisory-never-a-gate, and
the skill wiring (brand-setup config, content-engine application + recording,
/check advisory section that never scores).
"""
from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ds = _load("dmp_detect_surface", "detect_surface.py")
sts = _load("dmp_structural_scan", "structural-tell-scan.py")

CONTENT_ENGINE = (REPO / "skills" / "content-engine" / "SKILL.md").read_text(encoding="utf-8")
CHECK = (REPO / "skills" / "check" / "SKILL.md").read_text(encoding="utf-8")
BRAND_SETUP = (REPO / "skills" / "brand-setup" / "SKILL.md").read_text(encoding="utf-8")

_AI_PARA = ("Businesses today face many challenges in the modern landscape. It is "
            "important to remember that success typically requires careful planning and "
            "can often depend on many factors. Organizations may generally benefit from "
            "adopting best practices that can usually improve outcomes for teams.")
AI_FIXTURE = "# The Guide\n\n" + "".join(
    f"## {h}\n\n{_AI_PARA}\n\n{_AI_PARA}\n\nUltimately, this matters because planning "
    "is essential. In conclusion, the key takeaway is that preparation typically wins.\n\n"
    for h in ("Understanding The Basics", "Building The Foundation",
              "Growing The Business", "Scaling The Operation", "Measuring The Results"))

HUMAN_FIXTURE = """# What 14 months of failed cold email taught us

## The $4,300 mistake nobody warns you about

I spent Q3 2025 sending 11,000 cold emails for Acme Robotics. Open rate: 61%. Meetings booked: 4.

Four.

Our deliverability consultant, Priya Sharma, put it bluntly: "You optimized the wrong funnel stage." She was right, and the fix took one afternoon of rewriting.

## Why the 61% open rate was a trap that took us months to see

Opens measure subject lines. Meetings measure the offer. According to HubSpot's 2026 State of Sales report, reply-to-meeting conversion sits near 9% for B2B SaaS — we were at 2.1%.

The gap came from one paragraph in our template, the one bragging about features. I killed it and replaced it with a single case number: "We cut Vertex Manufacturing's quote-turnaround from 6 days to 11 hours." Replies tripled in two weeks, from 38 to 117.

## What I'd tell anyone starting this in 2026

Skip the sequence tooling debates entirely. Spend the first week interviewing five customers about why they actually bought — record the calls and quote them verbatim.

The tools don't book the meetings. The specifics do, and I have fourteen months of expensive proof of exactly that.
"""


class TestSurfaceAndDecision(unittest.TestCase):
    def test_classifier_directions(self):
        self.assertEqual(ds.classify_surface({"CLAUDECODE": "1"})["surface"], "claude")
        self.assertEqual(ds.classify_surface({"CODEX_SESSION_ID": "x"})["surface"], "non-claude")
        self.assertEqual(ds.classify_surface({})["surface"], "uncertain")

    def test_decision_matrix_with_the_failsafe_pin(self):
        cases = {("always", "non-claude"): True, ("off", "claude"): False,
                 ("claude-surfaces", "claude"): True,
                 ("claude-surfaces", "non-claude"): False,
                 ("claude-surfaces", "uncertain"): True}  # the fail-safe
        for (mode, surface), expected in cases.items():
            with self.subTest(mode=mode, surface=surface):
                self.assertEqual(ds.disclosure_applies(mode, surface), expected)


class TestStructuralScan(unittest.TestCase):
    def test_ai_fixture_fires_attention_on_core_tells(self):
        f = sts.structure_scan(AI_FIXTURE)["findings"]
        for key in ("moralizing", "section_symmetry", "parallel_headings",
                    "specificity", "stance"):
            self.assertEqual(f[key]["band"], "ATTENTION",
                             f"{key} did not fire on the AI-shaped fixture")

    def test_human_fixture_stays_ok_on_core_tells(self):
        f = sts.structure_scan(HUMAN_FIXTURE)["findings"]
        for key in ("moralizing", "section_symmetry", "parallel_headings",
                    "specificity", "stance"):
            self.assertEqual(f[key]["band"], "OK",
                             f"{key} false-fired on the human-shaped fixture")

    def test_findings_carry_spans(self):
        spans = sts.structure_scan(AI_FIXTURE)["findings"]["moralizing"]["spans"]
        self.assertTrue(spans)

    def test_scan_states_the_advisory_and_watermark_contract(self):
        note = sts.structure_scan(AI_FIXTURE)["advisory_note"]
        self.assertIn("advisory only", note)
        self.assertIn("no relationship to any statistical watermark", note)


class TestAdvisoryNeverAGate(unittest.TestCase):
    def test_structural_keys_absent_from_eval_configs(self):
        hits = []
        for cfg in (REPO / "config").glob("*.json"):
            flat = cfg.read_text(encoding="utf-8").lower()
            for needle in ("structural-tell", "structure_scan", "moralizing",
                           "parallel_heading"):
                if needle in flat:
                    hits.append(f"{cfg.name}: {needle}")
        self.assertEqual(hits, [],
                         "structural-tier thresholds leaked into a scored config: " + "; ".join(hits))

    def test_check_skill_says_it_never_scores_the_section(self):
        self.assertIn("NEVER affects the PASS/WARN/BLOCKED decision", CHECK)

    def test_content_engine_keeps_it_out_of_the_ready_gates(self):
        self.assertIn("it never gates `status: ready`", CONTENT_ENGINE)


class TestSkillWiring(unittest.TestCase):
    def test_content_engine_applies_and_records_the_disclosure(self):
        self.assertIn("detect_surface.py", CONTENT_ENGINE)
        self.assertIn("Never override the script's answer", CONTENT_ENGINE)
        self.assertIn("a recorded choice, not an omission", CONTENT_ENGINE)
        self.assertIn("survives `/digital-marketing-pro:publish-blog`", CONTENT_ENGINE)

    def test_default_wording_is_vendor_neutral(self):
        texts = re.findall(r"`\*Created with AI assistance[^`]*\*`", CONTENT_ENGINE)
        self.assertEqual(len(texts), 2)
        vendor_re = re.compile(r"\b(claude|anthropic|gpt|openai|gemini|google|copilot|codex)\b", re.I)
        for t in texts:
            self.assertIsNone(vendor_re.search(t), f"vendor name in default wording: {t}")

    def test_author_stays_optional(self):
        self.assertIn("never invent a name", CONTENT_ENGINE)
        self.assertIn("may stay null", BRAND_SETUP)

    def test_brand_setup_documents_all_three_modes(self):
        for token in ('"claude-surfaces"', "`always`", "`off`", "ai_disclosure"):
            self.assertIn(token, BRAND_SETUP)


if __name__ == "__main__":
    unittest.main()
