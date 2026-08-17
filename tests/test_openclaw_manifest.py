"""OpenClaw native manifest (openclaw.plugin.json) — v3.13.0.

Schema reference: https://docs.openclaw.ai/plugins/manifest
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
OPENCLAW_MANIFEST = PLUGIN_ROOT / "openclaw.plugin.json"


class TestOpenClawManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(OPENCLAW_MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_exists_at_repo_root(self):
        self.assertTrue(OPENCLAW_MANIFEST.exists())

    def test_id_required_and_canonical(self):
        # `id` is the canonical plugin id used in `plugins.entries.<id>`
        self.assertIn("id", self.data)
        self.assertEqual(self.data["id"], "digital-marketing-pro")

    def test_configSchema_required(self):
        # OpenClaw spec: "Every native OpenClaw plugin must ship a configSchema,
        # even for no-config plugins"
        self.assertIn("configSchema", self.data)
        schema = self.data["configSchema"]
        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["additionalProperties"], False,
                         "additionalProperties: false required to lock down config surface")

    def test_skills_points_at_skills_directory(self):
        # The `skills` array tells OpenClaw where to find SKILL.md files
        self.assertIn("skills", self.data)
        self.assertEqual(self.data["skills"], ["./skills"])

        # And that directory must actually exist with the full skill set
        skills_dir = PLUGIN_ROOT / "skills"
        self.assertTrue(skills_dir.exists())
        skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]
        self.assertGreater(len(skill_dirs), 100,
                           f"OpenClaw will load from ./skills; found only {len(skill_dirs)}")

    def test_version_matches_plugin_json(self):
        plugin_json = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(self.data.get("version"), plugin_json["version"],
                         "OpenClaw manifest version must track the canonical Claude Code manifest")

    def test_name_and_description_present(self):
        self.assertIn("name", self.data)
        self.assertIn("description", self.data)
        self.assertGreater(len(self.data["description"]), 30,
                           "OpenClaw description surfaces in UI; should be substantive")

    def test_no_hooks_declared(self):
        # Our zero-hooks policy across all platforms.
        self.assertNotIn("hooks", self.data)
        self.assertNotIn("provides_hooks", self.data)

    def test_no_unexpected_top_level_fields(self):
        # Per OpenClaw spec: id, configSchema (required), plus optional name/description/version/
        # kind/channels/providers/skills/enabledByDefault/requiresPlugins/activation/setup/
        # contracts/uiHints/modelCatalog/channelConfigs
        allowed = {
            "id", "configSchema",
            "name", "description", "version",
            "kind", "channels", "providers", "skills",
            "enabledByDefault", "requiresPlugins",
            "activation", "setup", "contracts", "uiHints",
            "modelCatalog", "channelConfigs",
        }
        unexpected = set(self.data.keys()) - allowed
        self.assertEqual(unexpected, set(),
                         f"Unexpected top-level fields in openclaw.plugin.json: {unexpected}")


class TestOpenClawConfigSchemaIsValidJSONSchema(unittest.TestCase):
    """The configSchema must be a structurally valid JSON Schema fragment."""

    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(OPENCLAW_MANIFEST.read_text(encoding="utf-8"))
        cls.schema = cls.data["configSchema"]

    def test_configSchema_has_type_object(self):
        self.assertEqual(self.schema["type"], "object")

    def test_configSchema_additionalProperties_locked_down(self):
        # We declare a no-config plugin — additionalProperties must be false
        # to prevent accidental config injection at runtime.
        self.assertEqual(self.schema["additionalProperties"], False)

    def test_configSchema_properties_block_exists(self):
        # Even for no-config, the properties block must be present as an empty
        # object (so JSON Schema validators don't treat undefined as "any").
        self.assertIn("properties", self.schema)
        self.assertIsInstance(self.schema["properties"], dict)


class TestOpenClawIDIsKebabCase(unittest.TestCase):
    """OpenClaw plugin IDs are used in URL paths + ClawHub slugs."""

    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(OPENCLAW_MANIFEST.read_text(encoding="utf-8"))

    def test_id_is_kebab_case(self):
        import re
        self.assertRegex(
            self.data["id"], r"^[a-z][a-z0-9-]*[a-z0-9]$",
            f"id must be kebab-case (a-z 0-9 hyphens) — got {self.data['id']!r}"
        )

    def test_id_matches_claude_plugin_name(self):
        # Across all our manifests the canonical name should be the same.
        cp = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(self.data["id"], cp["name"],
                         "OpenClaw id must match .claude-plugin/plugin.json's name")


class TestSkillsDirectoryDeclaredCorrectly(unittest.TestCase):
    """The `skills` field must reference an actual directory with SKILL.md files."""

    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(OPENCLAW_MANIFEST.read_text(encoding="utf-8"))

    def test_skills_paths_are_relative(self):
        for path in self.data["skills"]:
            self.assertTrue(path.startswith("./"),
                            f"OpenClaw skills paths must be relative — got {path!r}")

    def test_skills_paths_exist_on_disk(self):
        for path in self.data["skills"]:
            resolved = (PLUGIN_ROOT / path).resolve()
            self.assertTrue(resolved.exists(),
                            f"OpenClaw skills path {path!r} doesn't exist at {resolved}")
            self.assertTrue(resolved.is_dir(),
                            f"OpenClaw skills path {path!r} must be a directory")


if __name__ == "__main__":
    unittest.main()
