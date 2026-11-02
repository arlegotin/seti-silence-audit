"""Command entry points for reproducible, locally logged research."""

import argparse
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time

from .resources import ResourceLedger


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m seti_audit")
    subcommands = parser.add_subparsers(dest="command", required=True)
    logged = subcommands.add_parser("run-logged", help="Run a command and preserve resource/exit records")
    logged.add_argument("--stage", required=True)
    logged.add_argument("--ledger", type=Path, default=Path("results/resources.jsonl"))
    logged.add_argument("args", nargs=argparse.REMAINDER)
    options = parser.parse_args(argv)
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
