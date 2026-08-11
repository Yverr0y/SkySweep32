"""PlatformIO pre-build gate for the canonical Rev C hardware contract."""

from pathlib import Path
import subprocess
import sys

Import("env")  # type: ignore[name-defined]  # Provided by PlatformIO/SCons.

project_dir = Path(env.subst("$PROJECT_DIR"))  # type: ignore[name-defined]
generator = project_dir / "scripts" / "generate_rev_c_pinmap.py"
subprocess.run(
    [sys.executable, str(generator), "--check"],
    cwd=project_dir,
    check=True,
)
