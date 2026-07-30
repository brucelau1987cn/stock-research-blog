#!/usr/bin/env python3
"""
Serenity @aleabitoreddit 推文持久化脚本（防 /tmp 重启丢失）

调用方式：
  python3 ~/.hermes/scripts/serenity_persist.py fetch [--days N]
  python3 ~/.hermes/scripts/serenity_persist.py dump
  python3 ~/.hermes/scripts/serenity_persist.py high-water-mark <tweet_id>

数据源：xurl search "from:aleabitoreddit" -n 100
限制：X recent search 7 天窗口；不在窗口内的推文不可恢复。
输出：~/.hermes/cache/serenity/YYYY-MM-DD_HHMM.json + 高水位标记
      ~/.hermes/cache/serenity/_high_water.json

注意：每条推文必须 7 天内拉取，逾期不可恢复。Serenity cron (df4ab2b921b9)
每天 12:00 BJT 跑一次，确保 7 天内有 ~7 次机会拉到。
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

CACHE_DIR = Path.home() / ".hermes" / "cache" / "serenity"
HW_FILE = CACHE_DIR / "_high_water.json"
BJT = timezone(timedelta(hours=8))
DB_PATH = Path.home() / ".hermes" / "memory_store.db"
# 6 月及以后的推文才进 fact_store（用户决策 2026-06-13：之前不要了）
FACT_STORE_CUTOFF = "2026-06-01"
# Serenity user_id（用 user-timeline endpoint，无 7 天限制，且 since_id 增量=按条数计费）
SERENITY_USER_ID = "1940360837547565056"


def tweet_id_to_bjt(tid: str) -> str:
    """Snowflake (Twitter) tweet id → 毫秒时间戳 → BJT ISO 字符串。
    Snowflake epoch: 1288834974657 (2010-11-04T01:42:54.657Z)
    """
    try:
        ts_ms = (int(tid) >> 22) + 1288834974657
        dt_utc = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        dt_bjt = dt_utc.astimezone(BJT)
        return dt_bjt.strftime("%Y-%m-%d %H:%M:%S BJT")
    except (ValueError, TypeError, OSError):
        return "unknown"


def fetch_xurl(query: str, n: int = 100) -> list[dict]:
    """兼容旧 API：用 user-timeline endpoint 拉 Serenity 推文（无 7 天窗口）。

    Args:
        query: 忽略，保留签名以兼容旧调用
        n: max_results（默认 100）
    """
    # 高水位增量（避免拉全量，按条数计费）
    since_id = ""
    if HW_FILE.exists():
        try:
            hw = json.loads(HW_FILE.read_text())
            since_id = hw.get("max_tweet_id", "")
        except json.JSONDecodeError:
            pass

    url = f"/2/users/{SERENITY_USER_ID}/tweets?max_results={n}&tweet.fields=created_at,public_metrics,conversation_id,entities&expansions=author_id&user.fields=username,name,verified"
    if since_id:
        url += f"&since_id={since_id}"

    try:
        result = subprocess.run(
            ["xurl", url],
            capture_output=True, text=True, timeout=60,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"[xurl error] {e}", file=sys.stderr)
        return []
    if result.returncode != 0:
        print(f"[xurl rc={result.returncode}] {result.stderr[:200]}", file=sys.stderr)
        return []
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"[json error] {e}", file=sys.stderr)
        return []
    tweets = data.get("data", [])
    if not isinstance(tweets, list):
        return []
    return tweets


def enrich_tweet(t: dict) -> dict:
    """给推文补 BJT 时间 + 互动量归一化。"""
    out = dict(t)
    tid = t.get("id", "")
    out["bjt_time"] = tweet_id_to_bjt(tid) if tid else "unknown"
    pm = t.get("public_metrics", {}) or {}
    out["engagement"] = (
        pm.get("like_count", 0)
        + pm.get("retweet_count", 0) * 3
        + pm.get("reply_count", 0) * 2
        + pm.get("quote_count", 0) * 4
        + pm.get("bookmark_count", 0) * 5
    )
    return out


def cmd_fetch(days: int = 7) -> None:
    """拉新推文（since_id 增量模式），按天分文件落盘。"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tweets = fetch_xurl("from:aleabitoreddit", 100)  # query 参数已忽略
    print(f"[fetch] got {len(tweets)} new tweets (since_id mode)")
    if not tweets:
        return

    # 读高水位
    hw = {}
    if HW_FILE.exists():
        try:
            hw = json.loads(HW_FILE.read_text())
        except json.JSONDecodeError:
            hw = {}
    prev_max_id = hw.get("max_tweet_id", "")

    enriched = [enrich_tweet(t) for t in tweets]
    # 按 BJT 日期分组
    by_date: dict[str, list[dict]] = {}
    max_id = prev_max_id
    for t in enriched:
        bid = t.get("bjt_time", "unknown")[:10]
        by_date.setdefault(bid, []).append(t)
        tid = t.get("id", "")
        if tid and (not max_id or int(tid) > int(max_id)):
            max_id = tid

    # 写盘
    written = 0
    for date, items in by_date.items():
        fpath = CACHE_DIR / f"{date}.json"
        existing: list[dict] = []
        if fpath.exists():
            try:
                existing = json.loads(fpath.read_text())
            except json.JSONDecodeError:
                existing = []
        seen_ids = {x.get("id") for x in existing}
        for it in items:
            if it.get("id") not in seen_ids:
                existing.append(it)
                written += 1
        existing.sort(key=lambda x: int(x.get("id", 0)))
        fpath.write_text(json.dumps(existing, ensure_ascii=False, indent=2))

    # 更新高水位
    new_hw = {
        "max_tweet_id": max_id,
        "last_fetch_bjt": datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S"),
        "last_fetch_count": len(tweets),
        "files": sorted([p.name for p in CACHE_DIR.glob("2026-*.json")]),
    }
    HW_FILE.write_text(json.dumps(new_hw, ensure_ascii=False, indent=2))
    print(f"[fetch] wrote {written} new tweets across {len(by_date)} days")
    print(f"[fetch] high water: {prev_max_id} → {max_id}")


def cmd_dump() -> None:
    """列出所有已缓存推文，按 BJT 时间倒序输出 JSON。"""
    files = sorted(CACHE_DIR.glob("2026-*.json"))
    all_tweets: list[dict] = []
    for f in files:
        try:
            for t in json.loads(f.read_text()):
                all_tweets.append(t)
        except json.JSONDecodeError:
            continue
    all_tweets.sort(key=lambda x: int(x.get("id", 0)), reverse=True)
    print(json.dumps(all_tweets, ensure_ascii=False, indent=2))


def cmd_high_water(tid: str) -> None:
    """手动设高水位。"""
    if not HW_FILE.exists():
        HW_FILE.write_text("{}")
    hw = json.loads(HW_FILE.read_text())
    hw["max_tweet_id"] = tid
    hw["manual_set_bjt"] = datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")
    HW_FILE.write_text(json.dumps(hw, ensure_ascii=False, indent=2))
    print(f"high water set to {tid}")


def status() -> None:
    if HW_FILE.exists():
        print(json.dumps(json.loads(HW_FILE.read_text()), indent=2))
    else:
        print("no high water file yet")
    files = sorted(CACHE_DIR.glob("2026-*.json"))
    print(f"\ncached {len(files)} daily files:")
    for f in files:
        n = len(json.loads(f.read_text())) if f.exists() else 0
        print(f"  {f.name}  {n} tweets")


def sync_to_factstore() -> int:
    """把缓存里 6 月及以后、未存的推文写进 fact_store。

    Returns: 新增的 fact 条数
    """
    import sqlite3
    if not DB_PATH.exists():
        print(f"[sync] DB not found: {DB_PATH}", file=sys.stderr)
        return 0

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # 载入所有缓存推文
    all_tweets: list[dict] = []
    for f in sorted(CACHE_DIR.glob("2026-*.json")):
        for t in json.loads(f.read_text()):
            all_tweets.append(t)
    all_tweets.sort(key=lambda x: int(x.get("id", 0)))

    # 已存 fact 签名（推文文本前 80 字符，覆盖原手动 14 条的"推文"/"tweet"前缀差异）
    cur.execute("SELECT content FROM facts WHERE tags LIKE '%serenity%' AND tags LIKE '%tweet%'")
    seen: set[str] = set()
    seen_dates: set[str] = set()  # 已有 fact 覆盖的 BJT 日期，整日跳过
    import re as _re
    for (content,) in cur.fetchall():
        # 提取 BJT 日期
        dm = _re.search(r'(\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}\s*BJT', content)
        if dm:
            seen_dates.add(dm.group(1))
        # 提取"BJT: "之后的核心文本签名
        m = _re.search(r'BJT:\s*(.{30,80})', content)
        if m:
            seen.add(m.group(1).strip()[:60])
        # 也用 "推文" 关键字的旧格式
        elif "推文" in content:
            seen.add(content.split("推文", 1)[-1][:50])
    if seen_dates:
        print(f"[sync] skip dates with existing facts: {sorted(seen_dates)}", file=sys.stderr)

    new_count = 0
    import re
    for t in all_tweets:
        bjt = t.get("bjt_time", "")
        bjt_date = bjt[:10] if bjt else ""
        # 6 月及以后才落
        if not bjt or bjt_date < FACT_STORE_CUTOFF:
            continue
        # 已有人工 fact 覆盖的整日跳过（避免重复入库同主题）
        if bjt_date in seen_dates:
            continue
        text = t.get("text", "").strip()
        if not text:
            continue
        sig = text[:50]
        if sig in seen:
            continue

        cashtags = re.findall(r"\$([A-Z]{2,5})", text)
        tickers = list(set(cashtags))

        fact_content = (
            f"Serenity @aleabitoreddit tweet {bjt}: {text[:300]}"
            f"{'. 涉及标的: ' + ', '.join(['$' + tk for tk in tickers]) if tickers else ''}"
        )
        tags_parts = ["serenity", "tweet", bjt[:10], "cache-persist"]
        for tk in tickers[:3]:
            tags_parts.append(f"ticker-{tk.lower()}")

        cur.execute(
            "INSERT OR IGNORE INTO facts (content, category, tags, trust_score) "
            "VALUES (?, ?, ?, ?)",
            (fact_content, "general", ",".join(tags_parts), 0.65),
        )
        if cur.lastrowid:
            new_id = cur.lastrowid
            try:
                cur.execute(
                    "INSERT INTO facts_fts(rowid, content, tags) VALUES (?, ?, ?)",
                    (new_id, fact_content, ",".join(tags_parts)),
                )
            except sqlite3.OperationalError:
                pass
            new_count += 1
            seen.add(sig)

    conn.commit()
    conn.close()
    return new_count


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("dump")
    pf = sub.add_parser("fetch")
    pf.add_argument("--days", type=int, default=7)
    sub.add_parser("status")
    sub.add_parser("sync")
    pw = sub.add_parser("high-water-mark")
    pw.add_argument("tweet_id")

    args = p.parse_args()
    if args.cmd == "fetch":
        cmd_fetch(args.days)
    elif args.cmd == "dump":
        cmd_dump()
    elif args.cmd == "high-water-mark":
        cmd_high_water(args.tweet_id)
    elif args.cmd == "status":
        status()
    elif args.cmd == "sync":
        n = sync_to_factstore()
        print(f"[sync] wrote {n} new tweet facts to fact_store (cutoff={FACT_STORE_CUTOFF})")


if __name__ == "__main__":
    main()
