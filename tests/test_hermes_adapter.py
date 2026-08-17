"""Hermes Agent adapter (plugin.yaml + __init__.py at repo root) — v3.13.0."""
from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_YAML = PLUGIN_ROOT / "plugin.yaml"
ADAPTER_PY = PLUGIN_ROOT / "__init__.py"


def _read_yaml_field(yaml_text: str, key: str) -> str | None:
    """Stdlib-only YAML field reader — sufficient for the flat fields in our plugin.yaml.

    We avoid the PyYAML dependency so the test suite stays stdlib-only.
    Handles `key: value`, `key: "value"`, and `key: >- multiline` forms.
    """
    m = re.search(rf"^{key}:\s*>-\s*\n((?:\s+\S.*\n)+)", yaml_text, re.MULTILINE)
    if m:
        return " ".join(line.strip() for line in m.group(1).splitlines() if line.strip())
    m = re.search(rf'^{key}:\s*["\']?(.*?)["\']?\s*$', yaml_text, re.MULTILINE)
    if m:
        return m.group(1).strip().rstrip('"\'')
    return None


class TestHermesPluginYaml(unittest.TestCase):
    """Validate plugin.yaml schema per https://hermes-agent.nousresearch.com/docs/guides/build-a-hermes-plugin"""

    @classmethod
    def setUpClass(cls):
        cls.assertTrue_class = unittest.TestCase().assertTrue
        cls.yaml_text = PLUGIN_YAML.read_text(encoding="utf-8")

    def test_plugin_yaml_exists_at_repo_root(self):
        self.assertTrue(PLUGIN_YAML.exists(),
                        "Hermes requires plugin.yaml at the repo root; not found.")

    def test_required_name_present(self):
        name = _read_yaml_field(self.yaml_text, "name")
        self.assertEqual(name, "digital-marketing-pro")

    def test_required_version_present_and_semver(self):
        version = _read_yaml_field(self.yaml_text, "version")
        self.assertIsNotNone(version)
        self.assertRegex(version, r"^\d+\.\d+\.\d+$",
                         f"version must be semver, got: {version!r}")

    def test_required_description_present(self):
        desc = _read_yaml_field(self.yaml_text, "description")
        self.assertIsNotNone(desc)
        self.assertGreater(len(desc), 30,
                           "description should be substantive (Hermes UI surfaces it)")

    def test_optional_provides_tools_block(self):
        self.assertIn("provides_tools:", self.yaml_text,
                      "Skills-only plugin should explicitly declare empty provides_tools")

    def test_no_unexpected_hooks_declared(self):
        # Our zero-global-hooks policy must hold across Hermes too.
        # provides_hooks: [] (empty) is OK; provides_hooks: [some-hook] is NOT.
        m = re.search(r"^provides_hooks:\s*\[(.*?)\]", self.yaml_text, re.MULTILINE)
        self.assertIsNotNone(m, "provides_hooks: [] should be declared explicitly")
        contents = m.group(1).strip()
        self.assertEqual(contents, "",
                         f"DMP must ship zero Hermes hooks; got: {contents!r}")

    def test_requires_env_empty(self):
        # Plugin must install with zero required env vars (graceful degradation).
        m = re.search(r"^requires_env:\s*\[(.*?)\]", self.yaml_text, re.MULTILINE)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).strip(), "",
                         "DMP must not require env vars at install time")


class TestHermesAdapterPy(unittest.TestCase):
    """Validate __init__.py adapter — importable, exposes register(ctx), audit() works."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("dmp_hermes_adapter", ADAPTER_PY)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_adapter_imports_without_error(self):
        self.assertIsNotNone(self.module)

    def test_register_function_exists(self):
        self.assertTrue(hasattr(self.module, "register"),
                        "Hermes calls register(ctx) at startup — function must exist")
        self.assertTrue(callable(self.module.register))

    def test_audit_function_works(self):
        result = self.module.audit()
        self.assertIn("plugin_root", result)
        self.assertIn("plugin_version", result)
        self.assertIn("skill_count", result)
        self.assertGreater(result["skill_count"], 100,
                           "audit() should discover every skills/ directory")

    def test_register_against_mock_ctx_registers_all_skills(self):
        registered = []

        class MockCtx:
            def register_skill(self, name, path):
                registered.append((name, str(path)))

        self.module.register(MockCtx())
        self.assertGreater(len(registered), 100,
                           f"register() should expose every skill; got {len(registered)}")

    def test_register_degrades_gracefully_when_ctx_missing_register_skill(self):
        """If Hermes API differs from the documented spec, plugin must not crash."""
        class BadCtx:
            pass  # no register_skill attribute

        # Should NOT raise — adapter logs error and returns cleanly
        try:
            self.module.register(BadCtx())
        except Exception as exc:
            self.fail(f"register() must not raise on bad ctx; raised {type(exc).__name__}: {exc}")

    def test_plugin_version_matches_plugin_yaml(self):
        yaml_text = PLUGIN_YAML.read_text(encoding="utf-8")
        yaml_version = _read_yaml_field(yaml_text, "version")
        self.assertEqual(self.module.PLUGIN_VERSION, yaml_version,
                         "PLUGIN_VERSION in __init__.py must match plugin.yaml version")


if __name__ == "__main__":
    unittest.main()
