import platform

import pytest


def test_environment_records_actual_machine_and_probe_failures():
    from seti_audit.resources import inspect_environment

    result = inspect_environment()
    assert result["architecture"] == platform.machine()
    assert result["disk_free_bytes"] > 0
    assert result["python_version"].startswith("3.")
    assert set(result["packages"]) >= {"numpy", "scipy", "matplotlib", "pytest", "mpmath"}
    if result["physical_memory_bytes"] is None:
        assert "physical_memory" in result["probe_errors"]
    else:
        assert result["physical_memory_bytes"] > 0
    assert "numpy_build" in result and "scipy_build" in result
    assert isinstance(result["numpy_build"], dict)
    assert isinstance(result["scipy_build"], dict)


def test_batch_sizing_uses_actual_available_capacity_without_work_quota():
    from seti_audit.resources import physical_batch_size

    assert physical_batch_size(4096, bytes_per_history=2048, available_bytes=8192) == 4
    assert physical_batch_size(4096, bytes_per_history=2048, available_bytes=2**36) == 4096
    with pytest.raises(MemoryError):
        physical_batch_size(4096, bytes_per_history=2048, available_bytes=1024)
