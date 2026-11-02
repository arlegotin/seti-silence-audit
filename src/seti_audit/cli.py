"""Command entry points for reproducible, locally logged research."""

import argparse
import json
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time

from .resources import ResourceLedger, inspect_environment
from .artifacts import write_json_atomic
from .contracts import load_protocol


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m seti_audit")
    subcommands = parser.add_subparsers(dest="command", required=True)
    logged = subcommands.add_parser("run-logged", help="Run a command and preserve resource/exit records")
    logged.add_argument("--stage", required=True)
    logged.add_argument("--ledger", type=Path, default=Path("results/resources.jsonl"))
    logged.add_argument("args", nargs=argparse.REMAINDER)
    environment = subcommands.add_parser("env", help="Record actual hardware and scientific environment")
    environment.add_argument("--out", type=Path, default=Path("results/environment.json"))
    theorem = subcommands.add_parser("theorem-check", help="Independently verify finite-age continuum formulas")
    theorem.add_argument("--deterministic", action="store_true")
    theorem.add_argument("--shell", action="store_true", help="Also run the finite-shell suppression reference")
    theorem.add_argument("--histories", type=int, default=10000)
    theorem.add_argument("--phase", choices=("development", "confirmation"), default="development")
    theorem.add_argument("--source", type=Path, default=Path("docs/silence_contact_theorem.pdf"))
    theorem.add_argument("--out", type=Path, default=Path("results/theorem"))
    for name in ("acquire", "validate-data"):
        command = subcommands.add_parser(name)
        command.add_argument("--config", type=Path, default=Path("config/protocol.json"))
    calibration = subcommands.add_parser("calibrate", help="Measure throughput and plan initial precision")
    calibration.add_argument("--config", type=Path, default=Path("config/protocol.json"))
    calibration.add_argument("--sizes", nargs="+", type=int, default=[1024, 4096, 16384])
    calibration.add_argument("--out", type=Path, default=Path("results/calibration.json"))
    pilot_command = subcommands.add_parser("pilot", help="Run development mechanism controls")
    pilot_command.add_argument("--config", type=Path, default=Path("config/protocol.json"))
    pilot_command.add_argument("--histories", type=int, default=1024)
    pilot_command.add_argument("--out", type=Path, default=Path("results/pilot.json"))
    options = parser.parse_args(argv)
    if options.command in {"calibrate", "pilot"}:
        from dataclasses import asdict
        from .data import load_catalog, load_schedule
        from .experiments import calibrate, pilot
        protocol = load_protocol(options.config)
        catalog = load_catalog(Path("docs/blueprint.md"), Path("data"))
        schedule = load_schedule(catalog, Path("inputs"), Path("data"))
        ledger = ResourceLedger(Path("results/resources.jsonl"))
        if options.command == "calibrate":
            result = calibrate(protocol, catalog, schedule, ledger, sizes=tuple(options.sizes))
            brief = {"projected_initial_seconds": result.projected_seconds, "rss_bytes": result.rss_bytes,
                     "initial_survivors": result.initial_survivors, "evidence_ids": result.evidence_ids}
        else:
            result = pilot(protocol, catalog, schedule, ledger, n_histories=options.histories)
            brief = {"passed": result.passed, "evidence_ids": result.evidence_ids}
        write_json_atomic(options.out, asdict(result))
        print(json.dumps(brief))
        return 0
    if options.command == "theorem-check":
        from .theorem import check_theorem
        ledger = ResourceLedger(Path("results/resources.jsonl"))
        job, start = ledger.start("G1"), time.perf_counter()
        try:
            result = check_theorem(options.source, options.out)
        except BaseException as exc:
            ledger.finish(job, time.perf_counter() - start, 0, status="failed",
                          details={"exception": type(exc).__name__})
            raise
        ledger.finish(job, time.perf_counter() - start, 0,
                      details={"artifact": str(options.out / "deterministic.json")})
        if options.shell:
            import numpy as np
            from .theorem import sample_shell, shell_evidence
            rows = []
            for index, h in enumerate((.02, .5)):
                root = [20261101, 0 if options.phase == "development" else 1, 9, index]
                sample = sample_shell({"h": h, "alpha": 1, "phase": options.phase},
                                      np.random.default_rng(root), options.histories, ledger)
                rows.append(shell_evidence(sample, h) | {"seed": root})
            write_json_atomic(options.out / f"shell-{options.phase}.json",
                              {"phase": options.phase, "horizons": rows,
                               "status": "sampled; uncertainty/validation assessed separately"})
        print(json.dumps({"status": result["status"], "checks": len(result["ratios"])}))
        return 0
    if options.command == "env":
        result = inspect_environment()
        write_json_atomic(options.out, result)
        print(json.dumps({key: result[key] for key in
                          ["architecture", "physical_memory_bytes", "disk_free_bytes", "packages"]}, indent=2))
        return 0
    if options.command in {"acquire", "validate-data"}:
        from .data import acquire_sources, load_catalog, load_schedule, validate_schedule
        protocol = load_protocol(options.config)
        catalog = load_catalog(Path("docs/blueprint.md"), Path("data"))
        if options.command == "acquire":
            result = acquire_sources(protocol, catalog, ResourceLedger(Path("results/resources.jsonl")))
            print(json.dumps({key: result[key] for key in
                              ["catalog_status", "schedule_grade", "detector_grade", "downloaded_bytes_this_job"]}, indent=2))
        else:
            schedule = load_schedule(catalog, Path("inputs"), Path("data"))
            result = validate_schedule(schedule, catalog, schedule.provenance | {"kind": "observing_log"})
            write_json_atomic(Path("data/schedule_validation.json"), result)
            print(json.dumps(result, indent=2))
        return 0
    if options.command == "run-logged":
        command = options.args[1:] if options.args[:1] == ["--"] else options.args
        if not command:
            parser.error("run-logged requires a command after --")
        ledger = ResourceLedger(options.ledger)
        ledger.import_bootstrap(Path("results/bootstrap-usage.jsonl"))
        job = ledger.start(options.stage)
        start = time.perf_counter()
        try:
            result = subprocess.run(command, check=False)
        except BaseException as exc:
            ledger.finish(job, time.perf_counter() - start, 0, status="interrupted",
                          details={"exception": type(exc).__name__})
            raise
        ledger.finish(job, time.perf_counter() - start, 0,
                      status="complete" if result.returncode == 0 else "failed",
                      details={"returncode": result.returncode, "command": command,
                               "max_rss_bytes": int(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
                                                    * (1 if sys.platform == "darwin" else 1024)),
                               "free_disk_bytes": shutil.disk_usage(Path.cwd()).free})
        return result.returncode
    return 2
