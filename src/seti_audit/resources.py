"""Append-only observational accounting; no execution quotas."""

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import importlib.metadata
import math
import os
import errno
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import uuid

from .artifacts import canonical_bytes, _reject_constant


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
        with self._locked():
            return self._records_unlocked()

    def _records_unlocked(self) -> list[dict]:
        if not self.path.exists():
            return []
        content=self.path.read_bytes();lines=content.splitlines(keepends=True)
        records=[];offset=0;tail=None;complete_tail=False
        for index,line in enumerate(lines):
            if not line.strip():
                offset+=len(line);continue
            try:
                record=json.loads(line,parse_constant=_reject_constant)
                if not isinstance(record,dict) or not isinstance(record.get('job_id'),str) or not isinstance(record.get('event'),str):
                    raise ValueError('Invalid resource record')
            except (ValueError,UnicodeDecodeError):
                if index!=len(lines)-1 or line.endswith(b'\n'):
                    raise ValueError('Corrupted resource journal in its complete prefix') from None
                tail=content[offset:];break
            records.append(record)
            if index==len(lines)-1 and not line.endswith(b'\n'):
                tail=content[offset:];complete_tail=True;break
            offset+=len(line)
        if tail is not None:
            digest=hashlib.sha256(tail).hexdigest()
            evidence=self.path.with_name(self.path.name+'.interrupted.'+digest+'.bin')
            if evidence.exists():
                if evidence.read_bytes()!=tail:raise ValueError('Conflicting interrupted resource evidence')
            else:
                with evidence.open('xb') as stream:
                    stream.write(tail);stream.flush();os.fsync(stream.fileno())
                directory=os.open(evidence.parent,os.O_RDONLY)
                try:os.fsync(directory)
                finally:os.close(directory)
            with self.path.open('r+b') as stream:
                if complete_tail:
                    stream.seek(0,os.SEEK_END);stream.write(b'\n')
                else:stream.truncate(offset)
                stream.flush();os.fsync(stream.fileno())
            self._append({'event':'journal_recovery','job_id':'journal-recovery:'+digest,
                          'details':{'interrupted_bytes':len(tail),'evidence':str(evidence),
                                     'preserved_complete_record':complete_tail}})
            return self._records_unlocked()
        return records

    def _append(self, value: dict):
        value = value | {"schema_version": 1, "recorded_utc": datetime.now(timezone.utc).isoformat()}
        with self.path.open("ab") as stream:
            stream.write(canonical_bytes(value))
            stream.flush()
            os.fsync(stream.fileno())

    def start(self, stage: str, ensemble_id: int | None = None, *, details: dict | None = None) -> str:
        job_id = str(uuid.uuid4())
        with self._locked():
            self._records_unlocked()
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
            records = self._records_unlocked()
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
            previous = [r for r in self._records_unlocked() if r["job_id"] == job_id]
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
            known = {r["job_id"] for r in self._records_unlocked()}
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


def resource_preflight(output_dir: Path, *, bytes_required: int = 1) -> dict:
    """Measure current physical capacity; no elapsed-time or workload policy."""
    if not isinstance(bytes_required, int) or isinstance(bytes_required, bool) or bytes_required < 0:
        raise ValueError("Nonnegative measured storage requirement needed")
    probe = Path(output_dir).resolve()
    while not probe.exists():
        probe = probe.parent
    disk = shutil.disk_usage(probe)
    available, source, error = None, None, None
    if sys.platform == "darwin":
        process = subprocess.run(["vm_stat"], capture_output=True, text=True, check=False)
        page_size = re.search(r"page size of (\d+) bytes", process.stdout)
        pages = {name: int(value) for name, value in re.findall(r"Pages (free|inactive|speculative):\s+(\d+)\.", process.stdout)}
        if process.returncode == 0 and page_size and len(pages) == 3:
            available = sum(pages.values()) * int(page_size.group(1))
            source = "vm_stat free+inactive+speculative; reclaimable-memory estimate"
        else:
            error = process.stderr.strip() or "vm_stat output unavailable"
    else:
        try:
            available = int(os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE"))
            source = "OS available physical pages"
        except (ValueError, OSError):
            error = "Available-memory probe unsupported"
    result = {"disk_total_bytes": disk.total, "disk_free_bytes": disk.free, "bytes_required": bytes_required,
              "available_memory_bytes": available, "memory_probe": source, "memory_probe_error": error}
    if disk.free < bytes_required:
        raise OSError(errno.ENOSPC, f"Measured free storage {disk.free} bytes is below the current {bytes_required}-byte requirement")
    return result


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
