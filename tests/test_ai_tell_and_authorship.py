"""The humanize gate stops being a vibe, and the author stays in the piece.

Before this, `humanize_passed` asked for "AI-pattern density below the brand
threshold (under 10% of paragraphs flagged)" while nothing in the repo defined
what a flag was — no catalog, no agent, no script. A gate whose measurement is
undefined does not fail; it passes on impression.

These tests pin the replacement and, just as importantly, its restraint:

  * only the tells precise enough to gate on count toward the gate, because
    the aphorism heuristic alone flagged half the paragraphs of genuinely good
    hand-written copy — and `llm_favored_word` was later measured firing ONLY
    on prose published before ChatGPT existed, so it was dropped from the gate
    too;
  * absolute floors stop a single legitimate "actually" in a short piece from
    normalizing into a tell;
  * significance markers are DELETED, never reworded;
  * author sentences are exempt from every tell and may not be paraphrased;
  * the authored disclosure can only ever understate human involvement.

Nothing here targets a detector and no test asserts a "human enough" score.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ats = _load("dmp_ai_tell_scan", "ai-tell-scan.py")
sts = _load("dmp_structural_scan_2", "structural-tell-scan.py")
auth = _load("dmp_authorship", "authorship.py")

CONTENT_ENGINE = (REPO / "skills" / "content-engine" / "SKILL.md").read_text(encoding="utf-8")
CHECK = (REPO / "skills" / "check" / "SKILL.md").read_text(encoding="utf-8")

# Unedited model prose: banned lexicon, a significance marker, adverb cluster.
AI_COPY = """# The guide

## Understanding the basics

In today's landscape, businesses must delve into the intricate tapestry of modern
marketing. Here's the thing, that is the part that really matters. Leveraging
seamless solutions is pivotal.

Moreover, organizations should harness robust frameworks. It was genuinely a
quietly remarkable shift.

## What we measured

Approvals slipped from 14 days to 31 days in the Bavaria cohort during 2024.
"""

# Hand-written copy: specific, grounded, and carrying the short declaratives
# and plain connectives that real marketing writing carries.
HUMAN_COPY = """# Why our agency review estimates were wrong for two years

## The 14-day number came from a 2019 sample

We quoted 14 days for regulatory review because that is what the Fraunhofer
benchmark said in 2019. Nobody on the team had checked it since. When a client in
Bavaria missed a launch window last March, we pulled the current figures and found
the authors had revised the number twice.

The revised Fraunhofer median for Bavaria is 31 days. That correction changed how
we scope every submission we take.

## What Kessler Partners found

Kessler Partners audited the Bavaria cohort in 2024 and landed within a day of
Fraunhofer, at 30 days. Two methods, two teams, nearly the same answer. Saxony
behaved differently, holding near 18 days across the same period, which is why a
national average would have hidden the problem.

Reviewers in Bavaria told Kessler Partners the backlog came from staffing, and
payroll records supported them: the office lost eleven reviewers between 2023 and
2025 and replaced four.
"""

AUTHOR_SOURCE = """ok so the thing that killed us was the 14 day estimate. we quoted it for two years and nobody checked.
i found out in march when the bavaria client missed their launch window.
turns out fraunhofer revised it twice and we never noticed, its 31 days now not 14.
we lost about 40k in rework on that one account alone.
"""

DRAFT_PRESERVED = """# Why our review estimates were wrong

ok so the thing that killed us was the 14 day estimate. we quoted it for two years and nobody checked.

The figure came from a 2019 Fraunhofer benchmark nobody on the team had revisited.

i found out in march when the bavaria client missed their launch window.

Kessler Partners audited the same Bavaria cohort in 2024 and landed at 30 days.

turns out fraunhofer revised it twice and we never noticed, its 31 days now not 14.

we lost about 40k in rework on that one account alone.
"""

DRAFT_LAUNDERED = """# Why our review estimates were wrong

The critical issue was the 14-day estimate. We quoted it for two years, and nobody verified it.

The figure came from a 2019 Fraunhofer benchmark nobody on the team had revisited.

I discovered this in March, when the Bavaria client missed their launch window.

turns out fraunhofer revised it twice and we never noticed, its 31 days now not 14.
"""


class TestTheGateMeasuresSomething(unittest.TestCase):
    def test_ai_copy_fails_the_humanize_gate(self):
        r = ats.ai_tell_scan(AI_COPY)
        self.assertFalse(r["humanize_passed"])
        self.assertGreater(r["flagged_paragraph_pct"], 10.0)

    def test_human_copy_passes_the_humanize_gate(self):
        """The regression that matters most. A gate that fails hand-written
        copy is worse than the undefined gate it replaced, because it sends
        the pipeline into rewrite loops on work that was already good."""
        r = ats.ai_tell_scan(HUMAN_COPY)
        self.assertTrue(r["humanize_passed"],
                        f"human copy flagged at {r['flagged_paragraph_pct']}%: "
                        f"{[p['gating_tells'] for p in r['flagged_paragraphs']]}")
        self.assertEqual(r["flagged_paragraph_pct"], 0.0)

    def test_gate_counts_only_the_precise_tells(self):
        self.assertEqual(ats._GATING_TELLS,
                         {"significance_marker", "soft_adverb_cluster"})

    def test_llm_favored_words_do_not_gate(self):
        """Measured 2026-08-15 against 272 chunks of prose published before
        ChatGPT existed: 23 words from the list fired, every one of them ONLY
        on the human class and none on the LLM class. "robust", "facilitate",
        "harness" and "leverage" are ordinary technical English, while current
        models have largely been trained off them. As a gating signal it could
        only ever produce false positives.

        It must still be REPORTED — it is sound editorial advice for marketing
        copy — but it must never move the gate. If a future edit puts it back,
        this test is the record of why that is wrong."""
        self.assertNotIn("llm_favored_word", ats._GATING_TELLS)
        text = ("# T\n\nWe will leverage a robust framework to facilitate the "
                "rollout across the landscape of our estate. This will harness "
                "the platform and unlock a myriad of seamless outcomes.\n")
        r = ats.ai_tell_scan(text)
        self.assertTrue(r["humanize_passed"],
                        "llm-favored vocabulary alone must not fail the gate")
        flagged = [p for p in r["flagged_paragraphs"] if "llm_favored_word" in p["tells"]]
        self.assertTrue(flagged, "llm-favored words must still be reported to the editor")
        self.assertFalse(flagged[0]["counts_toward_gate"])

    def test_the_gate_does_not_claim_to_prove_humanness(self):
        """The gate is a density floor. Measured on 18 documents of default LLM
        prose it caught 0 — it would not catch a humanizer that silently did
        nothing. The advisory_note must not imply otherwise, because a gate
        that overstates what it proves is the same defect as a gate with no
        measurement behind it, just harder to notice."""
        note = ats.ai_tell_scan("# T\n\nA short factual paragraph about nothing.\n")["advisory_note"]
        low = note.lower()
        for overclaim in ("proves", "guarantees", "confirms human", "human-written",
                          "detects ai", "ai-generated"):
            self.assertNotIn(overclaim, low, f"advisory_note overclaims: {overclaim!r}")
        self.assertIn("floor", low,
                      "advisory_note should say plainly that the gate is a floor")

    def test_imprecise_tells_are_reported_but_do_not_gate(self):
        """Short declaratives and 'So,' openers stay visible to an editor
        without counting against the gate."""
        r = ats.ai_tell_scan(HUMAN_COPY)
        advisory_only = [p for p in r["flagged_paragraphs"] if not p["counts_toward_gate"]]
        self.assertTrue(advisory_only, "advisory tells should still be surfaced")
        for p in advisory_only:
            self.assertEqual(p["gating_tells"], [])

    def test_threshold_is_overridable_per_brand(self):
        strict = ats.ai_tell_scan(AI_COPY, max_flagged_pct=0.0)
        loose = ats.ai_tell_scan(AI_COPY, max_flagged_pct=100.0)
        self.assertFalse(strict["humanize_passed"])
        self.assertTrue(loose["humanize_passed"])

    def test_bands_use_one_vocabulary(self):
        for text in (AI_COPY, HUMAN_COPY):
            r = ats.ai_tell_scan(text)
            for metric, band in r["bands"].items():
                self.assertIn(band, ("LOW", "MODERATE", "HIGH"),
                              f"{metric} reported {band!r}, outside the band vocabulary")
            self.assertIn(r["advisory_rating"], ("LOW", "MODERATE", "HIGH"))


class TestSignificanceMarkers(unittest.TestCase):
    def test_marker_is_flagged_with_a_delete_instruction(self):
        r = ats.ai_tell_scan(AI_COPY)
        hits = [f for f in r["flagged_sentences"] if f["tell"] == "significance_marker"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["phrase"], "here's the thing")
        self.assertIn("Delete", hits[0]["fix"])
        self.assertIn("do not reword", hits[0]["fix"].lower())

    def test_curly_apostrophe_does_not_evade(self):
        r = ats.ai_tell_scan("The backlog doubled in Bavaria. Here’s the thing, it matters.")
        self.assertEqual(r["counts"]["significance_markers"], 1)

    def test_literal_prose_is_not_flagged(self):
        """'that's the part' and 'the thing is' have ordinary literal senses.
        A scan that cries wolf on plain prose gets ignored."""
        for text in (
            "Section 4 covers reviewer staffing. That's the part of the rule that changed.",
            "The instrument arrived damaged. The thing is broken beyond repair.",
        ):
            with self.subTest(text=text[:40]):
                self.assertEqual(ats.ai_tell_scan(text)["counts"]["significance_markers"], 0)


class TestAbsoluteFloors(unittest.TestCase):
    """Short pieces must not have tells manufactured out of arithmetic."""

    def test_one_soft_adverb_in_a_short_piece_does_not_band(self):
        text = "We asked five customers why they actually bought it, and recorded every call."
        r = ats.ai_tell_scan(text)
        self.assertGreater(r["per_1000_words"]["soft_adverb_tags_per_1000"], 4.0,
                           "sanity: the per-1000 figure should look alarming")
        self.assertEqual(r["bands"]["soft_adverb_tags_per_1000"], "LOW",
                         "one earned adverb must not band as a tell")

    def test_floors_are_declared_for_the_small_sample_metrics(self):
        for metric in ("significance_markers_per_1000", "soft_adverb_tags_per_1000",
                       "aphorism_candidates_per_1000"):
            self.assertIn(metric, ats._FLOORS)


class TestEntityDevelopment(unittest.TestCase):
    CHURN = "# Report\n\n## Findings\n\n" + " ".join(
        f"The {n} team logged a shift that quarter and staff there noted the change soon afterwards. "
        f"Analysts called the pattern broadly consistent with the prior period across that whole region. "
        f"Nobody involved disputed the summary that was circulated to the group later that same month. "
        for n in ("Fraunhofer", "Siemens", "Duisburg", "Stuttgart", "Hoffmann", "Weber",
                  "Leipzig", "Kessler", "Hannover", "Baumann", "Dortmund", "Vogel",
                  "Essen", "Bremen", "Aachen", "Kiel", "Rostock", "Ulm", "Trier", "Jena"))

    def test_finding_exists_in_the_structural_scan(self):
        self.assertIn("entity_development", sts.structure_scan(HUMAN_COPY)["findings"])

    def test_churn_fires_on_a_long_undeveloped_piece(self):
        f = sts.structure_scan(self.CHURN)["findings"]["entity_development"]
        self.assertTrue(f["measurable"])
        self.assertEqual(f["band"], "ATTENTION")

    def test_short_piece_is_not_banded(self):
        f = sts.structure_scan(HUMAN_COPY)["findings"]["entity_development"]
        self.assertFalse(f["measurable"])
        self.assertEqual(f["band"], "OK")

    def test_meaning_forbids_fixing_by_deletion(self):
        m = sts.structure_scan(self.CHURN)["findings"]["entity_development"]["meaning"].lower()
        self.assertIn("never by deleting", m)
        self.assertIn("forbidden", m)

    def test_thresholds_stay_out_of_scored_configs(self):
        self.assertIn("mentions_per_entity", sts._BANDS)
        for cfg in REPO.glob("config/**/*.json"):
            self.assertNotIn("mentions_per_entity", cfg.read_text(encoding="utf-8"),
                             f"structural threshold leaked into {cfg}")


class TestAuthorshipPreservation(unittest.TestCase):
    def test_preserved_draft_has_no_violations(self):
        r = auth.classify(AUTHOR_SOURCE, DRAFT_PRESERVED)
        self.assertEqual(r["violations"]["author_sentences_rewritten"], 0)
        self.assertEqual(r["violations"]["author_sentences_dropped"], 0)

    def test_paraphrasing_the_author_is_caught(self):
        r = auth.classify(AUTHOR_SOURCE, DRAFT_LAUNDERED)
        self.assertGreaterEqual(r["violations"]["author_sentences_rewritten"], 2)
        self.assertGreaterEqual(r["violations"]["author_sentences_dropped"], 1)

    def test_script_exit_codes(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            src = td / "source.md"
            src.write_text(AUTHOR_SOURCE, encoding="utf-8")
            for name, body, expected in (("good", DRAFT_PRESERVED, 0),
                                         ("bad", DRAFT_LAUNDERED, 3)):
                d = td / f"{name}.md"
                d.write_text(body, encoding="utf-8")
                proc = subprocess.run(
                    [sys.executable, str(SCRIPTS / "authorship.py"),
                     "--source", str(src), "--draft", str(d)],
                    capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(proc.returncode, expected, f"{name}: {proc.stderr[:200]}")

    def test_authored_claim_requires_clean_record_and_a_real_share(self):
        self.assertTrue(auth.classify(AUTHOR_SOURCE, DRAFT_PRESERVED)["may_claim_authored"])
        self.assertFalse(auth.classify(AUTHOR_SOURCE, DRAFT_LAUNDERED)["may_claim_authored"])
        self.assertFalse(auth.classify("", DRAFT_PRESERVED)["may_claim_authored"])

    def test_repeating_an_author_line_cannot_inflate_their_share(self):
        padded = DRAFT_PRESERVED + "\n\n" + ("we lost about 40k in rework on that one account alone.\n\n" * 4)
        self.assertEqual(auth.classify(AUTHOR_SOURCE, padded)["counts"]["author_verbatim"], 5)


class TestSkillWiring(unittest.TestCase):
    def test_humanize_gate_names_the_script(self):
        self.assertIn("ai-tell-scan.py", CONTENT_ENGINE)
        self.assertIn("do not judge this by eye", CONTENT_ENGINE.lower())

    def test_content_engine_documents_what_gates_and_what_does_not(self):
        self.assertIn("advisory context, not gate material", CONTENT_ENGINE)

    def test_content_engine_teaches_delete_not_reword(self):
        self.assertIn("DELETE the sentence. Do not reword it.", CONTENT_ENGINE)

    def test_content_engine_carries_the_source_draft_mode(self):
        for token in ("--source-draft", "00-source-draft.md", "authorship.py",
                      "may_claim_authored", "the mess is the signal"):
            self.assertIn(token, CONTENT_ENGINE)

    def test_author_sentences_are_exempt_from_the_tells(self):
        self.assertIn("do not apply to their sentences", CONTENT_ENGINE)

    def test_author_claims_are_not_verified_facts(self):
        self.assertIn("their voice, not verified facts", CONTENT_ENGINE)

    def test_entity_fix_direction_is_documented(self):
        self.assertIn("Fix by developing, never by deleting", CONTENT_ENGINE)

    def test_check_reports_both_tiers_and_never_scores_them(self):
        self.assertIn("ai-tell-scan.py", CHECK)
        self.assertIn("structural-tell-scan.py", CHECK)
        self.assertIn("NEVER affects the PASS/WARN/BLOCKED decision", CHECK)


class TestNoEvasionSurface(unittest.TestCase):
    """This work was mined from a detector-evasion skill. None of that came
    with it, and this guard exists so none of it arrives later."""

    FILES = [SCRIPTS / "ai-tell-scan.py", SCRIPTS / "authorship.py",
             SCRIPTS / "structural-tell-scan.py",
             REPO / "skills" / "content-engine" / "SKILL.md"]
    FORBIDDEN = ("zero-width", "homoglyph", "watermark removal", "remove the watermark",
                 "strip the watermark", "bypass the detector", "evade detection",
                 "pass as human", "discourse fracture")

    def test_no_evasion_technique_appears(self):
        offenders = []
        for path in self.FILES:
            low = path.read_text(encoding="utf-8").lower()
            offenders += [f"{path.name}: {t}" for t in self.FORBIDDEN if t in low]
        self.assertEqual(offenders, [], f"evasion surface introduced: {offenders}")

    def test_scans_disclaim_any_watermark_relationship(self):
        for path in (SCRIPTS / "ai-tell-scan.py", SCRIPTS / "structural-tell-scan.py"):
            self.assertIn("no relationship to any statistical watermark",
                          path.read_text(encoding="utf-8"))

    def test_authorship_disclaims_being_a_detector_tool(self):
        src = (SCRIPTS / "authorship.py").read_text(encoding="utf-8").lower()
        self.assertIn("not a detector-evasion tool", src)
        self.assertIn("no target ratio", src)


class TestSelfContainment(unittest.TestCase):
    """DMP never delegates a capability to a sibling plugin."""

    def test_new_scripts_do_not_reference_sibling_plugins(self):
        for name in ("ai-tell-scan.py", "authorship.py"):
            text = (SCRIPTS / name).read_text(encoding="utf-8").lower()
            for sibling in ("contentforge", "socialforge"):
                self.assertNotIn(sibling, text, f"{name} references {sibling}")


if __name__ == "__main__":
    unittest.main()


class TestAphorismProxyIsCalibrated(unittest.TestCase):
    """Field-test findings, 2026-08-14. Measured against a published human essay
    AND against this plugin's own generated article, the <=9-word heuristic
    flagged ordinary factual sentences ("The neighbouring region barely moved.")
    and rated both HIGH. A proxy that cannot tell a maxim from a short fact must
    not headline the rating."""

    def test_self_contained_maxims_still_flagged(self):
        for s in ("Speed wins the shelf.", "Strong brands design the data to travel.",
                  "The future looks bright."):
            with self.subTest(s=s):
                self.assertTrue(ats.is_aphorism_candidate(s))

    def test_context_dependent_sentences_are_not_maxims(self):
        for s in ("That is what you are looking for.", "The next step is to notice them.",
                  "I decided to find out by making it.", "But pick something and get going.",
                  "And that is not all."):
            with self.subTest(s=s):
                self.assertFalse(ats.is_aphorism_candidate(s))

    def test_aphorisms_do_not_drive_the_advisory_rating(self):
        maxims = "\n\n".join(["Speed wins the shelf. Quality matters above all else."] * 12)
        r = ats.ai_tell_scan(maxims)
        self.assertGreater(r["per_1000_words"]["aphorism_candidates_per_1000"], 30,
                           "sanity: fixture should be dense with maxims")
        self.assertEqual(r["bands"]["aphorism_candidates_per_1000"], "HIGH",
                         "the band is still computed and reported")
        self.assertEqual(r["advisory_rating"], "LOW",
                         "aphorism density alone must not raise the rating")

    def test_real_human_writing_passes_the_gate_and_rates_calmly(self):
        """The regression that matters: good prose must not read as AI."""
        r = ats.ai_tell_scan(HUMAN_COPY)
        self.assertTrue(r["humanize_passed"])
        self.assertIn(r["advisory_rating"], ("LOW", "MODERATE"))


class TestRobustnessAndPerformance(unittest.TestCase):
    """Found by adversarial load testing, 2026-08-14. The all-pairs authorship
    matcher was quadratic (11.4s at 500 sentences) and its prefilter pruned
    nothing when the draft genuinely contained the author's sentences."""

    ADVERSARIAL = {
        "empty": "", "whitespace": "   \n\n\t ", "single_char": "x",
        "no_punctuation": "this never ends",
        "unicode": "# 🎯 Résumé\n\nLe café naïve 日本語 Ελληνικά مرحبا\n",
        "rtl": "# שלום\n\nזהו טקסט עם 31 ו-14.\n",
        "cjk": "# 標題\n\n這是一段中文文字。第二句話。\n",
        "malformed_frontmatter": "---\ntitle: unterminated\n\n# H\n\nBody.\n",
        "unclosed_fence": "# D\n\n```py\nprint(1)\n\nAfter.\n",
        "null_bytes": "# D\x00\n\nText \x00 here.\n",
        "html": "# <script>alert(1)</script>\n\n<img src=x onerror=y>\n",
        "windows_newlines": "# D\r\n\r\nA line.\r\nAnother.\r\n",
        "only_punctuation": "... !!! ??? ---\n",
    }

    def test_scans_never_crash_on_adversarial_input(self):
        for name, text in self.ADVERSARIAL.items():
            with self.subTest(case=name):
                a = ats.ai_tell_scan(text)
                s = sts.structure_scan(text)
                self.assertIn(a["advisory_rating"], ("LOW", "MODERATE", "HIGH"))
                self.assertIn(s["overall"], ("OK", "NOTE", "ATTENTION"))
                self.assertIsInstance(a["humanize_passed"], bool)
                for f in s["findings"].values():
                    self.assertIn(f["band"], ("OK", "NOTE", "ATTENTION"))

    def test_authorship_never_crashes_on_adversarial_input(self):
        for name, text in self.ADVERSARIAL.items():
            with self.subTest(case=name):
                r = auth.classify(text, text)
                self.assertEqual(r["violations"]["author_sentences_rewritten"], 0)
                auth.classify(text, "")
                auth.classify("", text)

    def test_authorship_is_not_quadratic(self):
        import time
        big = "The Fraunhofer report tracked review delays across Bavaria in 2024. " * 5000
        start = time.time()
        r = auth.classify(big, big)
        elapsed = time.time() - start
        self.assertEqual(r["counts"]["author_verbatim"], 5000)
        self.assertLess(elapsed, 5.0,
                        f"authorship matching took {elapsed:.1f}s on 5000 sentences — "
                        "the quadratic all-pairs behaviour has returned")

    def test_scan_output_is_deterministic_in_process(self):
        blobs = {json.dumps(ats.ai_tell_scan(HUMAN_COPY), sort_keys=True) for _ in range(5)}
        self.assertEqual(len(blobs), 1, "ai_tell_scan output varies between identical runs")


class TestScanOutputMustNotLandInTheMeasuredFile(unittest.TestCase):
    """The content-engine used to say "append the scan JSON to 05-humanize.md"
    while ALSO running `authorship.py --draft 05-humanize.md` against that same
    file. authorship.py classifies every sentence in the draft, so following
    both instructions diluted the author's share with the tool's own output.

    Measured on a real humanizer run: appending a report and the scan JSON moved
    author_word_share 0.253 -> 0.206 and flipped may_claim_authored true ->
    false. Violations stayed clean throughout, which is why the defect was
    invisible to the check that was supposed to catch problems.
    """

    SKILL = Path(__file__).resolve().parent.parent / "skills" / "content-engine" / "SKILL.md"

    def test_skill_no_longer_appends_scan_output_to_the_draft(self):
        text = self.SKILL.read_text(encoding="utf-8")
        self.assertNotIn("Append the scan JSON to `05-humanize.md`", text)
        self.assertNotIn("paste its JSON into `05-humanize.md`", text)

    def test_skill_names_a_separate_destination(self):
        text = self.SKILL.read_text(encoding="utf-8")
        self.assertIn("05-scans.json", text,
                      "scan output needs its own file, or it lands in the measured draft")

    def test_diluting_the_draft_moves_the_share_but_not_the_violations(self):
        src = ("we spent two years on this and got it wrong twice.\n"
               "the fix in the end was unglamorous and took a fortnight.\n")
        body = ("# T\n\nwe spent two years on this and got it wrong twice.\n\n"
                "A researched sentence adds context from the fact-check file here.\n\n"
                "the fix in the end was unglamorous and took a fortnight.\n")
        appended = body + "\n\n```json\n" + json.dumps(
            {"advisory_rating": "LOW", "note": "scan output pasted into the draft"}) + "\n```\n" \
            + "The scan reported no flagged sentences in this pass. " * 14

        clean = auth.classify(src, body)
        diluted = auth.classify(src, appended)
        self.assertTrue(clean["may_claim_authored"])
        self.assertFalse(diluted["may_claim_authored"])
        self.assertEqual(clean["violations"], diluted["violations"],
                         "the violation check cannot see this problem — only the share moves")
