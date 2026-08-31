"""Append-only JSONL event history plus per-job manifests."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path


class JobStore:
    def __init__(self, root: Path):
        self.root = root
        self.jobs_dir = root / "jobs"
        self.events_file = root / "events.jsonl"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def write(self, job: dict) -> None:
        path = self.jobs_dir / f"{job['id']}.json"
        temp = path.with_suffix(".tmp")
        with self._lock:
            temp.write_text(json.dumps(job, indent=2, sort_keys=True), encoding="utf-8")
            temp.replace(path)

    def get(self, job_id: str) -> dict | None:
        path = self.jobs_dir / f"{job_id}.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list(self, limit: int = 30) -> list[dict]:
        paths = sorted(self.jobs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        return [json.loads(p.read_text(encoding="utf-8")) for p in paths[:limit]]

    def event(self, job_id: str, event: str, details: dict | None = None) -> None:
        record = {
            "at": datetime.now(timezone.utc).isoformat(),
            "job_id": job_id,
            "event": event,
            "details": details or {},
        }
        with self._lock:
            with self.events_file.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
