import json
import tempfile
import unittest
from pathlib import Path

import policy_run_guard as guard


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


class PolicyRunGuardTests(unittest.TestCase):
    def fixture(self, root, *, last_run="2026-10-22T01:00:00+00:00", attempted=1):
        dump(root / "policy_sources.json", [{"id": "cn_a"}, {"id": "cn_b"}])
        dump(root / "site/data/policy_source_status.json", [
            {"id": "cn_a", "status": "ok_no_recent"},
            {"id": "cn_b", "status": "ok_no_recent"},
        ])
        dump(root / "site/data/policy_crawl_state.json", {
            "last_run": last_run,
            "configured_source_count": 2,
            "attempted_source_count": attempted,
            "status_counts": {"ok_no_recent": 2},
        })
        marker = root / "diagnostics/this_job_started_utc.txt"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("2026-10-22T00:30:00Z\n", encoding="utf-8")
        return marker

    def test_accepts_fresh_run_with_individual_statuses(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            marker = self.fixture(root)
            result = guard.verify(root, marker)
            self.assertEqual(result["configured_source_count"], 2)
            self.assertEqual(result["attempted_source_count"], 1)

    def test_rejects_stale_state(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            marker = self.fixture(root, last_run="2026-10-21T23:00:00+00:00")
            with self.assertRaisesRegex(RuntimeError, "stale crawl state"):
                guard.verify(root, marker)

    def test_rejects_status_id_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            marker = self.fixture(root)
            dump(root / "site/data/policy_source_status.json", [
                {"id": "cn_a", "status": "ok_no_recent"},
                {"id": "cn_wrong", "status": "ok_no_recent"},
            ])
            with self.assertRaisesRegex(RuntimeError, "do not match configured"):
                guard.verify(root, marker)

    def test_rejects_inconsistent_status_counts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            marker = self.fixture(root)
            dump(root / "site/data/policy_source_status.json", [
                {"id": "cn_a", "status": "blocked"},
                {"id": "cn_b", "status": "ok_no_recent"},
            ])
            with self.assertRaisesRegex(RuntimeError, "status_counts disagree"):
                guard.verify(root, marker)

    def test_rejects_zero_attempts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            marker = self.fixture(root, attempted=0)
            with self.assertRaisesRegex(RuntimeError, "attempted_source_count is zero"):
                guard.verify(root, marker)


if __name__ == "__main__":
    unittest.main()
