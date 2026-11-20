"""The owner's start scripts in scripts/: runnable, valid bash, strict mode, loopback only.

They are not run here: starting a real server would open a port, and the gates stay in-process.
"""

import os
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
COMMANDS = ["start.sh", "stop.sh", "restart.sh"]


@pytest.mark.parametrize("name", COMMANDS)
def test_each_command_is_executable_and_strict(name):
    path = SCRIPTS / name
    assert os.access(path, os.X_OK), name
    text = path.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash\n"), name
    assert "set -euo pipefail" in text, name


@pytest.mark.parametrize("name", [*COMMANDS, "_server.sh"])
def test_each_script_is_valid_bash(name):
    subprocess.run(["bash", "-n", str(SCRIPTS / name)], check=True)


def test_the_scripts_never_widen_the_host_or_print_the_env_file():
    for path in SCRIPTS.glob("*.sh"):
        text = path.read_text(encoding="utf-8")
        assert "0.0.0.0" not in text, path.name
        assert "cat .env" not in text and 'cat "$REPO/.env"' not in text, path.name
