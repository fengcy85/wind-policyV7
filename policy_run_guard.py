"""Fail the Actions job if the crawler did not write coherent data THIS run.

A failed individual source is acceptable; a stale, incomplete or skipped
crawler run is not. This guard is deliberately offline and has no side effects.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"required crawl output missing or invalid: {path}") from exc


def _utc_timestamp(raw: str, label: str) -> datetime:
    try:
        value = datetime.fromisoformat(str(raw).strip().replace("Z", "+00:00"))
        if value.tzinfo is None:
            raise ValueError("missing timezone")
        return value.astimezone(timezone.utc)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"invalid {label} timestamp: {raw!r}") from exc


def verify(root: Path = ROOT, marker: Path | None = None) -> dict:
    """Validate state+statuses against config, with actual job start as freshness barrier."""
    root = Path(root)
    marker = Path(marker) if marker is not None else root / "diagnostics/this_job_started_utc.txt"
    try:
        started = _utc_timestamp(marker.read_text(encoding="utf-8"), "job start")
    except OSError as exc:
        raise RuntimeError(f"required job start marker missing: {marker}") from exc

    sources = _load(root / "policy_sources.json")
    statuses = _load(root / "site/data/policy_source_status.json")
    state = _load(root / "site/data/policy_crawl_state.json")
    if not isinstance(sources, list) or not isinstance(statuses, list) or not isinstance(state, dict):
        raise RuntimeError("invalid crawl output structure")

    source_ids = [row.get("id") for row in sources if isinstance(row, dict)]
    status_ids = [row.get("id") for row in statuses if isinstance(row, dict)]
    if (len(source_ids) != len(sources) or len(set(source_ids)) != len(sources)
            or any(not isinstance(sid, str) or not sid for sid in source_ids)):
        raise RuntimeError("configured sources contain invalid or duplicate IDs")
    if (len(status_ids) != len(statuses) or len(set(status_ids)) != len(statuses)
            or set(status_ids) != set(source_ids)):
        raise RuntimeError("crawl statuses do not match configured source IDs")

    configured = state.get("configured_source_count")
    if type(configured) is not int or configured != len(sources):
        raise RuntimeError("configured_source_count disagrees with policy_sources.json")

    attempts = state.get("attempted_source_count")
    if type(attempts) is not int or attempts <= 0:
        raise RuntimeError("attempted_source_count is zero or invalid")
    if attempts > configured:
        raise RuntimeError("attempted_source_count exceeds configured_source_count")

    last_run = _utc_timestamp(state.get("last_run"), "last_run")
    if last_run < started:
        raise RuntimeError("stale crawl state: last_run precedes this job's crawl start")

    counts = state.get("status_counts")
    if not isinstance(counts, dict) or any(type(v) is not int or v < 0 for v in counts.values()):
        raise RuntimeError("invalid status_counts in crawl state")
    if sum(counts.values()) != configured:
        raise RuntimeError("status_counts total disagrees with configured sources")
    observed = {}
    for row in statuses:
        code = row.get("status")
        if not isinstance(code, str) or not code:
            raise RuntimeError("status row missing status code")
        observed[code] = observed.get(code, 0) + 1
    if observed != counts:
        raise RuntimeError("status_counts disagree with source statuses")

    return {
        "last_run": last_run.isoformat(),
        "configured_source_count": configured,
        "attempted_source_count": attempts,
        "status_counts": counts,
    }


def main() -> None:
    result = verify()
    print("CRAWL STATE PASS:", json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
