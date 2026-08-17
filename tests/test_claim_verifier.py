"""Guards for claim-verifier.py extraction (GitHub issue #10).

The percentage pattern ended in `%\\b` — and because "%" is a non-word
character, that \\b only matched when a WORD character followed the "%".
Net effect: "98%x" was a claim while "98% of customers", "98%." and a
percentage at end-of-line were invisible — the common cases failed and the
typo case passed. These tests pin the corrected behaviour through the real
CLI (`--action extract-claims`), the path a real caller uses.
"""
from __future__ import annotations

import unittest

from _helpers import run_json


def _extract(text: str) -> list[dict]:
    data, rc = run_json("claim-verifier.py", "--action", "extract-claims", "--text", text)
    assert rc == 0, data
    return data["claims"]


def _percentages(text: str) -> list[str]:
    return [c["text"] for c in _extract(text) if c["type"] == "percentage"]


class TestPercentageExtraction(unittest.TestCase):
    def test_percent_followed_by_space(self):
        # The issue's headline repro: this returned 0 claims before the fix.
        self.assertEqual(_percentages("98% of customers saw results"), ["98%"])

    def test_percent_followed_by_punctuation(self):
        self.assertEqual(_percentages("Customer satisfaction reached 98%."), ["98%"])

    def test_percent_at_end_of_text(self):
        self.assertEqual(_percentages("Retention is now 91%"), ["91%"])

    def test_decimal_percent(self):
        self.assertEqual(_percentages("Churn fell to 2.5% overall"), ["2.5%"])

    def test_percent_glued_to_word_char_is_not_a_claim(self):
        # The ONLY case the old pattern matched — a typo, not a claim.
        self.assertEqual(_percentages("98%x is malformed"), [])

    def test_percentage_change_still_wins_over_bare_percentage(self):
        claims = _extract("Revenue grew 45% year over year")
        types = {c["type"] for c in claims}
        self.assertIn("percentage_change", types)

    def test_multiple_percentages_in_one_text(self):
        self.assertEqual(
            _percentages("98% of customers stayed; NPS response rate was 62%"),
            ["98%", "62%"])


if __name__ == "__main__":
    unittest.main()
