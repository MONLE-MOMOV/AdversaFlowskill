"""全局配置管理。

读取环境变量和可选的 proagent.yaml 项目级配置。
优先级：环境变量 > 项目级 yaml > 默认值。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Settings:
    """ProAgent 全局配置."""

    # --- LLM 配置 ---
    model: str = "claude-opus-4-8"
    max_tokens: int = 16000
    thinking_type: str = "adaptive"  # "adaptive" | "disabled"
    effort: str = "high"  # low | medium | high | xhigh | max

    # --- 对抗辩论配置 ---
    max_debate_rounds: int = 3
    max_unit_redo_rounds: int = 3

    # --- 存储配置 ---
    projects_dir: str = "./projects"

    @classmethod
    def from_env(cls) -> "Settings":
        """从环境变量创建配置。"""
        return cls(
            model=os.getenv("PROAGENT_MODEL", "claude-opus-4-8"),
            max_tokens=int(os.getenv("PROAGENT_MAX_TOKENS", "16000")),
            thinking_type=os.getenv("PROAGENT_THINKING_TYPE", "adaptive"),
            effort=os.getenv("PROAGENT_EFFORT", "high"),
            max_debate_rounds=int(os.getenv("PROAGENT_MAX_DEBATE_ROUNDS", "3")),
            max_unit_redo_rounds=int(os.getenv("PROAGENT_MAX_UNIT_REDO", "3")),
            projects_dir=os.getenv("PROAGENT_PROJECTS_DIR", "./projects"),
        )

    def merge_yaml(self, yaml_data: dict[str, Any]) -> "Settings":
        """合并项目级 YAML 配置（优先级低于环境变量）。"""
        for key, value in yaml_data.items():
            if hasattr(self, key) and value is not None:
                env_val = os.getenv(f"PROAGENT_{key.upper()}")
                if env_val is None:
                    setattr(self, key, value)
        return self


# 全局默认配置实例
default_settings = Settings.from_env()
