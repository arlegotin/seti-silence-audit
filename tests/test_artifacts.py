import json

import pytest


def test_canonical_hash_round_trip_and_content_check(tmp_path):
    from seti_audit.artifacts import canonical_hash, read_json_checked, write_json_atomic

    destination = tmp_path / "nested" / "result.json"
    digest = write_json_atomic(destination, {"schema_version": 1, "b": 2, "a": "é"})
    assert digest == canonical_hash({"a": "é", "b": 2, "schema_version": 1})
    assert read_json_checked(destination, digest)["a"] == "é"
    destination.write_text('{"schema_version":1,"a":"tampered","b":2}\n')
    with pytest.raises(ValueError, match="hash"):
        read_json_checked(destination, digest)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_value_cannot_replace_valid_artifact(tmp_path, value):
    from seti_audit.artifacts import write_json_atomic

    destination = tmp_path / "result.json"
    write_json_atomic(destination, {"value": 1})
    with pytest.raises(ValueError):
        write_json_atomic(destination, {"value": value})
    assert json.loads(destination.read_text()) == {"value": 1}


def test_nonfinite_external_json_is_rejected(tmp_path):
    from seti_audit.artifacts import read_json_checked

    destination = tmp_path / "bad.json"
    destination.write_text('{"value":NaN}')
    with pytest.raises(ValueError):
        read_json_checked(destination)
