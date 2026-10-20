"""Read-only runtime launcher. Installation is an explicit setup_env command."""
import importlib.util
import os
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    env_dir = root.parent / ".venv"
    env_python = env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    # Reuse an installed private environment; never create or install one.
    if env_python.is_file() and Path(sys.prefix).resolve() != env_dir.resolve():
        os.execv(str(env_python), [str(env_python), "-B", str(Path(__file__).resolve()), *sys.argv[1:]])
    if importlib.util.find_spec("lunar_python") is None:
        print("缺少 lunar-python。请先显式运行 scripts/setup_env.py；日常起盘不会安装依赖。", file=sys.stderr)
        return 2
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    from qimen.cli import main as chart_main
    return chart_main()


if __name__ == "__main__":
    raise SystemExit(main())
