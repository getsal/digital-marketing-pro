"""skills-index.json is a contract, not a snapshot.

The index publishes what each skill guarantees (tier E executes scripts,
M routes through the quality machinery, G structured guidance). A contract
nobody enforces is marketing; these tests are the enforcement:

  * the committed index must exactly match a fresh regeneration (no drift),
  * every script a skill references must exist (no broken promises),
  * the executable tier must not silently collapse (floor pinned),
  * every skill directory is indexed and every index entry has a directory.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from _helpers import PLUGIN_ROOT, SCRIPTS_DIR, import_script

INDEX = PLUGIN_ROOT / "skills-index.json"
SKILLS = PLUGIN_ROOT / "skills"

# Floor, not target: 107 skills executed real scripts when the contract was
# introduced (v3.21.0). A dip below 100 means machinery was removed at scale.
E_TIER_FLOOR = 100


def load_index():
    return json.loads(INDEX.read_text(encoding="utf-8"))


class TestSkillsIndexContract(unittest.TestCase):
    def test_index_exists_and_parses(self):
        self.assertTrue(INDEX.exists(), "skills-index.json missing — run build_skills_index.py")
        idx = load_index()
        self.assertEqual(idx["skill_count"], len(idx["skills"]))

    def test_no_drift_from_reality(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "build_skills_index.py"), "--check"],
            capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0,
                         "skills-index.json drifted from the repo:\n" + proc.stderr)

    def test_every_referenced_script_exists(self):
        broken = [f"{e['name']} -> {e['missing_scripts']}"
                  for e in load_index()["skills"] if e["missing_scripts"]]
        self.assertEqual(broken, [],
                         "Skills reference scripts that do not exist:\n  " + "\n  ".join(broken))

    def test_executable_tier_floor(self):
        tiers = load_index()["tiers"]
        self.assertGreaterEqual(
            tiers["E"], E_TIER_FLOOR,
            f"Only {tiers['E']} skills execute real scripts (floor {E_TIER_FLOOR}) — "
            "machinery was removed at scale, or the scanner regressed.")

    def test_index_covers_exactly_the_skill_dirs(self):
        on_disk = {d.name for d in SKILLS.iterdir() if d.is_dir()}
        indexed = {e["name"] for e in load_index()["skills"]}
        self.assertEqual(on_disk, indexed,
                         f"unindexed: {sorted(on_disk - indexed)}; "
                         f"ghost entries: {sorted(indexed - on_disk)}")

    def test_every_entry_has_a_description(self):
        empty = [e["name"] for e in load_index()["skills"] if not e["description"].strip()]
        self.assertEqual(empty, [], "Skills with empty frontmatter descriptions: " + ", ".join(empty))

    # ── plant checks: the analyzer itself ───────────────────────────

    def test_script_ref_scanner_sees_invocations(self):
        mod = import_script("build_skills_index.py")
        self.assertEqual(mod.SCRIPT_REF.findall("run `python scripts/roi-calculator.py --json`"),
                         ["roi-calculator.py"])
        self.assertEqual(mod.SCRIPT_REF.findall("no scripts here"), [])

    def test_frontmatter_parser_handles_quoted_values(self):
        mod = import_script("build_skills_index.py")
        fm = mod.parse_frontmatter('---\nname: x\ndescription: "Has: a colon"\n---\nbody')
        self.assertEqual(fm["description"], "Has: a colon")

    def test_tier_assignment_is_e_when_scripts_exist(self):
        """A skill whose docs invoke an existing script must index as tier E —
        if this fails the whole depth contract is mislabeled."""
        idx = load_index()
        by_name = {e["name"]: e for e in idx["skills"]}
        with_scripts = [e for e in idx["skills"] if e["scripts"]]
        self.assertTrue(with_scripts, "no skill indexes any script — scanner regressed")
        for e in with_scripts:
            self.assertEqual(by_name[e["name"]]["tier"], "E",
                             f"{e['name']} references {e['scripts']} but is tier {e['tier']}")


if __name__ == "__main__":
    unittest.main()
