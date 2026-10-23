"""Detect mixed old/new source files before Actions starts a live crawl."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from adapters.registry import load_adapter

ROOT = Path(__file__).resolve().parents[1]


class ReleaseFileIntegrityTests(unittest.TestCase):
    def test_all_source_views_match_adapters(self):
        canonical = json.loads((ROOT / "policy_sources.json").read_text(encoding="utf-8"))
        mirrored = json.loads((ROOT / "site/data/policy_sources.json").read_text(encoding="utf-8"))
        published = json.loads((ROOT / "site/data/policy_source_registry.json").read_text(encoding="utf-8"))
        self.assertEqual(canonical, mirrored, "public source mirror differs from crawler config")
        self.assertEqual(
            {row["id"]: row["url"] for row in canonical},
            {row["id"]: row["url"] for row in published},
            "published source registry has stale URLs",
        )
        for source in canonical:
            with self.subTest(id=source["id"]):
                load_adapter(source)

    def test_workflow_guard_script_exists(self):
        workflow = (ROOT / ".github/workflows/update.yml").read_text(encoding="utf-8")
        self.assertIn("python policy_run_guard.py", workflow)
        self.assertTrue((ROOT / "policy_run_guard.py").is_file())


if __name__ == "__main__":
    unittest.main()
