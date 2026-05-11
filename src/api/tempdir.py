import os
import tempfile
from pathlib import Path


def _default_temp_candidates() -> list[Path]:
    """Return ordered fallback temp-directory candidates."""
    return [Path(tempfile.gettempdir()), Path("/tmp"), Path("/var/tmp"), Path("/usr/tmp")]


def _is_writable_dir(path: Path) -> bool:
    """Create directory (if needed) and verify write access."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False

    try:
        with tempfile.NamedTemporaryFile(dir=path, prefix=".hsds-write-test-", delete=True):
            pass
    except OSError:
        return False

    return True


def get_writable_temp_dir(env_var: str = "HSDS_TMP_DIR") -> str:
    """Resolve a writable temp directory for API file operations."""
    configured = os.getenv(env_var)
    if configured:
        candidate_paths = [Path(configured)]
    else:
        candidate_paths = _default_temp_candidates()

    for candidate in candidate_paths:
        if _is_writable_dir(candidate):
            return str(candidate)

    raise RuntimeError(
        f"No writable temporary directory available. Set {env_var} to a writable path. "
        f"Checked: {[str(path) for path in candidate_paths]}"
    )
