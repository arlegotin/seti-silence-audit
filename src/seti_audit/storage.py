"""Immutable hashed batches, atomic publication, and recoverable commit records."""

from contextlib import contextmanager
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

import numpy as np

from .artifacts import canonical_bytes, canonical_hash, read_json_checked, write_json_atomic
from .contracts import AuditCounts


@contextmanager
def _locked(root):
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".writer.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _fsync_dir(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _array_bytes(arrays):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in sorted(arrays.items()):
            if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
                raise ValueError("Unsafe array key")
            array = np.asarray(value)
            if array.dtype.hasobject:
                raise ValueError("Object arrays cannot be evidence")
            stream = io.BytesIO()
            np.save(stream, array, allow_pickle=False)
            info = zipfile.ZipInfo(name + ".npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, stream.getvalue())
    return output.getvalue()


def _append_commit(root, record):
    with (root / "commits.jsonl").open("ab") as stream:
        stream.write(canonical_bytes(record))
        stream.flush()
        os.fsync(stream.fileno())


def _read_commits(root):
    path = root / "commits.jsonl"
    if not path.exists():
        return {}
    content = path.read_bytes()
    records, valid = {}, 0
    lines = content.splitlines(keepends=True)
    for index, line in enumerate(lines):
        try:
            if not line.endswith(b"\n"):
                raise ValueError("Incomplete commit line")
            record = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            if index != len(lines) - 1:
                raise ValueError("Corrupted batch commit journal") from None
            # Preserve the interrupted bytes, then recover from hashed published
            # directories. A partial append must not destroy a committed batch.
            suffix = content[valid:]
            evidence = root / ("commits.interrupted." + hashlib.sha256(suffix).hexdigest() + ".bin")
            evidence.write_bytes(suffix)
            with path.open("r+b") as stream:
                stream.truncate(valid)
                stream.flush(); os.fsync(stream.fileno())
            break
        identifier = record["batch_id"]
        if identifier in records:
            raise ValueError("Duplicate batch commit record")
        records[identifier] = record
        valid += len(line)
    return records


def _load_one(path, protocol_hash):
    manifest = read_json_checked(path / "manifest.json")
    if manifest["batch_id"] != path.name:
        raise ValueError("Batch identity mismatch")
    payload = read_json_checked(path / "payload.json", manifest["payload_sha256"])
    if payload["protocol_hash"] != protocol_hash:
        raise ValueError("Batch protocol mismatch")
    content = (path / "arrays.npz").read_bytes()
    if hashlib.sha256(content).hexdigest() != manifest["arrays_sha256"]:
        raise ValueError("Batch array hash mismatch")
    with np.load(io.BytesIO(content), allow_pickle=False) as archive:
        arrays = {key: archive[key] for key in archive.files}
    for counts in payload.get("counts_by_cell", {}).values():
        AuditCounts(**counts)
    digest = canonical_hash(manifest)
    return payload | {"_batch_id": path.name, "_batch_hash": digest, "_arrays": arrays}


def commit_batch(output_dir: Path, batch_id: str, payload: dict, arrays: dict) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", batch_id) or batch_id in {".", ".."}:
        raise ValueError("Unsafe batch ID")
    if not isinstance(payload.get("protocol_hash"), str):
        raise ValueError("Batch requires protocol identity")
    payload_content, array_content = canonical_bytes(payload), _array_bytes(arrays)
    manifest = {"batch_id": batch_id, "protocol_hash": payload["protocol_hash"],
                "payload_sha256": hashlib.sha256(payload_content).hexdigest(),
                "arrays_sha256": hashlib.sha256(array_content).hexdigest()}
    digest = canonical_hash(manifest)
    root = Path(output_dir) / "checkpoints"
    with _locked(root):
        records = _read_commits(root)
        destination = root / batch_id
        if destination.exists():
            previous = _load_one(destination, payload["protocol_hash"])
            if previous["_batch_hash"] != digest:
                raise ValueError("Conflicting immutable batch payload")
        else:
            temporary = Path(tempfile.mkdtemp(prefix=".stage-", dir=root))
            try:
                for name, content in (("payload.json", payload_content), ("arrays.npz", array_content)):
                    with (temporary / name).open("wb") as stream:
                        stream.write(content); stream.flush(); os.fsync(stream.fileno())
                write_json_atomic(temporary / "manifest.json", manifest)
                _fsync_dir(temporary)
                os.rename(temporary, destination)
                _fsync_dir(root)
            finally:
                if temporary.exists():
                    shutil.rmtree(temporary)
        record = {"batch_id": batch_id, "batch_hash": digest}
        if batch_id in records and records[batch_id] != record:
            raise ValueError("Conflicting batch commit record")
        if batch_id not in records:
            _append_commit(root, record)
    return digest


def load_committed_batches(output_dir: Path, protocol_hash: str) -> tuple[dict, ...]:
    root = Path(output_dir) / "checkpoints"
    with _locked(root):
        records = _read_commits(root)
        rows = []
        for path in sorted(root.iterdir()):
            if not path.is_dir() or path.name.startswith("."):
                continue
            row = _load_one(path, protocol_hash)
            record = {"batch_id": path.name, "batch_hash": row["_batch_hash"]}
            if path.name in records and records[path.name] != record:
                raise ValueError("Batch manifest/commit hash mismatch")
            if path.name not in records:
                _append_commit(root, record)
            rows.append(row)
        if set(records) - {row["_batch_id"] for row in rows}:
            raise ValueError("Committed batch missing from storage")
    return tuple(rows)
