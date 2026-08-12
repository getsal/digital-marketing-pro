"""The capstone smoke: a synthetic brand runs the executable spine end to end.

Unit tests prove each script works alone; this proves they work as an
ENGAGEMENT — one fresh workspace, one brand, outputs of each step feeding the
next, exactly as the 12-Part methodology chains them:

    intake (engagement-state) → market truth with provenance (benchmark_book)
    → media math on quoted numbers (roi-calculator) → campaign persistence
    with the provenance still attached (campaign-tracker) → model resolution
    that carries its basis (resolve_model) → coherent engagement status.

The flagship assertion is the provenance chain: the source URL recorded with a
benchmark must surface, unbroken, inside the campaign that was planned on it.
If any joint drops provenance, "every number has a source" is marketing, not
architecture — and this test is what keeps it architecture.

Brand and all figures are synthetic ("Meridian Roasters" does not exist).
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _helpers import run_json, run_script

BRAND = "Meridian Roasters"
ENG = "2026-q3"
BENCH_SOURCE = "https://example.com/2026-linkedin-benchmarks"


class TestEngagementSmoke(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_full_engagement_chain(self):
        # ── Part 1: intake ──────────────────────────────────────────
        data, rc = run_json("engagement-state.py", "init", "--brand", BRAND,
                            "--id", ENG, marketing_home=self.home)
        self.assertEqual(rc, 0, f"engagement init failed: {data}")
        self.assertEqual(data["action"], "initialised")

        _, rc = run_json("engagement-state.py", "add-stone-fact",
                         "--brand", BRAND, "--id", ENG,
                         "--fact-json", json.dumps({
                             "fact": "Wholesale accounts drive 60% of revenue",
                             "source": "intake workshop notes",
                             "category": "business"}),
                         marketing_home=self.home)
        self.assertEqual(rc, 0, "add-stone-fact failed")

        _, rc = run_json("engagement-state.py", "add-opinion",
                         "--brand", BRAND, "--id", ENG,
                         "--hypothesis-json", json.dumps({
                             "hypothesis": "LinkedIn thought leadership can open wholesale doors",
                             "category": "channel",
                             "client_evidence": "two wholesale deals began with a founder post",
                             "research_question": "Do LinkedIn-sourced leads close at wholesale rates?"}),
                         marketing_home=self.home)
        self.assertEqual(rc, 0, "add-opinion failed")

        for step in ("mark-part-started", "mark-part-completed"):
            _, rc = run_json("engagement-state.py", step, "--brand", BRAND,
                             "--id", ENG, "--part", "1", marketing_home=self.home)
            self.assertEqual(rc, 0, f"{step} part 1 failed")

        # ── Market truth enters with provenance ─────────────────────
        for metric, low, high in (("cpm", 30, 60), ("cpl", 50, 200)):
            proc = run_script("benchmark_book.py", "--action", "record",
                              "--metric", metric, "--channel", "linkedin",
                              "--segment", "b2b", "--low", low, "--high", high,
                              "--source", BENCH_SOURCE, marketing_home=self.home)
            self.assertEqual(proc.returncode, 0, f"record {metric}: {proc.stderr}")

        cpl, rc = run_json("benchmark_book.py", "--action", "quote",
                           "--metric", "cpl", "--channel", "linkedin",
                           "--segment", "b2b", marketing_home=self.home)
        self.assertEqual(rc, 0)
        self.assertEqual(cpl["status"], "fresh")

        # ── Media math runs on the QUOTED numbers, not on memory ────
        cpl_mid = (cpl["low"] + cpl["high"]) / 2          # 125
        spend = 5000
        expected_leads = int(spend / cpl_mid)              # 40
        channels = [
            {"name": "linkedin", "spend": spend, "conversions": expected_leads,
             "revenue": expected_leads * 300},
            {"name": "organic", "spend": 0, "conversions": 12, "revenue": 3600},
        ]
        proc = run_script("roi-calculator.py", "--channels", json.dumps(channels),
                          "--period", "2026-Q3", marketing_home=self.home)
        self.assertEqual(proc.returncode, 0, f"roi-calculator failed: {proc.stderr}")
        roi_payload = json.loads(proc.stdout)
        self.assertTrue(roi_payload, "roi-calculator returned empty payload")

        # ── Campaign persists WITH the provenance attached ──────────
        campaign = {
            "name": "Q3 wholesale lead gen",
            "channel": "linkedin",
            "budget": spend,
            "target_leads": expected_leads,
            "assumptions": {"cpl": {"low": cpl["low"], "high": cpl["high"],
                                    "source": cpl["source"], "as_of": cpl["as_of"]}},
        }
        data, rc = run_json("campaign-tracker.py", "--brand", BRAND,
                            "--action", "save-campaign",
                            "--data", json.dumps(campaign), marketing_home=self.home)
        self.assertEqual(rc, 0, f"save-campaign failed: {data}")
        self.assertEqual(data.get("status"), "saved", f"save-campaign refused: {data}")
        campaign_id = data["campaign_id"]

        listed, rc = run_json("campaign-tracker.py", "--brand", BRAND,
                              "--action", "list-campaigns", marketing_home=self.home)
        self.assertEqual(rc, 0)
        self.assertIn("Q3 wholesale lead gen", json.dumps(listed),
                      "campaign not visible in list-campaigns")

        stored, rc = run_json("campaign-tracker.py", "--brand", BRAND,
                              "--action", "get-campaign", "--id", campaign_id,
                              marketing_home=self.home)
        self.assertEqual(rc, 0)
        # THE flagship assertion: the benchmark's source URL survived the whole
        # chain — quote → plan → persisted campaign record. No joint dropped it.
        self.assertEqual(stored["assumptions"]["cpl"]["source"], BENCH_SOURCE,
                         "provenance was dropped between benchmark quote and campaign store")
        self.assertEqual(stored["assumptions"]["cpl"]["as_of"], cpl["as_of"])
        self.assertEqual(stored["budget"], spend)

        # ── Model resolution carries its basis ──────────────────────
        proc = run_script("resolve_model.py", "--for-execution",
                          "latest-balanced-anthropic", marketing_home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        resolved = json.loads(proc.stdout)
        self.assertEqual(resolved["basis"], "shipped-registry")
        self.assertTrue(resolved["model_id"])

        # ── Engagement state is coherent at the end ─────────────────
        status, rc = run_json("engagement-state.py", "status", "--brand", BRAND,
                              "--id", ENG, marketing_home=self.home)
        self.assertEqual(rc, 0)
        stext = json.dumps(status)
        self.assertIn("completed", stext, f"part 1 not completed in status: {stext[:400]}")

    def test_chain_refuses_unprovenanced_numbers(self):
        """The negative twin: with NO recorded benchmark the quote step refuses
        (exit 3) — the chain cannot silently run on remembered numbers."""
        data, rc = run_json("benchmark_book.py", "--action", "quote",
                            "--metric", "cpl", "--channel", "linkedin",
                            marketing_home=self.home)
        self.assertEqual(rc, 3)
        self.assertEqual(data["status"], "absent")


if __name__ == "__main__":
    unittest.main()
