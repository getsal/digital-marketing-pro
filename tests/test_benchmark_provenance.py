"""Market-priced figures in skill docs must carry provenance, and it must not rot.

The disease this prevents: "LinkedIn CPMs are high ($30–$60)" written as
timeless fact. Auction prices drift; an undated range becomes a confident lie.
The cure is not deleting the numbers — order-of-magnitude priors are genuinely
useful for planning — it is stamping them:

  * Any skills/ doc whose lines pair a $ figure with a market-metric token
    (CPM, CPC, CPL, ...) or a subscription price ($N/mo) must carry a
    "Benchmark provenance (as of YYYY-MM)" banner that routes commitments
    through scripts/benchmark_book.py.
  * The banner's stamp AGES OUT: older than {WARN_MONTHS} months prints a
    refresh warning at test time; older than {FAIL_MONTHS} months FAILS the
    suite. A red test is the point — benchmark rot becomes visible at release
    time instead of living silently in a doc nobody rereads.

Deliberately NOT flagged: strategy budget bands, survey incentives, legal
penalty ranges, and worked-example dialog — those are either structural or
clearly illustrative. Files where every hit is illustrative are exempted BY
NAME below with the reason.
"""
from __future__ import annotations

import re
import unittest
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills"

WARN_MONTHS = 6
FAIL_MONTHS = 15

# A market-metric token in the same line as a dollar figure = a market-priced
# claim. Tokens are matched uppercase, as the docs write them; vCPM/CPCV etc.
# are covered by the CPM/CPV stems inside them.
METRIC_TOKEN = re.compile(r"\b(?:v?CPM|CPC[V]?|CPL|CPA|CPE|CPV|CPI)\b")
DOLLAR = re.compile(r"\$\d")
# Subscription pricing: "$49-$125/mo", "$500–$1,000/month"
SUBSCRIPTION = re.compile(r"\$[\d,.]+(?:\s*[–—-]\s*\$?[\d,.]+)?\s*\+?/\s*mo", re.I)
# Creator rate cards: "$50–$250 per post"
PER_POST = re.compile(r"\$[\d,.Kk+]+(?:\s*[–—-]\s*\$?[\d,.Kk+]+)?\s*(?:per post|/post)", re.I)

# Rate-card tables whose lines carry no metric token (the column header names
# the unit), so the line scanner cannot see them. Pinned by name: these must
# carry the banner regardless of what the scanner finds.
RATE_CARD_FILES = {
    "influencer-creator/contract-frameworks.md",
    "influencer-creator/influencer-discovery.md",
}

BANNER = re.compile(r"\*\*Benchmark provenance \(as of (\d{4})-(\d{2})\):\*\*")

# Every hit in these files is a quoted worked example or an example goal, not a
# market-rate table. Keep this list short and honest — a file with real
# benchmark tables does not belong here.
EXEMPT = {
    # "$85 CPA … $22 CPA" inside an illustrative reallocation message
    "budget-tracker/SKILL.md",
    # "$2.40 … $3.00" CPC inside a quoted example of anonymized benchmarking
    "context-engine/agency-operations-guide.md",
    # "$50 CPL benchmark" as a SMART-goal phrasing example (routed to brand
    # history / benchmark book in the surrounding text)
    "campaign-orchestrator/campaign-planning.md",
    # "$500/month threshold" is the documented default of a CLI flag, not market data
    "campaign-audit/SKILL.md",
    # "$85 AOV = $2,975,000 abandoned/month" — worked arithmetic example
    "cro/checkout-optimization.md",
    # "~~$99/mo~~ $79/mo" etc. — price-DISPLAY formatting patterns, all illustrative
    "cro/pricing-psychology.md",
    # "Example: If target CPA = $50" — explicitly labeled example
    "paid-advertising/bid-strategy.md",
    # example CLV/CAC segmentation table illustrating the framework, not market rates
    "analytics-insights/clv-analysis.md",
}


def market_priced_lines(text: str) -> list[str]:
    hits = []
    for line in text.splitlines():
        if ((DOLLAR.search(line) and METRIC_TOKEN.search(line))
                or SUBSCRIPTION.search(line) or PER_POST.search(line)):
            hits.append(line.strip()[:120])
    return hits


def files_in_scope():
    for f in sorted(SKILLS.rglob("*.md")):
        rel = f.relative_to(SKILLS).as_posix()
        text = f.read_text(encoding="utf-8", errors="replace")
        hits = market_priced_lines(text)
        if rel in RATE_CARD_FILES and not hits:
            hits = ["<rate-card table pinned by name>"]
        if hits:
            yield rel, text, hits


class TestBenchmarkProvenance(unittest.TestCase):
    def test_every_market_priced_doc_carries_the_banner(self):
        missing = []
        for rel, text, hits in files_in_scope():
            if rel in EXEMPT:
                continue
            if not BANNER.search(text):
                missing.append(f"{rel} ({len(hits)} market-priced lines, e.g. {hits[0]!r})")
        self.assertEqual(missing, [],
                         "Docs with market-priced figures but no provenance banner "
                         "(add the 'Benchmark provenance (as of YYYY-MM)' banner or, if every "
                         "hit is illustrative, exempt the file BY NAME with a reason):\n  "
                         + "\n  ".join(missing))

    def test_banner_references_the_book(self):
        bad = []
        for rel, text, _ in files_in_scope():
            if rel in EXEMPT:
                continue
            if BANNER.search(text) and "benchmark_book.py" not in text:
                bad.append(rel)
        self.assertEqual(bad, [], "Banner present but does not route refreshes through "
                                  "benchmark_book.py:\n  " + "\n  ".join(bad))

    def test_banner_stamps_age_out(self):
        """Stamps older than FAIL_MONTHS fail; older than WARN_MONTHS warn.
        This test is SUPPOSED to go red as time passes — that is the feature."""
        today = date.today()
        expired, warnings = [], []
        for rel, text, _ in files_in_scope():
            m = BANNER.search(text)
            if not m:
                continue
            year, month = int(m.group(1)), int(m.group(2))
            age_months = (today.year - year) * 12 + (today.month - month)
            if age_months > FAIL_MONTHS:
                expired.append(f"{rel} (stamped {year}-{month:02d}, {age_months} months old)")
            elif age_months > WARN_MONTHS:
                warnings.append(f"{rel} (stamped {year}-{month:02d}, {age_months} months old)")
        for w in warnings:
            print(f"[benchmark-provenance] refresh soon: {w}")
        self.assertEqual(expired, [],
                         "Provenance stamps older than %d months — re-verify the figures "
                         "against live sources and re-stamp:\n  " % FAIL_MONTHS
                         + "\n  ".join(expired))

    def test_known_benchmark_docs_are_in_scope(self):
        """Regression pins: if the scanner weakens, these three must still be
        caught — they are the canonical market-rate carriers."""
        in_scope = {rel for rel, _, _ in files_in_scope()}
        for pin in ("paid-advertising/linkedin-ads.md",
                    "influencer-creator/micro-influencer-strategy.md",
                    "context-engine/industry-profiles.md"):
            self.assertIn(pin, in_scope,
                          f"{pin} no longer flagged by the scanner — the scanner regressed, "
                          "not the doc.")

    def test_exempt_files_still_exist(self):
        for rel in EXEMPT:
            self.assertTrue((SKILLS / rel).exists(),
                            f"EXEMPT entry {rel} no longer exists — prune the list.")

    # ── plant checks: the scanner itself ────────────────────────────

    def test_scanner_flags_planted_metric_line(self):
        self.assertTrue(market_priced_lines("| CPM | $30–$60 | high |"))
        self.assertTrue(market_priced_lines("Expect $30–$150 CPL depending on offer"))
        self.assertTrue(market_priced_lines("| **Jasper** | ... | $49-$125/mo |"))

    def test_scanner_ignores_structural_dollars(self):
        self.assertFalse(market_priced_lines("- **Budget**: $5,000-$25,000 per account/year"))
        self.assertFalse(market_priced_lines("| B2C customers | Gift card | $5-$25 per response |"))
        self.assertFalse(market_priced_lines("$2,500 per unintentional violation"))


if __name__ == "__main__":
    unittest.main()
