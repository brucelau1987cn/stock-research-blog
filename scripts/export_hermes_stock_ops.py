#!/usr/bin/env python3
"""Export Stock site Hermes cron jobs and helper scripts without secrets/runtime state."""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any

RUNTIME_FIELDS = {
    "created_at", "next_run_at", "last_run_at", "last_status", "last_error",
    "last_delivery_error", "fire_claim", "provider_snapshot", "model_snapshot",
    "base_url_snapshot", "paused_at", "paused_reason", "state", "schedule_display",
}
HELPERS = (
    "iwencai_runner.py",
    "is_trading_day.py",
    "is_us_trading_day.py",
    "serenity_persist.py",
)
SECRET_PATTERNS = (
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^\s'\"]{8,}"),
)


def portable(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("/root/projects/stock-research-blog", "${STOCK_SITE_DIR}").replace("/root/", "${HOME}/")
    if isinstance(value, list):
        return [portable(item) for item in value]
    if isinstance(value, dict):
        return {key: portable(item) for key, item in value.items()}
    return value


def sanitize_job(job: dict) -> dict:
    result = {key: value for key, value in job.items() if key not in RUNTIME_FIELDS}
    result.pop("origin", None)  # chat/user IDs are machine-specific
    result["model"] = None
    result["provider"] = None
    result["base_url"] = None
    repeat = result.get("repeat")
    if isinstance(repeat, dict):
        result["repeat"] = {"times": repeat.get("times")}
    return portable(result)


def assert_safe(text: str) -> None:
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            raise SystemExit(f"Refusing export: possible secret matched {pattern.pattern}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hermes-home", type=Path, default=Path.home() / ".hermes")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "ops" / "hermes")
    args = parser.parse_args()

    jobs_path = args.hermes_home / "cron" / "jobs.json"
    raw = json.loads(jobs_path.read_text())
    jobs = [sanitize_job(job) for job in raw.get("jobs", [])]
    jobs.sort(key=lambda job: (job.get("name", ""), job.get("id", "")))

    args.output.mkdir(parents=True, exist_ok=True)
    exported = json.dumps({"schema_version": 1, "jobs": jobs}, ensure_ascii=False, indent=2) + "\n"
    assert_safe(exported)
    (args.output / "stock-cron-jobs.json").write_text(exported)

    helper_dir = args.output / "scripts"
    helper_dir.mkdir(exist_ok=True)
    for name in HELPERS:
        source = args.hermes_home / "scripts" / name
        if not source.exists():
            raise SystemExit(f"Missing required helper: {source}")
        text = source.read_text()
        assert_safe(text)
        (helper_dir / name).write_text(text)

    print(f"Exported {len(jobs)} jobs and {len(HELPERS)} helper scripts to {args.output}")


if __name__ == "__main__":
    main()
