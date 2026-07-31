#!/usr/bin/env python3
"""Validate a YAML/JSON mapping and atomically write canonical tracker JSON."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile

import yaml


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()

    data = yaml.safe_load(args.source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("tracker state must be a mapping")

    args.target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{args.target.name}.", suffix=".tmp", dir=args.target.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, args.target)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise

    verified = json.loads(args.target.read_text(encoding="utf-8"))
    if verified != data:
        raise SystemExit("tracker state verification mismatch")
    print(f"TRACKER_STATE_OK {args.target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
