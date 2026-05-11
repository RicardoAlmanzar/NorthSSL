from collections.abc import Sequence
from pathlib import Path
from subprocess import CompletedProcess, run

def run_command(arguments: Sequence[str], *, cwd: str | Path | None = None, timeout: int | None = None) -> CompletedProcess[str]:
    return run(
        list(arguments),
        check=False,
        capture_output=True,
        cwd=str(cwd) if cwd is not None else None,
        text=True,
        timeout=timeout,
    )
