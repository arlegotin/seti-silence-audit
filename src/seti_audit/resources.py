"""Append-only observational accounting; no execution quotas."""

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import math
import os
from pathlib import Path
import uuid

from .artifacts import canonical_bytes


class ResourceLedger:
    def __init__(self, path: Path):
        self.path = Path(path)

    @contextmanager
    def _locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.with_suffix(self.path.suffix + ".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def records(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]

    def _append(self, value: dict):
        value = value | {"schema_version": 1, "recorded_utc": datetime.now(timezone.utc).isoformat()}
        with self.path.open("ab") as stream:
            stream.write(canonical_bytes(value))
            stream.flush()
            os.fsync(stream.fileno())

    def start(self, stage: str, ensemble_id: int | None = None) -> str:
        job_id = str(uuid.uuid4())
        with self._locked():
            self._append({"event": "start", "job_id": job_id, "stage": stage,
                          "ensemble_id": ensemble_id, "pid": os.getpid()})
        return job_id

    def finish(self, job_id: str, elapsed_seconds: float, history_evaluations: int,
               download_bytes: int = 0, *, status: str = "complete", details: dict | None = None) -> None:
        if not math.isfinite(elapsed_seconds) or elapsed_seconds < 0:
            raise ValueError("Invalid elapsed duration")
        if any(not isinstance(v, int) or v < 0 for v in (history_evaluations, download_bytes)):
            raise ValueError("Usage counts must be nonnegative integers")
        with self._locked():
            records = self.records()
            if any(r["job_id"] == job_id and r["event"] in {"finish", "import"} for r in records):
                raise ValueError("Job already finished")
            if not any(r["job_id"] == job_id and r["event"] == "start" for r in records):
                raise ValueError("Unknown job ID")
            self._append({"event": "finish", "job_id": job_id, "elapsed_seconds": elapsed_seconds,
                          "history_evaluations": history_evaluations, "download_bytes": download_bytes,
                          "status": status, "details": details or {}})

    def pending_jobs(self) -> list[dict]:
        records = self.records()
        finished = {r["job_id"] for r in records if r["event"] == "finish"}
        return [r for r in records if r["event"] == "start" and r["job_id"] not in finished]

    def usage(self) -> dict:
        totals = {"elapsed_seconds": 0.0, "history_evaluations": 0, "download_bytes": 0}
        for record in self.records():
            if record["event"] in {"finish", "import"}:
                for key in totals:
                    totals[key] += record.get(key, 0)
        return totals

    def import_bootstrap(self, path: Path) -> int:
        if not Path(path).exists():
            return 0
        imported = 0
        with self._locked():
            known = {r["job_id"] for r in self.records()}
            for line in Path(path).read_text().splitlines():
                record = json.loads(line)
                identifier = "bootstrap:" + record["job_id"]
                if identifier not in known:
                    self._append(record | {"event": "import", "job_id": identifier})
                    known.add(identifier)
                    imported += 1
        return imported
