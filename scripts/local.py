"""Run a command with project-local environment values without logging secrets."""
import os
import subprocess
import sys
from pathlib import Path

if Path(".env").exists():
    for line in Path(".env").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)
raise SystemExit(subprocess.call(sys.argv[1:]))
