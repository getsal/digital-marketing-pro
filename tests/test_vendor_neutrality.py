"""The instruction surface must not depend on, endorse, or instruct installing
commercial translation products.

The rule this enforces (suite-wide policy): capability KINDS are resolved at
run time; a workflow may USE whatever the user has connected, but no skill or
agent may name a commercial translation product as the way the work gets done,
and nothing anywhere may instruct signing up for one. The localization cluster
carried a hardcoded four-vendor routing table until v3.23.0 — this guard keeps
it from growing back.

Deliberately allowed (the "user's already-connected tools" rung):
  - the connector CATALOG (CONNECTORS.md, docs/architecture registry tables,
    docs/getting-started env-var setup, docs/integrations-guide per-connector
    setup) — these enable connectors the USER chose; they are not workflow
    instructions
  - connect/SKILL.md's name-matching examples (it matches user input against
    the catalog)
  - language-router.py's TRANSLATION_SERVER_HINTS — recognition data that lets
    connected servers be DISCOVERED; explicitly commented as not-endorsement
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from _helpers import PLUGIN_ROOT, import_script

SKILLS = PLUGIN_ROOT / "skills"
AGENTS = PLUGIN_ROOT / "agents"

# Tokens for commercial translation products the cluster used to hardwire.
VENDOR_RE = re.compile(r"(?i)\b(deepl|sarvam|lara[- ]translate)\b")

# Catalog surfaces inside the scanned tree where naming connectors is the job.
EXEMPT = {
    # matches user-typed connector names against the registry catalog
    "skills/connect/SKILL.md",
}

# Anywhere in the repo: never instruct signing up for / installing a
# commercial translation product.
SIGNUP_RE = re.compile(
    r"(?i)(sign up|subscribe|install|create an account)[^.\n]{0,60}"
    r"\b(deepl|sarvam|lara[- ]translate)\b")


def instruction_files():
    for base in (SKILLS, AGENTS):
        for f in sorted(base.rglob("*.md")):
            yield f.relative_to(PLUGIN_ROOT).as_posix(), f.read_text(
                encoding="utf-8", errors="replace")


class TestTranslationVendorNeutrality(unittest.TestCase):
    def test_no_vendor_names_on_the_instruction_surface(self):
        hits = []
        for rel, text in instruction_files():
            if rel in EXEMPT:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if VENDOR_RE.search(line):
                    hits.append(f"{rel}:{i}: {line.strip()[:100]}")
        self.assertEqual(hits, [],
                         "Commercial translation vendors named on the instruction "
                         "surface (route by capability instead; see "
                         "multilingual-execution-guide §2):\n  " + "\n  ".join(hits))

    def test_no_signup_instructions_anywhere_in_skills_or_agents(self):
        hits = []
        for rel, text in instruction_files():
            m = SIGNUP_RE.search(text)
            if m:
                hits.append(f"{rel}: {m.group(0)[:100]}")
        self.assertEqual(hits, [], "Sign-up/install instructions for commercial "
                                   "translation products:\n  " + "\n  ".join(hits))

    def test_language_config_enum_stays_free_form(self):
        """Regression pin on the exact defect: set-translation-pref validated
        against a closed four-vendor list. It must stay free-form."""
        text = (SKILLS / "language-config" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("free-form", text,
                      "language-config no longer describes the preference as free-form")
        self.assertNotRegex(text, r"one of\s+`",
                            "language-config appears to enumerate a closed service list again")

    def test_router_route_never_names_a_vendor_uninvited(self):
        """With no brand preference and no connected servers, the route payload
        must refuse — and must not contain a vendor token anywhere."""
        lr = import_script("language-router.py")
        import io
        from contextlib import redirect_stdout
        from unittest import mock
        buf = io.StringIO()
        with mock.patch.object(lr, "_connected_translation_servers", return_value=[]):
            with redirect_stdout(buf):
                lr.action_route(mock.Mock(source="en", target="hi", brand=None))
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["basis"], "unresolved")
        self.assertIsNone(payload["recommended_service"])
        self.assertIsNone(VENDOR_RE.search(json.dumps(payload)),
                          "unresolved route payload names a vendor")

    # ── plant checks ────────────────────────────────────────────────

    def test_scanner_fires_on_planted_endorsement(self):
        self.assertTrue(VENDOR_RE.search("Route European languages to DeepL."))
        self.assertTrue(SIGNUP_RE.search("First, sign up for a DeepL Pro account."))

    def test_scanner_ignores_capability_language(self):
        clean = ("Route by capability: native Indic coverage, formality "
                 "registers, script-aware output. Resolve from connected servers.")
        self.assertIsNone(VENDOR_RE.search(clean))


if __name__ == "__main__":
    unittest.main()
