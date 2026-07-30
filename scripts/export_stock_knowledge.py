#!/usr/bin/env python3
"""Export a sanitized, portable stock-knowledge corpus from Hermes memory."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

INCLUDE = re.compile(
    r"(?i)(ticker-|serenity|stock|share|A-share|US-stock|HK-stock|ETF|market|trading|"
    r"investment|portfolio|macro|sector|industry|iwencai|hithink|mx-data|"
    r"选股|股票|个股|行情|筹码|板块|行业|市场|交易|美股|港股|A股|财报|估值|"
    r"支撑|压力|止损|复盘|仓位|持仓|技术分析|叶氏)"
)
EXCLUDE = re.compile(
    r"(?i)(api[_-]?key|password|credential|github token|telegram token|"
    r"jobs\.json|cron jobs|provider=|base_url|模型策略|服务器配置)"
)
SECRET_PATTERNS = (
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]{6,}"),
    re.compile(r"https://[^/@\s]+:[^/@\s]+@github\.com"),
)
URL = re.compile(r"https?://\S+")
HANDLE = re.compile(r"(?<![\w$])@[A-Za-z0-9_]{1,32}")
PHONE = re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)")
EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
WHITESPACE = re.compile(r"[ \t]+")


def clean_text(text: str) -> str:
    text = URL.sub("[source-url-removed]", text)
    text = EMAIL.sub("[email-removed]", text)
    text = PHONE.sub("[phone-removed]", text)
    text = HANDLE.sub("[handle-removed]", text)
    text = "\n".join(WHITESPACE.sub(" ", line).strip() for line in text.splitlines())
    return text.strip()


def normalized_tags(tags: str) -> list[str]:
    result = []
    for tag in tags.split(","):
        tag = tag.strip()
        if not tag or re.search(r"(?i)(user|chat|token|secret|credential|provider|cron)", tag):
            continue
        result.append(tag)
    return sorted(set(result), key=str.lower)


def assert_safe(text: str) -> None:
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            raise SystemExit(f"Refusing export: sensitive pattern matched {pattern.pattern}")


def iter_facts(connection: sqlite3.Connection) -> Iterable[tuple]:
    query = """
        SELECT content, category, tags, trust_score, created_at, updated_at
        FROM facts ORDER BY created_at, fact_id
    """
    yield from connection.execute(query)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path.home() / ".hermes" / "memory_store.db")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "knowledge" / "memory")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    skipped = Counter()
    connection = sqlite3.connect(args.db)
    try:
        for content, category, tags, trust, created, updated in iter_facts(connection):
            haystack = f"{tags or ''} {content or ''}"
            if category == "user_pref":
                skipped["user_preference"] += 1
                continue
            if not INCLUDE.search(haystack):
                skipped["not_stock_related"] += 1
                continue
            if EXCLUDE.search(haystack):
                skipped["system_or_credential_context"] += 1
                continue
            cleaned = clean_text(content or "")
            clean_tags = normalized_tags(tags or "")
            if not cleaned:
                skipped["empty_after_cleaning"] += 1
                continue
            source_id = hashlib.sha256((cleaned + "\0" + ",".join(clean_tags)).encode()).hexdigest()[:20]
            record = {
                "source_id": source_id,
                "content": cleaned,
                "category": category,
                "tags": clean_tags,
                "trust_score": round(float(trust or 0.0), 3),
                "created_at": created,
                "updated_at": updated,
            }
            line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            assert_safe(line)
            records.append((source_id, line, clean_tags))
    finally:
        connection.close()

    # Exact duplicates collapse by content/tags hash.
    unique = {source_id: (line, tags) for source_id, line, tags in records}
    output_file = args.output / "stock-knowledge.jsonl"
    output_text = "\n".join(unique[key][0] for key in sorted(unique)) + "\n"
    assert_safe(output_text)
    output_file.write_text(output_text)

    tag_counts = Counter(tag for _, tags in unique.values() for tag in tags)
    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(unique),
        "source": "sanitized export from Hermes holographic memory",
        "redactions": ["URLs", "social handles", "email addresses", "Chinese mobile numbers", "credential-like strings"],
        "excluded": dict(skipped),
        "top_tags": tag_counts.most_common(40),
        "import_note": "Import records as new facts; source_id is a content/tag deduplication key, not the original database fact_id.",
    }
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    assert_safe(manifest_text)
    (args.output / "manifest.json").write_text(manifest_text)
    print(f"Exported {len(unique)} sanitized stock facts to {output_file}")


if __name__ == "__main__":
    main()
