"""language-router.py — capability routing resolves at run time, never from a table.

The contract under test: route names a capability kind and criteria; a concrete
service appears ONLY via the brand's recorded preference or the user's
connected MCP servers; with neither, the router refuses and hands back the
resolution ladder. A shipped vendor table can never quietly return.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _helpers import import_script, run_json

language_router = import_script("language-router.py")

VENDOR_TOKENS = ("deepl", "sarvam", "lara-translate", "google-cloud-translation")


class TestCapabilityProfiles(unittest.TestCase):
    def test_every_family_has_kind_and_criteria(self):
        for family, profile in language_router.FAMILY_CAPABILITY_PROFILES.items():
            self.assertTrue(profile["capability_kind"].startswith("translation."),
                            f"{family}: capability_kind malformed")
            self.assertTrue(profile["service_criteria"], f"{family}: no criteria")

    def test_profiles_contain_no_vendor_names(self):
        """The whole point: criteria, not endorsements. If a product name gets
        edited into a profile, the routing table has been reintroduced."""
        blob = json.dumps(language_router.FAMILY_CAPABILITY_PROFILES).lower()
        for token in VENDOR_TOKENS:
            self.assertNotIn(token, blob,
                             f"vendor name {token!r} found inside FAMILY_CAPABILITY_PROFILES")


class TestRouteResolution(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_unresolved_refuses_and_ships_the_ladder(self):
        with mock.patch.object(language_router, "_connected_translation_servers",
                               return_value=[]):
            with _captured_route(source="en", target="hi") as payload:
                pass
        self.assertIsNone(payload["recommended_service"])
        self.assertEqual(payload["basis"], "unresolved")
        self.assertEqual(len(payload["resolution_ladder"]), 3)
        self.assertIn("never instruct installing", " ".join(payload["resolution_ladder"]).lower())
        blob = json.dumps(payload).lower()
        for token in VENDOR_TOKENS:
            self.assertNotIn(token, blob,
                             f"unresolved route payload names vendor {token!r}")

    def test_brand_preference_wins_and_is_free_form(self):
        """A server name that exists in no shipped list must resolve cleanly —
        unknown is not unusable."""
        brand_dir = self.home / "brands" / "acme"
        brand_dir.mkdir(parents=True)
        (brand_dir / "profile.json").write_text(json.dumps(
            {"language": {"translation_preferences": {"de": "my-own-translator"}}}),
            encoding="utf-8")
        data, rc = run_json("language-router.py", "--action", "route",
                            "--source", "en", "--target", "de", "--brand", "acme",
                            marketing_home=self.home)
        self.assertEqual(rc, 0)
        self.assertEqual(data["recommended_service"], "my-own-translator")
        self.assertEqual(data["basis"], "brand-preference")

    def test_single_connected_candidate_resolves(self):
        with mock.patch.object(language_router, "_connected_translation_servers",
                               return_value=["team-translation-server"]):
            with _captured_route(source="en", target="fr") as payload:
                pass
        self.assertEqual(payload["recommended_service"], "team-translation-server")
        self.assertEqual(payload["basis"], "connected-servers")

    def test_multiple_candidates_defer_to_criteria(self):
        with mock.patch.object(language_router, "_connected_translation_servers",
                               return_value=["server-a", "server-b"]):
            with _captured_route(source="en", target="ja") as payload:
                pass
        self.assertIsNone(payload["recommended_service"])
        self.assertEqual(payload["connected_candidates"], ["server-a", "server-b"])
        self.assertIn("service_criteria", payload["selection_instruction"])

    def test_preference_missing_from_connected_warns(self):
        brand_dir = self.home / "brands" / "acme"
        brand_dir.mkdir(parents=True)
        (brand_dir / "profile.json").write_text(json.dumps(
            {"language": {"translation_preferences": {"de": "gone-server"}}}),
            encoding="utf-8")
        with mock.patch.dict(os.environ, {"CLAUDE_MARKETING_HOME": str(self.home)}):
            with mock.patch.object(language_router, "_connected_translation_servers",
                                   return_value=["other-server"]):
                with _captured_route(source="en", target="de", brand="acme") as payload:
                    pass
        self.assertEqual(payload["recommended_service"], "gone-server")
        self.assertIn("warning", payload)


class TestServerHintMatcher(unittest.TestCase):
    def test_recognizes_translation_ish_names(self):
        hints = language_router.TRANSLATION_SERVER_HINTS
        self.assertTrue(any(h in "my-translation-bridge" for h in hints))
        self.assertFalse(any(h in "slack" for h in hints))
        self.assertFalse(any(h in "google-ads" for h in hints))


class TestRegression(unittest.TestCase):
    """Detection and scoring were untouched by the rework — pin them."""

    def test_detect_hindi(self):
        # Devanagari round-trips through the subprocess only with explicit
        # UTF-8 decoding on the parent side (Windows defaults to cp1252),
        # so this test drives subprocess directly instead of run_json.
        import subprocess
        import sys as _sys
        from _helpers import SCRIPTS_DIR
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("यह एक हिंदी वाक्य है")
            path = fh.name
        try:
            proc = subprocess.run(
                [_sys.executable, str(SCRIPTS_DIR / "language-router.py"),
                 "--action", "detect", "--file", path],
                capture_output=True, encoding="utf-8", errors="replace", timeout=60)
        finally:
            Path(path).unlink(missing_ok=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["detected_language"], "hi")

    def test_score_flags_lost_placeholder(self):
        data, rc = run_json("language-router.py", "--action", "score",
                            "--original", "Hi {{name}}, welcome!",
                            "--translated", "Hola, bienvenido!",
                            "--source", "en", "--target", "es")
        self.assertEqual(rc, 0)
        self.assertIn("{{name}}",
                      data["dimensions"]["placeholder_integrity"]["missing"])


class _captured_route:
    """Run action_route in-process with stdout captured as parsed JSON."""

    def __init__(self, source, target, brand=None):
        self.args = mock.Mock(source=source, target=target, brand=brand)

    def __enter__(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            language_router.action_route(self.args)
        self.payload = json.loads(buf.getvalue())
        return self.payload

    def __exit__(self, *exc):
        return False


if __name__ == "__main__":
    unittest.main()
