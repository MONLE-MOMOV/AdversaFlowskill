"""JSON 文件持久化 —— 原子写入和备份。

使用 os.replace() 保证写入的原子性（POSIX 保证同一文件系统上的原子操作）。
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from proagent.models.state import PipelineState

logger = logging.getLogger(__name__)

STATE_FILENAME = "state.json"
BACKUP_SUFFIX = ".bak"


class StateStore:
    """流水线状态的 JSON 文件持久化。"""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.state_path = self.project_dir / STATE_FILENAME

    # ------------------------------------------------------------------
    # 读取
    # ------------------------------------------------------------------

    def load(self) -> Optional[PipelineState]:
        """加载项目状态。

        Returns:
            PipelineState 或 None（状态文件不存在时）
        """
        if not self.state_path.exists():
            logger.info("状态文件不存在: %s", self.state_path)
            return None

        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            return PipelineState(**data)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("状态文件损坏: %s", e)
            # 尝试从备份恢复
            return self._try_restore_from_backup()

    def _try_restore_from_backup(self) -> Optional[PipelineState]:
        """尝试从最近的备份恢复。"""
        backups = sorted(
            self.project_dir.glob(f"{STATE_FILENAME}{BACKUP_SUFFIX}.*"),
            key=os.path.getmtime,
            reverse=True,
        )
        for backup in backups:
            try:
                data = json.loads(backup.read_text(encoding="utf-8"))
                logger.warning("从备份恢复状态: %s", backup.name)
                return PipelineState(**data)
            except (json.JSONDecodeError, ValueError):
                continue
        logger.error("所有备份也损坏，无法恢复")
        return None

    # ------------------------------------------------------------------
    # 写入
    # ------------------------------------------------------------------

    def save(self, state: PipelineState) -> None:
        """原子化保存状态。

        1. 如有现有状态，先备份
        2. 写入临时文件
        3. 原子替换
        """
        self.project_dir.mkdir(parents=True, exist_ok=True)

        # 备份现有状态
        if self.state_path.exists():
            self._backup()

        # 更新元数据
        state.updated_at = datetime.now(timezone.utc)

        # 序列化
        json_str = state.model_dump_json(indent=2, ensure_ascii=False)

        # 写入临时文件后原子替换
        fd, tmp_path = tempfile.mkstemp(
            suffix=".tmp", prefix="state.", dir=self.project_dir
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(json_str)
            os.replace(tmp_path, str(self.state_path))
        finally:
            # 清理可能残留的临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        logger.info("状态已保存: %s", self.state_path)

    def _backup(self) -> None:
        """创建当前状态的备份。"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.project_dir / f"{STATE_FILENAME}{BACKUP_SUFFIX}.{timestamp}"
        try:
            backup_path.write_bytes(self.state_path.read_bytes())
            logger.debug("备份已创建: %s", backup_path)
        except OSError as e:
            logger.warning("备份失败: %s", e)

    # ------------------------------------------------------------------
    # 项目管理
    # ------------------------------------------------------------------

    @classmethod
    def create_project(
        cls,
        project_dir: Path,
        initial_requirement: str,
    ) -> tuple["StateStore", PipelineState]:
        """创建新的项目状态。

        Returns:
            (StateStore, PipelineState) 元组
        """
        state = PipelineState.create(initial_requirement)
        store = cls(project_dir)
        store.save(state)
        return store, state

    @classmethod
    def list_projects(cls, base_dir: Path) -> list[Path]:
        """列出所有项目目录。"""
        if not base_dir.exists():
            return []
        return sorted(
            p.parent
            for p in base_dir.rglob(STATE_FILENAME)
            if p.is_file()
        )
