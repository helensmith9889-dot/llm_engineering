#!/usr/bin/env python3
"""Assign next wave batches from teaching_annotate_progress.json"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

TOOLS = Path(__file__).resolve().parent
prog = json.loads((TOOLS / "teaching_annotate_progress.json").read_text(encoding="utf-8"))
WAVE_AGENTS = int(sys.argv[1]) if len(sys.argv) > 1 else 4
NORMAL = 3
LARGE = 80 * 1024
wave_name = sys.argv[2] if len(sys.argv) > 2 else "wave"

pending = [r for r in prog["order"] if prog["files"][r]["status"] == "pending"]
wave = []
remaining = pending[:]
for _ in range(WAVE_AGENTS):
    batch = []
    while remaining and len(batch) < NORMAL:
        rel = remaining[0]
        sz = prog["files"][rel].get("bytes") or 0
        if sz >= LARGE and batch:
            break
        remaining.pop(0)
        batch.append(rel)
        if sz >= LARGE:
            break
    if batch:
        wave.append(batch)
    else:
        break

for i, batch in enumerate(wave):
    for rel in batch:
        prog["files"][rel]["status"] = "in_progress"
        prog["files"][rel]["agent"] = f"{wave_name}-agent{i}"

prog["updated_at"] = datetime.now(timezone.utc).isoformat()
prog["counts"] = {
    k: sum(1 for v in prog["files"].values() if v["status"] == k)
    for k in ("done", "pending", "in_progress", "failed", "skipped")
}
prog["counts"]["total"] = len(prog["files"])
(TOOLS / "teaching_annotate_progress.json").write_text(
    json.dumps(prog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
out = TOOLS / f"{wave_name}_batches.json"
out.write_text(json.dumps(wave, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"counts": prog["counts"], "batches": wave}, ensure_ascii=False, indent=2))
