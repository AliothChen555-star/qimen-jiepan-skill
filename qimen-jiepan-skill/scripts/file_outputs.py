"""Protect frozen inputs when a derived-data command writes its output."""
import os
from pathlib import Path


def ensure_distinct_output(source, output):
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError("输出路径不得覆盖原盘；请指定不同的派生结果文件")
    if source.exists() and output.exists() and os.path.samefile(source, output):
        raise ValueError("输出与原盘指向同一文件；请勿通过硬链接覆盖原盘")

