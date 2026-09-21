import os
import subprocess
import sys
from pathlib import Path


root = Path(__file__).resolve().parent
skill_root = root.parent
venv_dir = skill_root / ".venv"
venv_python = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

if Path(sys.prefix).resolve() != venv_dir.resolve():
    subprocess.run([sys.executable, str(root / "setup_env.py"), "--quiet"], check=True)
    os.execv(str(venv_python), [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]])

sys.path.insert(0, str(root))
from qimen.cli import main


if __name__ == "__main__":
    main()
