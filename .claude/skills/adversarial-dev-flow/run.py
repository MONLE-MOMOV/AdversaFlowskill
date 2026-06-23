#!/usr/bin/env python3
"""Skill 入口 —— 桥接到 proagent CLI。

Claude Code 通过 /adversarial-dev-flow 调用此脚本。
使用方式:
  python3 run.py start --project <dir> --requirement "..."
  python3 run.py status --project <dir>
  python3 run.py resume --project <dir>
  python3 run.py jump --project <dir> --phase <1-7>
"""

import os
import sys

# 自动推导项目根目录并加入 PYTHONPATH
_skill_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_skill_dir, "..", "..", ".."))
_src_dir = os.path.join(_project_root, "src")

if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from proagent.main import cli

if __name__ == "__main__":
    cli()
