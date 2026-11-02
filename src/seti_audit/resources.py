"""Append-only observational accounting; no execution quotas."""

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import importlib.metadata
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
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

    def start(self, stage: str, ensemble_id: int | None = None, *, details: dict | None = None) -> str:
        job_id = str(uuid.uuid4())
        with self._locked():
            self._append({"event": "start", "job_id": job_id, "stage": stage,
                          "ensemble_id": ensemble_id, "pid": os.getpid(), "details": details or {}})
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
            progress = [r for r in records if r["job_id"] == job_id and r["event"] == "progress"]
            if progress and (elapsed_seconds < progress[-1]["elapsed_seconds"]
                             or history_evaluations < progress[-1]["history_evaluations"]):
                raise ValueError("Final cumulative usage cannot decrease")
            self._append({"event": "finish", "job_id": job_id, "elapsed_seconds": elapsed_seconds,
                          "history_evaluations": history_evaluations, "download_bytes": download_bytes,
                          "status": status, "details": details or {}})

    def pending_jobs(self) -> list[dict]:
        records = self.records()
        finished = {r["job_id"] for r in records if r["event"] == "finish"}
        return [r for r in records if r["event"] == "start" and r["job_id"] not in finished]

    def progress(self, job_id: str, elapsed_seconds: float, history_evaluations: int,
                 *, details: dict | None = None) -> None:
        if (not math.isfinite(elapsed_seconds) or elapsed_seconds < 0
                or not isinstance(history_evaluations, int) or history_evaluations < 0):
            raise ValueError("Invalid cumulative progress")
        with self._locked():
            previous = [r for r in self.records() if r["job_id"] == job_id]
            if not previous or any(r["event"] == "finish" for r in previous):
                raise ValueError("Job absent or already finished")
            last = previous[-1]
            if elapsed_seconds < last.get("elapsed_seconds", 0) or history_evaluations < last.get("history_evaluations", 0):
                raise ValueError("Cumulative progress cannot decrease")
            self._append({"event": "progress", "job_id": job_id, "elapsed_seconds": elapsed_seconds,
                          "history_evaluations": history_evaluations, "details": details or {}})

    def usage(self) -> dict:
        totals = {"elapsed_seconds": 0.0, "history_evaluations": 0, "download_bytes": 0}
        latest = {}
        for record in self.records():
            if record["event"] in {"progress", "finish", "import"}:
                latest[record["job_id"]] = record
        for record in latest.values():
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


def physical_batch_size(desired: int, *, bytes_per_history: int, available_bytes: int) -> int:
    if desired <= 0 or bytes_per_history <= 0 or available_bytes < 0:
        raise ValueError("Invalid batch capacity input")
    count = min(desired, available_bytes // bytes_per_history)
    if count < 1:
        raise MemoryError("Available memory cannot hold one history batch element")
    return count


def inspect_environment() -> dict:
    import numpy
    import scipy

    errors = {}

    def probe(name, args):
        result = subprocess.run(args, capture_output=True, text=True, check=False)
        if result.returncode:
            errors[name] = result.stderr.strip()
            return None
        return result.stdout.strip()

    memory = probe("physical_memory", ["sysctl", "-n", "hw.memsize"]) if sys.platform == "darwin" else None
    cpu = probe("cpu_available", ["sysctl", "-n", "hw.logicalcpu"]) if sys.platform == "darwin" else os.cpu_count()
    power = probe("power", ["pmset", "-g", "custom"]) if sys.platform == "darwin" else "not macOS"
    builds = {}
    for name, module in [("numpy_build", numpy), ("scipy_build", scipy)]:
        builds[name] = module.show_config(mode="dicts")
    return {"schema_version": 1, "recorded_utc": datetime.now(timezone.utc).isoformat(),
            "architecture": platform.machine(), "python_version": platform.python_version(),
            "python_executable": sys.executable, "platform": platform.platform(),
            "physical_memory_bytes": int(memory) if memory else None,
            "cpu_available": int(cpu) if cpu else None,
            "disk_free_bytes": shutil.disk_usage(Path.cwd()).free,
            "packages": {name: importlib.metadata.version(name)
                         for name in ["numpy", "scipy", "matplotlib", "pytest", "mpmath"]},
            "power_settings": power, "probe_errors": errors,
            "thread_environment": {key: os.environ.get(key) for key in
                                   ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"]},
            "precision": "CPU binary64", **builds}
