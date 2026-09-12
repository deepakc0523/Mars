#!/usr/bin/env python3
"""
dev-setup.py — One-shot development environment setup for MARS backend.

This script:
  1. Checks that Python >= 3.11 is available
  2. Creates a virtual environment in backend/.venv
  3. Installs backend/requirements.txt
  4. Copies .env.example to backend/.env if it does not exist

Run from the repository root:
    python scripts/dev_setup.py
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
BACKEND_DIR = REPO_ROOT / "backend"
VENV_DIR = BACKEND_DIR / ".venv"
REQUIREMENTS = BACKEND_DIR / "requirements.txt"
ENV_EXAMPLE = REPO_ROOT / ".env.example"
ENV_FILE = BACKEND_DIR / ".env"


def check_python() -> None:
    v = sys.version_info
    if v < (3, 11):
        print(f"❌  Python 3.11+ is required. Found {v.major}.{v.minor}.")
        sys.exit(1)
    print(f"✅  Python {v.major}.{v.minor}.{v.micro}")


def create_venv() -> None:
    if VENV_DIR.exists():
        print(f"⏭   Virtual environment already exists: {VENV_DIR}")
        return
    print(f"🔧  Creating virtual environment at {VENV_DIR} …")
    subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
    print("✅  Virtual environment created.")


def pip_install() -> None:
    if sys.platform == "win32":
        pip = VENV_DIR / "Scripts" / "pip.exe"
    else:
        pip = VENV_DIR / "bin" / "pip"

    print("📦  Installing backend dependencies …")
    subprocess.run(
        [str(pip), "install", "--upgrade", "pip", "--quiet"], check=True
    )
    subprocess.run(
        [str(pip), "install", "-r", str(REQUIREMENTS)], check=True
    )
    print("✅  Dependencies installed.")


def copy_env() -> None:
    if ENV_FILE.exists():
        print(f"⏭   {ENV_FILE} already exists — skipping.")
        return
    import shutil
    shutil.copy(ENV_EXAMPLE, ENV_FILE)
    print(f"✅  Created {ENV_FILE} from .env.example.")
    print("⚠️   Remember to fill in your API keys in backend/.env")


def main() -> None:
    print("═" * 50)
    print("  MARS Dev Setup")
    print("═" * 50)
    check_python()
    create_venv()
    pip_install()
    copy_env()
    print()
    print("🚀  Setup complete!")
    print()
    print("To start the backend:")
    if sys.platform == "win32":
        print("  cd backend && .venv\\Scripts\\activate && uvicorn main:app --reload")
    else:
        print("  cd backend && source .venv/bin/activate && uvicorn main:app --reload")


if __name__ == "__main__":
    main()
