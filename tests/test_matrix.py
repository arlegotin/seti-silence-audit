from collections import defaultdict


def test_complete_matrix_preserves_scientific_combinations(repo_root, tmp_path):
    from seti_audit.contracts import load_protocol
    from seti_audit.data import load_catalog, load_schedule
    from seti_audit.experiments import build_matrix, build_bound_registry

    protocol = load_protocol(repo_root / "config/protocol.json")
    catalog = load_catalog(repo_root / "docs/blueprint.md", tmp_path / "data")
    schedule = load_schedule(catalog, tmp_path / "inputs", tmp_path / "data")
    cells = build_matrix(protocol, schedule)
    assert len({c["cell_id"] for c in cells}) == len(cells)
    assert {c["model_id"] for c in cells if c["model_kind"] == "interacting"} == set(range(20))
    assert {c["model_id"] for c in cells if c["model_kind"] == "ideal_silence"} == set(range(16))
    assert len([c for c in cells if c["model_kind"] == "ideal_silence"]) == 48
    assert all(c["emission_id"] in ("E0", "E1") for c in cells if c["future_multiplier"] != 1)
    assert all(c["emission_id"] == "E1" and c["detector_id"] in ("Dnom", "Dweak", "Dhigh")
               for c in cells if c["model_id"] >= 16)
    for kind in ("interacting", "independent_sites"):
        for model_id in range(16):
            main = [c for c in cells if c["model_kind"] == kind and c["model_id"] == model_id
                    and c["future_multiplier"] == 1]
            for emission in ("E1", "E2", "E3", "E4", "E5"):
                assert {c["detector_id"] for c in main if c["emission_id"] == emission} >= {"Dnom", "Dweak", "Dhigh", "Dpositive", "Duncal"}
    registry = build_bound_registry(cells)
    for pool, value in registry["pools"].items():
        assert value["A"] == .025
        assert value["M"] == sum(i["pool"] == pool for i in registry["items"].values())
    # Future continuation cannot allocate the shared past likelihood again.
    selected = [c for c in cells if c["model_kind"] == "interacting" and c["model_id"] == 0
                and c["emission_id"] == "E1" and c["detector_id"] == "Dnom"]
    assert len({c["interval_ids"]["null_low"] for c in selected}) == 1
    assert all(c["thresholds"] == [.01, .05, .1] for c in cells)
