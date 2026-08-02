#!/usr/bin/env python3
"""Rune manifest-based package generator.

Scans each Runes/* subdirectory for a ``manifest.json`` file and emits
a packages summary.  If no manifest is present the directory is skipped.

Output is printed as JSON to stdout (for CI / scripting) and also written
to ``Runes/packages.json``.
"""
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

RUNES_ROOT = Path(__file__).resolve().parent
OUTPUT_FILE = RUNES_ROOT / "packages.json"


def _find_manifests() -> List[Dict[str, Any]]:
    packages: List[Dict[str, Any]] = []
    for entry in sorted(RUNES_ROOT.iterdir()):
        if not entry.is_dir():
            continue
        mf = entry / "manifest.json"
        if not mf.is_file():
            continue
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
            data.setdefault("dir", entry.name)
            packages.append(data)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[WARN] Skipping {mf}: {exc}", file=sys.stderr)
    return packages


def main() -> None:
    pkgs = _find_manifests()
    summary = {
        "generated_by": "generate_packages.py",
        "count": len(pkgs),
        "packages": pkgs,
    }
    OUTPUT_FILE.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()