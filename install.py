#!/usr/bin/env python3
"""Sourcerer automated installation script.

This script prepares a local Python virtual environment, installs all
backend and frontend dependencies, builds the frontend for production
and prints final instructions for running the application.
"""

import os
import sys
import subprocess
from pathlib import Path


def run(cmd, cwd=None):
    """Run a command and exit if it fails."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"Error while running: {' '.join(cmd)}")
        sys.exit(result.returncode)


def check_python():
    if sys.version_info < (3, 10):
        print("Python 3.10 or newer is required.")
        sys.exit(1)


def check_node():
    try:
        version = subprocess.check_output(["node", "--version"]).decode().strip().lstrip("v")
        major = int(version.split(".")[0])
        if major < 16:
            raise ValueError
    except Exception:
        print("Node.js 16 or newer is required. Please install it and rerun this script.")
        sys.exit(1)


def create_venv(venv_path: Path) -> Path:
    if not venv_path.exists():
        run([sys.executable, "-m", "venv", str(venv_path)])
    if os.name == "nt":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


if __name__ == "__main__":
    check_python()
    check_node()

    project_root = Path(__file__).parent.resolve()
    venv_dir = project_root / "venv"
    python_exe = create_venv(venv_dir)

    run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"])
    run([str(python_exe), "-m", "pip", "install", "-e", "."])

    frontend_dir = project_root / "frontend"
    run(["npm", "install"], cwd=frontend_dir)
    run(["npm", "run", "build"], cwd=frontend_dir)

    print("\nInstallation complete!\n")
    print("To start Sourcerer:")
    if os.name == "nt":
        print(f"  {venv_dir}\\Scripts\\activate && python run.py full")
    else:
        print(f"  source {venv_dir}/bin/activate && python run.py full")
