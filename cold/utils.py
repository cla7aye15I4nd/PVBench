import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from patchagent.builder.utils import BuilderProcessError, BuilderTimeoutError


def backdoor_subprocess_run(
    command: List,
    cwd: Path,
    input: Optional[bytes] = None,
    timeout: Optional[float] = None,
    env: Optional[Dict[str, Any]] = None,
) -> Tuple[bytes, bytes]:
    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            input=input,
            capture_output=True,
            text=False,
            check=True,
            timeout=timeout,
            env=env,
        )

        return process.stdout, process.stderr
    except subprocess.CalledProcessError as e:
        stdout = e.stdout.decode(errors="ignore") if e.stdout else ""
        stderr = e.stderr.decode(errors="ignore") if e.stderr else ""

        raise BuilderProcessError(
            message=f"Return code {e.returncode}",
            command=command,
            cwd=cwd,
            stdout=stdout,
            stderr=stderr,
        )
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout.decode(errors="ignore") if e.stdout else ""
        stderr = e.stderr.decode(errors="ignore") if e.stderr else ""

        raise BuilderTimeoutError(
            message=f"Timeout after {e.timeout} seconds",
            command=command,
            cwd=cwd,
            stdout=stdout,
            stderr=stderr,
        )
