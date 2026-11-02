"""Canonical, finite JSON and durable atomic replacement."""

import hashlib
import json
import os
from pathlib import Path
import tempfile


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


def canonical_hash(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def write_json_atomic(path: Path, value: object) -> str:
    content = canonical_bytes(value)  # Validate before touching a valid destination.
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.",
                                         suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return hashlib.sha256(content).hexdigest()


def _reject_constant(value: str):
    raise ValueError(f"Nonfinite JSON constant: {value}")


def read_json_checked(path: Path, expected_hash: str | None = None) -> dict:
    content = Path(path).read_bytes()
    if expected_hash is not None and hashlib.sha256(content).hexdigest() != expected_hash:
        raise ValueError(f"Artifact hash mismatch: {path}")
    value = json.loads(content, parse_constant=_reject_constant)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value
