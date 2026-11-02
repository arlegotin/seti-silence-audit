"""Immutable hashed batches, atomic publication, and recoverable commit records."""

from contextlib import contextmanager
import fcntl
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid
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


def _missing_store():
    return FileNotFoundError('Restore the required checkpoint state and raw checkpoint store before resuming; saved aggregates support report regeneration, not replacement sampling.')


def _store_identity(output, root, protocol_hash, *, create):
    outside=output/'checkpoint_store.json';inside=root/'.store.json'
    if outside.exists():
        identity=read_json_checked(outside)
        if not inside.exists():raise _missing_store()
        if read_json_checked(inside)!=identity:raise ValueError('Checkpoint store identity mismatch')
    elif inside.exists():
        identity=read_json_checked(inside)
        write_json_atomic(outside,identity)
    elif create:
        identity={'schema_version':1,'protocol_hash':protocol_hash,'store_id':str(uuid.uuid4())}
        # Inner identity first: an interrupted initialization can reconstruct
        # its outer marker, never silently reconstruct a lost data store.
        write_json_atomic(inside,identity);write_json_atomic(outside,identity)
    else:
        return
    if identity.get('protocol_hash')!=protocol_hash or not identity.get('store_id'):
        raise ValueError('Checkpoint store protocol/identity mismatch')


def verify_checkpoint_references(output_dir, protocol_hash, batches, ledger=None):
    """Require every externally recorded committed batch before simulation.

    Legacy stores lack the identity pair. Their completed snapshots and job
    records still bind prior evidence, including compressed published results.
    """
    output=Path(output_dir);by_id={b['_batch_id']:b for b in batches}
    hashes={b['_batch_hash'] for b in batches};required_hashes=set();required_ids={};payloads={}
    paths={output/name for name in ('confirmation.json','checkpoint_summary.json','result.json','execution_totals.json') if (output/name).exists()}
    paths.update(output.glob('checkpoint-*.json'));paths.update(output.glob('checkpoint-*.json.gz'))
    for folder in ('summaries','completed_snapshots'):
        paths.update((output/folder).glob('*.json'));paths.update((output/folder).glob('*.json.gz'))
    for path in sorted(paths):
        if path.suffix=='.gz':
            value=json.loads(gzip.decompress(path.read_bytes()))
        else:value=read_json_checked(path)
        if value.get('protocol_hash') not in (None,protocol_hash):raise ValueError('Saved checkpoint protocol mismatch')
        if 'content_hash' in value and value['content_hash']!=canonical_hash({k:v for k,v in value.items() if k!='content_hash'}):
            raise ValueError('Saved checkpoint content hash mismatch')
        required_hashes.update(value.get('batch_hashes',()))
        for meta in value.get('batches',()):
            identifier=meta.get('_batch_id',meta.get('batch_id'))
            if identifier:
                digest=meta.get('_batch_hash',meta.get('batch_hash'))
                if identifier in required_ids and digest and required_ids[identifier] not in (None,digest):
                    raise ValueError('Conflicting saved batch references')
                required_ids[identifier]=digest or required_ids.get(identifier)
        for meta in value.get('all_published_batches',()):
            identifier=meta['batch_id'];required_ids.setdefault(identifier,None)
            payloads[identifier]=meta['payload_sha256']
    if ledger is not None:
        records=ledger.records()
        own={r['job_id'] for r in records if r['event']=='start' and r.get('details',{}).get('protocol_hash')==protocol_hash}
        for record in records:
            details=record.get('details',{})
            if record['job_id'] in own and record['event']=='finish' and details.get('batch_id'):
                required_ids[details['batch_id']]=details['batch_hash']
    if required_hashes-hashes or set(required_ids)-set(by_id):raise _missing_store()
    for identifier,digest in required_ids.items():
        if digest is not None and by_id[identifier]['_batch_hash']!=digest:
            raise ValueError('Stored batch differs from saved evidence')
    for identifier,digest in payloads.items():
        manifest=read_json_checked(output/'checkpoints'/identifier/'manifest.json')
        if manifest['payload_sha256']!=digest:raise ValueError('Stored payload differs from execution records')
    grouped={}
    for batch in batches:
        if 'batch_index' in batch:
            key=batch.get('group_id',batch.get('model_id'))
            grouped.setdefault(key,[]).append(batch['batch_index'])
    if any(sorted(indices)!=list(range(len(indices))) for indices in grouped.values()):raise _missing_store()


def verify_checkpoint_progress(batches, initials, looks, *, group_key):
    if set(initials)!=set(looks) or any(not isinstance(j,int) or isinstance(j,bool) or j<1 for j in looks.values()):
        raise ValueError('Checkpoint state groups/indices differ from the frozen experiment')
    advanced=any(j>1 for j in looks.values())
    for group,initial in initials.items():
        count=sum(b['sample_size'] for b in batches if b[group_key]==group)
        look=looks[group];minimum=initial*2**(look-2) if look>1 else (initial if advanced else 0)
        if count<minimum or count>initial*2**(look-1):raise _missing_store()


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
        _store_identity(Path(output_dir),root,payload['protocol_hash'],create=True)
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
    if not root.exists() and any((Path(output_dir)/name).exists() for name in ('run_state.json','state.json','checkpoint_store.json')):
        raise _missing_store()
    with _locked(root):
        _store_identity(Path(output_dir),root,protocol_hash,create=False)
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
