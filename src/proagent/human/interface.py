"""人机交互接口 —— HumanInTheLoop。

支持三种模式：
- interactive: 终端交互式输入（默认，适合独立使用）
- file_driven: 从 JSON 文件读取预置答案（用于脚本/CI）
- claude_code: Claude Code 适配模式（通过 stdout 协议通信）
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Callable

from proagent.models.state import HumanDecision, UnresolvedItem

logger = logging.getLogger(__name__)

# Claude Code 协议标记
PROTOCOL_MARKER = "__PROAGENT_NEEDS_HUMAN__"
PROTOCOL_END = "__PROAGENT_END_ACTION__"


class HumanQuestion:
    """人工问题。"""

    def __init__(
        self,
        question_id: str,
        prompt: str,
        options: list[str] | None = None,
        default: str = "",
    ):
        self.question_id = question_id
        self.prompt = prompt
        self.options = options or []
        self.default = default


class HumanAnswer:
    """人工回答。"""

    def __init__(self, question_id: str, value: str, notes: str = ""):
        self.question_id = question_id
        self.value = value
        self.notes = notes


class BaseHumanInterface:
    """人机交互接口基类。"""

    def ask(self, question: HumanQuestion) -> HumanAnswer:
        raise NotImplementedError

    def adjudicate(
        self, unresolved_items: list[UnresolvedItem]
    ) -> list[HumanDecision]:
        raise NotImplementedError

    def confirm(self, summary: str) -> bool:
        raise NotImplementedError

    def report_progress(self, message: str) -> None:
        print(f"\n📊 {message}")


class HumanInTheLoop(BaseHumanInterface):
    """交互模式 —— 终端 input() 阻塞等待。

    适合独立使用（不在 Claude Code 中）。
    """

    def __init__(self):
        pass

    def ask(self, question: HumanQuestion) -> HumanAnswer:
        print()
        print("─" * 60)
        print(f"❓ {question.prompt}")
        if question.options:
            for i, opt in enumerate(question.options, 1):
                print(f"   [{i}] {opt}")
        print("─" * 60)

        while True:
            try:
                raw = input("> ").strip()
                if not raw and question.default:
                    return HumanAnswer(question.question_id, question.default)
                if question.options:
                    idx = int(raw) - 1
                    if 0 <= idx < len(question.options):
                        raw = question.options[idx]
                    else:
                        print(f"请输入 1-{len(question.options)}")
                        continue
                return HumanAnswer(question.question_id, raw)
            except (ValueError, EOFError):
                print("请输入有效值")
            except KeyboardInterrupt:
                print("\n用户中断")
                sys.exit(1)

    def adjudicate(
        self, unresolved_items: list[UnresolvedItem]
    ) -> list[HumanDecision]:
        decisions: list[HumanDecision] = []
        if not unresolved_items:
            return decisions

        print()
        print("=" * 60)
        print(f"⚠️  需要人工裁决 —— {len(unresolved_items)} 项未解决的争议")
        print("=" * 60)

        for i, item in enumerate(unresolved_items):
            print()
            print(f"--- 争议 {i + 1}/{len(unresolved_items)} ---")
            c = item.challenge
            print(f"问题条目: {c.get('item', 'N/A')}")
            print(f"严重程度: {c.get('severity', 'N/A')}")
            print(f"挑战理由: {c.get('rationale', 'N/A')}")
            print(f"建议方案: {c.get('suggestion', 'N/A')}")
            print(f"僵局原因: {item.reason}")
            if item.response:
                print(f"提案方回应: {item.response.get('action', 'N/A')}")

            print()
            print("请裁决: [a] 采纳挑战方  [r] 接受提案方  [o] 自定义")

            while True:
                try:
                    choice = input("> ").strip().lower()
                    if choice == "a":
                        decisions.append(HumanDecision(
                            item_reference=str(c.get("item", "")),
                            decision="approved", notes="采纳挑战方意见"))
                        break
                    elif choice == "r":
                        decisions.append(HumanDecision(
                            item_reference=str(c.get("item", "")),
                            decision="rejected", notes="接受提案方方案"))
                        break
                    elif choice == "o":
                        notes = input("自定义裁决说明: ").strip()
                        decisions.append(HumanDecision(
                            item_reference=str(c.get("item", "")),
                            decision="overridden", notes=notes))
                        break
                    else:
                        print("请输入 a/r/o")
                except (EOFError, KeyboardInterrupt):
                    print("\n跳过此项")
                    break

        print(f"\n✅ 人工裁决完成: {len(decisions)} 项")
        return decisions

    def confirm(self, summary: str) -> bool:
        print()
        print("=" * 60)
        print(summary)
        print("=" * 60)
        print("请输入 y(是) / n(否): ")

        while True:
            try:
                choice = input("> ").strip().lower()
                if choice in ("y", "yes"):
                    return True
                elif choice in ("n", "no"):
                    return False
                print("请输入 y 或 n")
            except (EOFError, KeyboardInterrupt):
                return False


class FileDrivenInterface(BaseHumanInterface):
    """文件驱动模式 —— 从 JSON 文件读取预置答案。

    适合脚本和 CI 环境。
    """

    def __init__(self, answers: dict[str, str] | None = None, answers_file: Path | None = None):
        self.answers: dict[str, str] = {}
        if answers:
            self.answers.update(answers)
        if answers_file:
            self._load(answers_file)

    def _load(self, path: Path) -> None:
        if not path.exists():
            logger.warning("答案文件不存在: %s", path)
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            self.answers.update({str(k): str(v) for k, v in data.items()})

    def ask(self, question: HumanQuestion) -> HumanAnswer:
        value = self.answers.get(question.question_id, question.default)
        return HumanAnswer(question.question_id, value)

    def adjudicate(self, unresolved_items) -> list[HumanDecision]:
        decisions = []
        for i, item in enumerate(unresolved_items):
            ref = str(item.challenge.get("item", f"item_{i}"))
            choice = self.answers.get(ref, self.answers.get(f"adjudicate_{i}", "a"))
            if choice == "a":
                decisions.append(HumanDecision(
                    item_reference=ref, decision="approved",
                    notes="采纳挑战方意见（文件驱动）"))
            elif choice == "r":
                decisions.append(HumanDecision(
                    item_reference=ref, decision="rejected",
                    notes="接受提案方方案（文件驱动）"))
            else:
                decisions.append(HumanDecision(
                    item_reference=ref, decision="overridden",
                    notes=choice))
        return decisions

    def confirm(self, summary: str) -> bool:
        raw = self.answers.get("confirm", "yes").lower()
        return raw in ("yes", "y", "true", "1")


class ClaudeCodeInterface(BaseHumanInterface):
    """Claude Code 适配模式 —— 通过 stdout 协议通信。

    不阻塞 stdin。当需要人工输入时：
    1. 将问题信息写入 state 的 pending_human_action 字段
    2. 打印 __PROAGENT_NEEDS_HUMAN__ 协议标记 + JSON 问题
    3. 调用 save_callback 触发状态持久化
    4. 返回 sentinel 值（confirm 返回 False，adjudicate 返回空列表）

    Claude Code 读取 stdout 后向用户展示问题，
    用户答复后，Claude Code 写入答案文件并重新调用 CLI。
    """

    def __init__(
        self,
        save_callback: Callable[[], None] | None = None,
        project_dir: Path | None = None,
    ):
        self._save_callback = save_callback
        self._project_dir = project_dir
        self._pending_action: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # 协议输出
    # ------------------------------------------------------------------

    def _emit_action(self, action: dict[str, Any]) -> None:
        """输出协议标记和 JSON 问题块到 stdout。"""
        self._pending_action = action
        print()
        print(PROTOCOL_MARKER)
        print(json.dumps(action, ensure_ascii=False, indent=2))
        print(PROTOCOL_END)
        print()
        sys.stdout.flush()

        # 触发状态保存
        if self._save_callback:
            self._save_callback()

    # ------------------------------------------------------------------
    # 交互实现
    # ------------------------------------------------------------------

    def ask(self, question: HumanQuestion) -> HumanAnswer:
        self._emit_action({
            "action_type": "ask",
            "question_id": question.question_id,
            "prompt": question.prompt,
            "options": question.options,
            "default": question.default,
        })
        return HumanAnswer(question.question_id, "")

    def confirm(self, summary: str) -> bool:
        self._emit_action({
            "action_type": "confirm",
            "summary": summary,
        })
        return False  # 返回 False 表示 "未确认"，触发暂停

    def adjudicate(
        self, unresolved_items: list[UnresolvedItem]
    ) -> list[HumanDecision]:
        items_data = []
        for i, item in enumerate(unresolved_items):
            items_data.append({
                "index": i,
                "item_ref": item.challenge.get("item", f"item_{i}"),
                "severity": item.challenge.get("severity", "N/A"),
                "challenge": item.challenge.get("rationale", ""),
                "suggestion": item.challenge.get("suggestion", ""),
                "proposer_action": item.response.get("action", ""),
                "proposer_rationale": item.response.get("rationale", ""),
                "deadlock_reason": item.reason,
            })

        self._emit_action({
            "action_type": "adjudicate",
            "item_count": len(items_data),
            "items": items_data,
        })
        return []  # 返回空列表表示 "未裁决"

    # ------------------------------------------------------------------
    # 属性
    # ------------------------------------------------------------------

    @property
    def pending_action(self) -> dict[str, Any] | None:
        return self._pending_action


# ============================================================
# 工厂函数
# ============================================================

def create_interface(
    mode: str = "interactive",
    answers_file: Path | None = None,
    answers_dict: dict[str, str] | None = None,
    save_callback: Callable[[], None] | None = None,
    project_dir: Path | None = None,
) -> BaseHumanInterface:
    """创建人机交互接口。

    Args:
        mode: "interactive" | "file_driven" | "claude_code"
        answers_file: 文件驱动模式的答案文件路径
        answers_dict: 文件驱动模式的答案字典
        save_callback: Claude Code 模式的保存回调
        project_dir: 项目目录

    Returns:
        BaseHumanInterface 实例
    """
    if mode == "claude_code":
        return ClaudeCodeInterface(
            save_callback=save_callback,
            project_dir=project_dir,
        )
    elif mode == "file_driven":
        return FileDrivenInterface(
            answers=answers_dict,
            answers_file=answers_file,
        )
    else:
        return HumanInTheLoop()
