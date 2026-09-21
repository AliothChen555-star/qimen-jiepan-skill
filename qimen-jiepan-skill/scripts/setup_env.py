import hashlib
import os
import subprocess
import sys
import venv
from pathlib import Path


def main() -> None:
    quiet = "--quiet" in sys.argv[1:]
    skill_root = Path(__file__).resolve().parent.parent
    requirements = skill_root / "requirements.txt"
    env_dir = skill_root / ".venv"
    env_python = env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    marker = env_dir / ".requirements.sha256"

    if not requirements.is_file():
        raise FileNotFoundError(f"Missing dependency manifest: {requirements}")

    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    if not env_python.is_file():
        venv.EnvBuilder(with_pip=True, clear=False).create(env_dir)

    if not marker.is_file() or marker.read_text(encoding="ascii").strip() != digest:
        subprocess.run(
            [str(env_python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(requirements)],
            check=True,
            stdout=subprocess.DEVNULL if quiet else None,
        )
        marker.write_text(digest + "\n", encoding="ascii")

    if not quiet:
        print(env_python)


if __name__ == "__main__":
    main()
