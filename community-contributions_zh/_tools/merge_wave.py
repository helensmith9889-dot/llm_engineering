#!/usr/bin/env python3
"""Merge batch_results/waveN_agent*.json into progress.json"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

TOOLS = Path(__file__).resolve().parent
wave_name = sys.argv[1] if len(sys.argv) > 1 else "wave1"
prog = json.loads((TOOLS / "teaching_annotate_progress.json").read_text(encoding="utf-8"))
results = [
    json.loads(p.read_text(encoding="utf-8"))
    for p in sorted((TOOLS / "batch_results").glob(f"{wave_name}_agent*.json"))
]
if not results:
    print("no results", wave_name)
    sys.exit(1)

prefix = f"{wave_name}-"
batches_path = TOOLS / f"{wave_name}_batches.json"
batch_by_agent: dict[str, list[str]] = {}
if batches_path.exists():
    batches = json.loads(batches_path.read_text(encoding="utf-8"))
    for i, batch in enumerate(batches):
        batch_by_agent[f"{wave_name}-agent{i}"] = batch


ROOT = TOOLS.parent


def resolve_path(rel: str, agent: str | None) -> str | None:
    # Accept absolute paths under ROOT
    try:
        p = Path(rel)
        if p.is_absolute():
            rel = str(p.resolve().relative_to(ROOT))
    except Exception:
        pass
    if rel in prog["files"]:
        return rel
    name = Path(rel).name
    # Prefer the agent's assigned batch (avoids basename collisions)
    if agent and agent in batch_by_agent:
        for cand in batch_by_agent[agent]:
            if Path(cand).name == name:
                return cand
    cands = [k for k in prog["files"] if Path(k).name == name]
    wave_cands = [k for k in cands if (prog["files"][k].get("agent") or "").startswith(prefix)]
    if len(wave_cands) == 1:
        return wave_cands[0]
    if len(cands) == 1:
        return cands[0]
    return None


for r in results:
    agent = r.get("agent")
    for rel in r.get("done", []):
        resolved = resolve_path(rel, agent)
        if resolved:
            prog["files"][resolved]["status"] = "done"
            prog["files"][resolved]["note"] = (r.get("notes") or "")[:200]
            prog["files"][resolved]["agent"] = agent
    for f in r.get("failed", []):
        rel = f["path"] if isinstance(f, dict) else f
        reason = f.get("reason", "") if isinstance(f, dict) else ""
        resolved = resolve_path(rel, agent) or (rel if rel in prog["files"] else None)
        if resolved:
            prog["files"][resolved]["status"] = "failed"
            prog["files"][resolved]["note"] = reason
            prog["files"][resolved]["agent"] = agent

for rel, meta in prog["files"].items():
    agent = meta.get("agent") or ""
    if agent.startswith(prefix) and meta["status"] == "in_progress":
        meta["status"] = "failed"
        meta["note"] = "no result from agent"

prog["updated_at"] = datetime.now(timezone.utc).isoformat()
prog["counts"] = {
    k: sum(1 for v in prog["files"].values() if v["status"] == k)
    for k in ("done", "pending", "in_progress", "failed", "skipped")
}
prog["counts"]["total"] = len(prog["files"])
(TOOLS / "teaching_annotate_progress.json").write_text(
    json.dumps(prog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps({"wave": wave_name, "counts": prog["counts"], "agents": len(results)}, ensure_ascii=False))
