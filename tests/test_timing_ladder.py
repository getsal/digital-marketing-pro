"""Posting-time and send-time recommendations follow the measurement ladder.

The contract: first-party history outranks population baselines and is the
only path to "high" confidence; baselines are stamped, capped at medium, and
age out (warn, then refuse) instead of masquerading as timeless truth; email
outputs always carry the per-recipient-STO doctrine. A timing table that
cannot expire is a 2024 opinion wearing a 2026 date — these tests keep the
expiry mechanism alive.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from _helpers import import_script, run_json, run_script

posting = import_script("posting-time-analyzer.py")
sendtime = import_script("send-time-optimizer.py")


def _write_json(payload):
    fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8")
    json.dump(payload, fh)
    fh.close()
    return fh.name


def make_post_history(weeks=10):
    """Synthetic history with an unambiguous Wednesday-morning peak."""
    base = datetime(2026, 5, 4)
    entries = []
    for week in range(weeks):
        for wd, hr, eng in [(2, 10, 400), (2, 11, 390), (4, 16, 200),
                            (0, 9, 150), (5, 10, 170), (2, 9, 380)]:
            ts = base + timedelta(days=week * 7 + wd, hours=hr)
            entries.append({"posted_at": ts.isoformat(), "engagement": eng})
    return entries


class TestPostingTimeLadder(unittest.TestCase):
    def test_first_party_wins_and_finds_the_real_peak(self):
        path = _write_json(make_post_history())
        try:
            data, rc = run_json("posting-time-analyzer.py",
                                "--platform", "instagram", "--history", path)
        finally:
            Path(path).unlink(missing_ok=True)
        self.assertEqual(rc, 0)
        self.assertEqual(data["basis"], "first-party")
        top = data["recommendations"][0]
        self.assertEqual(top["day"], "Wednesday")
        self.assertGreaterEqual(top["sample_size"], posting.MIN_BUCKET_POSTS)
        self.assertIn("total_posts_analyzed", data)

    def test_thin_history_falls_back_with_explanation(self):
        path = _write_json(make_post_history(weeks=1))  # 6 posts < 30
        try:
            data, rc = run_json("posting-time-analyzer.py",
                                "--platform", "instagram", "--history", path)
        finally:
            Path(path).unlink(missing_ok=True)
        self.assertEqual(rc, 0)
        self.assertEqual(data["basis"], "population-baseline")
        self.assertIn("first_party_insufficient", data)

    def test_baseline_carries_stamp_ceiling_and_relative_strength(self):
        data, rc = run_json("posting-time-analyzer.py", "--platform", "linkedin",
                            "--industry", "saas", "--audience-type", "b2b")
        self.assertEqual(rc, 0)
        self.assertEqual(data["basis"], "population-baseline")
        self.assertEqual(data["baseline_as_of"], posting.BASELINE_AS_OF)
        self.assertIn("medium", data["confidence_ceiling"])
        for rec in data["recommendations"]:
            self.assertIn("relative_strength", rec)
            self.assertNotIn("confidence", rec,
                             "baseline recs must not claim absolute confidence")

    def test_every_platform_has_an_algorithm_note(self):
        for platform in posting.PLATFORM_BENCHMARKS:
            self.assertIn(platform, posting.ALGORITHM_NOTES,
                          f"{platform} lacks a 2026 algorithm note")

    def test_baseline_status_ages_out(self):
        old = (datetime.now() - timedelta(days=200)).strftime("%Y-%m-%d")
        ancient = (datetime.now() - timedelta(days=600)).strftime("%Y-%m-%d")
        self.assertEqual(posting.baseline_status(posting.BASELINE_AS_OF)[0], "fresh")
        self.assertEqual(posting.baseline_status(old)[0], "aging")
        self.assertEqual(posting.baseline_status(ancient)[0], "stale")

    def test_shipped_stamp_is_not_already_stale(self):
        """Self-aging release gate: when the shipped BASELINE_AS_OF exceeds the
        warn window, this fails and the tables must be re-verified. That red
        build is the feature."""
        status, age = posting.baseline_status()
        self.assertNotEqual(status, "stale",
                            f"posting baseline is {age} days old — re-verify the tables")
        if status == "aging":
            print(f"[timing-ladder] posting baseline {age} days old — refresh soon")


class TestSendTimeLadder(unittest.TestCase):
    def _history(self, weeks=8):
        base = datetime(2026, 4, 6)
        entries = []
        for week in range(weeks):
            for wd, hr, rate in [(1, 10, 0.31), (3, 14, 0.22), (1, 9, 0.28)]:
                ts = base + timedelta(days=week * 7 + wd, hours=hr)
                entries.append({"sent_at": ts.isoformat(),
                                "opens": int(5000 * rate), "recipients": 5000})
        return entries

    def test_first_party_ranks_by_open_rate(self):
        path = _write_json(self._history())
        try:
            data, rc = run_json("send-time-optimizer.py", "--industry", "saas",
                                "--audience-type", "b2b", "--history", path)
        finally:
            Path(path).unlink(missing_ok=True)
        self.assertEqual(rc, 0)
        self.assertEqual(data["basis"], "first-party")
        top = data["recommendations"][0]
        self.assertEqual(top["day"], "Tuesday")
        self.assertIn("open_rate", top)
        self.assertIn("sample_size", top)

    def test_thin_send_log_falls_back_with_explanation(self):
        path = _write_json(self._history(weeks=2))  # 6 sends < 12
        try:
            data, rc = run_json("send-time-optimizer.py", "--industry", "saas",
                                "--audience-type", "b2b", "--history", path)
        finally:
            Path(path).unlink(missing_ok=True)
        self.assertEqual(rc, 0)
        self.assertEqual(data["basis"], "population-baseline")
        self.assertIn("first_party_insufficient", data)

    def test_every_output_carries_the_sto_doctrine(self):
        data, rc = run_json("send-time-optimizer.py", "--industry", "ecommerce",
                            "--audience-type", "b2c")
        self.assertEqual(rc, 0)
        self.assertIn("per-recipient", data["sto_note"])
        self.assertEqual(data["baseline_as_of"], sendtime.BASELINE_AS_OF)
        for rec in data["recommendations"]:
            self.assertIn("relative_strength", rec)

    def test_timezone_adjustment_still_works(self):
        data, rc = run_json("send-time-optimizer.py", "--industry", "saas",
                            "--audience-type", "b2b", "--timezone", "+5")
        self.assertEqual(rc, 0)
        self.assertIn("adjusted", data["timezone"])

    def test_shipped_stamp_is_not_already_stale(self):
        status, age = sendtime.baseline_status()
        self.assertNotEqual(status, "stale",
                            f"send-time baseline is {age} days old — re-verify the tables")
        if status == "aging":
            print(f"[timing-ladder] send-time baseline {age} days old — refresh soon")

    def test_missing_history_file_errors_cleanly(self):
        proc = run_script("send-time-optimizer.py", "--industry", "saas",
                          "--audience-type", "b2b", "--history", "no-such-file.json")
        self.assertEqual(proc.returncode, 1)


if __name__ == "__main__":
    unittest.main()
