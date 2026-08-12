"""benchmark_book.py — the contract, exercised as a real caller would.

The book's promise: no number without provenance, no quote without a status,
no stale figure reused silently. Each promise gets a test that would fail if
someone "simplified" the script back into a seed table or a bare-number quote.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from _helpers import run_json, run_script


class TestBenchmarkBook(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # ── record ──────────────────────────────────────────────────────

    def test_record_requires_source_url(self):
        proc = run_script("benchmark_book.py", "--action", "record",
                          "--metric", "cpm", "--channel", "linkedin",
                          "--low", "30", "--high", "60",
                          marketing_home=self.home)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("source URL", proc.stderr)

    def test_record_rejects_non_url_source(self):
        proc = run_script("benchmark_book.py", "--action", "record",
                          "--metric", "cpm", "--channel", "linkedin",
                          "--low", "30", "--high", "60",
                          "--source", "I remember reading this somewhere",
                          marketing_home=self.home)
        self.assertEqual(proc.returncode, 2)

    def test_record_rejects_unknown_metric(self):
        proc = run_script("benchmark_book.py", "--action", "record",
                          "--metric", "vibes", "--channel", "linkedin",
                          "--low", "1", "--high", "2",
                          "--source", "https://example.com/x",
                          marketing_home=self.home)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("Unknown metric", proc.stderr)

    def test_record_rejects_inverted_range(self):
        proc = run_script("benchmark_book.py", "--action", "record",
                          "--metric", "cpm", "--channel", "linkedin",
                          "--low", "60", "--high", "30",
                          "--source", "https://example.com/x",
                          marketing_home=self.home)
        self.assertEqual(proc.returncode, 2)

    def test_record_then_quote_fresh(self):
        run_script("benchmark_book.py", "--action", "record",
                   "--metric", "cpm", "--channel", "linkedin", "--segment", "b2b",
                   "--low", "30", "--high", "60",
                   "--source", "https://example.com/2026-benchmarks",
                   marketing_home=self.home)
        data, code = run_json("benchmark_book.py", "--action", "quote",
                              "--metric", "cpm", "--channel", "linkedin",
                              "--segment", "b2b", marketing_home=self.home)
        self.assertEqual(code, 0)
        self.assertEqual(data["status"], "fresh")
        self.assertEqual(data["low"], 30)
        self.assertEqual(data["high"], 60)
        self.assertEqual(data["source"], "https://example.com/2026-benchmarks")
        self.assertNotIn("warning", data)

    def test_point_value_records_low_equals_high(self):
        run_script("benchmark_book.py", "--action", "record",
                   "--metric", "cpc", "--channel", "meta",
                   "--value", "1.20", "--source", "https://example.com/x",
                   marketing_home=self.home)
        data, code = run_json("benchmark_book.py", "--action", "quote",
                              "--metric", "cpc", "--channel", "meta",
                              marketing_home=self.home)
        self.assertEqual(code, 0)
        self.assertEqual(data["low"], data["high"])

    # ── quote statuses ──────────────────────────────────────────────

    def test_quote_absent_refuses_with_lookup_hint(self):
        data, code = run_json("benchmark_book.py", "--action", "quote",
                              "--metric", "cpl", "--channel", "tiktok",
                              marketing_home=self.home)
        self.assertEqual(code, 3)
        self.assertEqual(data["status"], "absent")
        self.assertIn("Look it up live", data["action_required"])
        self.assertIn("record", data["action_required"])

    def test_quote_aging_carries_warning(self):
        as_of = (date.today() - timedelta(days=180)).isoformat()
        run_script("benchmark_book.py", "--action", "record",
                   "--metric", "cpm", "--channel", "meta",
                   "--low", "8", "--high", "18", "--as-of", as_of,
                   "--source", "https://example.com/x", marketing_home=self.home)
        data, code = run_json("benchmark_book.py", "--action", "quote",
                              "--metric", "cpm", "--channel", "meta",
                              marketing_home=self.home)
        self.assertEqual(code, 0)
        self.assertEqual(data["status"], "aging")
        self.assertIn("refresh", data["warning"])

    def test_quote_stale_refuses(self):
        as_of = (date.today() - timedelta(days=400)).isoformat()
        run_script("benchmark_book.py", "--action", "record",
                   "--metric", "cpm", "--channel", "meta",
                   "--low", "8", "--high", "18", "--as-of", as_of,
                   "--source", "https://example.com/x", marketing_home=self.home)
        data, code = run_json("benchmark_book.py", "--action", "quote",
                              "--metric", "cpm", "--channel", "meta",
                              marketing_home=self.home)
        self.assertEqual(code, 3)
        self.assertEqual(data["status"], "stale")
        self.assertIn("refusing to quote", data["action_required"])

    def test_segment_falls_back_to_channel_wide_and_says_so(self):
        run_script("benchmark_book.py", "--action", "record",
                   "--metric", "cpm", "--channel", "linkedin",
                   "--low", "30", "--high", "60",
                   "--source", "https://example.com/x", marketing_home=self.home)
        data, code = run_json("benchmark_book.py", "--action", "quote",
                              "--metric", "cpm", "--channel", "linkedin",
                              "--segment", "healthcare", marketing_home=self.home)
        self.assertEqual(code, 0)
        self.assertIn("segment_fallback", data)

    # ── the no-seed-table promise ───────────────────────────────────

    def test_ships_empty_no_seeded_numbers(self):
        """A fresh workspace has zero entries: every number must arrive via a
        recorded lookup. If someone adds a seed table this fails."""
        data, code = run_json("benchmark_book.py", "--action", "list",
                              marketing_home=self.home)
        self.assertEqual(code, 0)
        self.assertEqual(data, [])

    def test_corrupt_book_is_an_error_not_an_empty_book(self):
        book = self.home / "benchmark-book.json"
        book.parent.mkdir(parents=True, exist_ok=True)
        book.write_text("{not json", encoding="utf-8")
        proc = run_script("benchmark_book.py", "--action", "list",
                          marketing_home=self.home)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("Corrupt", proc.stderr)

    def test_staleness_reports_ages(self):
        old = (date.today() - timedelta(days=200)).isoformat()
        run_script("benchmark_book.py", "--action", "record",
                   "--metric", "cpc", "--channel", "google-search",
                   "--low", "1", "--high", "5", "--as-of", old,
                   "--source", "https://example.com/x", marketing_home=self.home)
        data, code = run_json("benchmark_book.py", "--action", "staleness",
                              marketing_home=self.home)
        self.assertEqual(code, 0)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["status"], "aging")
        self.assertGreaterEqual(data[0]["age_days"], 200)


if __name__ == "__main__":
    unittest.main()
