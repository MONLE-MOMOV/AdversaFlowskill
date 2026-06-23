"""CLI 入口 —— 基于 Click。

提供 start / resume / status / jump 四个子命令。
支持 --mode claude_code 以适配 Claude Code 交互。
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click

from proagent.config.settings import default_settings
from proagent.human.interface import (
    PROTOCOL_MARKER,
    PROTOCOL_END,
    BaseHumanInterface,
    ClaudeCodeInterface,
    FileDrivenInterface,
    HumanInTheLoop,
    create_interface,
)
from proagent.llm.client import LLMClient
from proagent.models.state import IN_PROGRESS, BLOCKED
from proagent.persistence.store import StateStore
from proagent.pipeline.conductor import PhaseConductor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger("proagent")


def _resolve_answers(project_path: Path, answers_file: str | None) -> dict[str, str] | None:
    """解析答案：优先从 --answers 参数，其次从项目目录下的 answers.json。"""
    if answers_file:
        path = Path(answers_file)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))

    # 自动检测项目目录下的 answers.json
    auto_path = project_path / "answers.json"
    if auto_path.exists():
        click.echo(f"📄 检测到答案文件: {auto_path}")
        return json.loads(auto_path.read_text(encoding="utf-8"))

    return None


@click.group()
@click.version_option(version="0.1.0", prog_name="proagent")
def cli():
    """ProAgent — 多角色对抗式 AI 开发流程系统。

    通过 AI 角色之间的结构化对抗辩论，将模糊需求转化为高质量软件交付。
    """


@cli.command()
@click.option("--project", "-p", required=True, type=str, help="项目目录路径")
@click.option("--requirement", "-r", required=True, help="初始模糊需求描述")
def start(project: str, requirement: str):
    """启动一个新的对抗式开发流程。"""
    project_path = Path(project)
    store, state = StateStore.create_project(project_path, requirement)

    click.echo(f"✅ 项目已创建: {state.project_id}")
    click.echo(f"📁 项目目录: {project}")
    click.echo(f"📋 当前阶段: 阶段 {state.current_phase} - 需求精炼")
    click.echo(f"📝 原始需求: {requirement[:100]}{'...' if len(requirement) > 100 else ''}")
    click.echo()
    click.echo("运行以下命令推进流水线:")
    click.echo(f"  /adversarial-dev-flow resume --project {project}")


@cli.command()
@click.option("--project", "-p", required=True, type=str, help="项目目录路径")
@click.option(
    "--mode", "-m",
    type=click.Choice(["interactive", "claude_code", "file_driven"]),
    default="claude_code",
    help="交互模式: interactive(终端) / claude_code(适配Claude Code) / file_driven(文件驱动)",
)
@click.option(
    "--answers", "-a",
    type=str, default=None,
    help="答案 JSON 文件路径（用于文件驱动模式或 Claude Code 回复）",
)
@click.option(
    "--max-phases", type=int, default=7,
    help="最大执行的阶段数（默认全部 7 个）",
)
def resume(project: str, mode: str, answers: str | None, max_phases: int):
    """从中断处恢复流水线执行。

    根据 mode 参数选择交互方式:
    - claude_code (默认): 遇到人工裁决时打印协议标记并退出
    - interactive: 在终端中阻塞等待人工输入
    - file_driven: 从 JSON 文件读取预置答案
    """
    project_path = Path(project)
    store = StateStore(project_path)
    state = store.load()

    if state is None:
        click.echo(f"❌ 项目状态文件不存在: {project_path / 'state.json'}")
        click.echo("请先运行 'proagent start' 创建项目。")
        sys.exit(1)

    # 检查是否有待处理的人工裁决 + 已提供答案
    resolved_answers = _resolve_answers(project_path, answers)
    pending_phase = state.get_current_phase()

    if pending_phase.unresolved_items and resolved_answers:
        click.echo("📥 人工裁决答案已注入，继续执行...")
        _apply_answers(state, resolved_answers, pending_phase)

    # 检查是否有因确认而阻塞的阶段 + 已提供确认答案
    if pending_phase.status == BLOCKED and not pending_phase.unresolved_items:
        if _check_confirm_answer(resolved_answers, pending_phase):
            click.echo("📥 人工确认已注入，继续执行...")
            pending_phase.status = "completed"
            state.current_phase += 1
            store.save(state)
            # 刷新 pending_phase 引用
            pending_phase = state.get_current_phase()

    # 创建交互接口
    if mode == "file_driven" and resolved_answers:
        human = create_interface("file_driven", answers_dict=resolved_answers)
    elif mode == "claude_code":
        human = create_interface(
            "claude_code",
            save_callback=lambda: store.save(state),
            project_dir=project_path,
        )
    elif mode == "interactive":
        human = create_interface("interactive")
    else:
        human = create_interface("claude_code", save_callback=lambda: store.save(state))

    # 创建 LLM 客户端和编排器
    llm = LLMClient(default_settings)
    conductor = PhaseConductor(store, llm, human, default_settings)

    click.echo(f"📂 项目: {state.project_id}")
    click.echo(f"📍 当前阶段: 阶段 {state.current_phase}")
    click.echo(f"🔧 交互模式: {mode}")

    # 执行阶段
    phases_run = 0
    while state.current_phase <= min(7, max_phases):
        phase_state = state.get_current_phase()

        if phase_state.status == "completed":
            state.current_phase += 1
            store.save(state)
            continue

        if phase_state.status == BLOCKED:
            click.echo(f"🚫 阶段 {state.current_phase} 处于阻塞状态")
            if phase_state.unresolved_items:
                click.echo("   有待处理的人工裁决项。请提供裁决后使用 --answers 恢复。")
            break

        click.echo(f"\n{'='*50}")
        click.echo(f"  执行阶段 {state.current_phase}: {_phase_name(state.current_phase)}")
        click.echo(f"{'='*50}")

        state = conductor.advance(state)
        store.save(state)
        phases_run += 1

        # 检查是否因为需要人工输入而暂停
        if state.get_current_phase().unresolved_items:
            click.echo(f"\n⏸️  阶段 {state.current_phase} 需要人工裁决。")
            click.echo(f"   争议项数: {len(state.get_current_phase().unresolved_items)}")
            click.echo(f"   请审核后提供裁决，然后重新运行:")
            click.echo(f"   /adversarial-dev-flow resume --project {project} --answers answers.json")
            break

        # 检查是否需要人工确认
        if state.get_current_phase().status == BLOCKED:
            click.echo(f"\n⏸️  阶段 {state.current_phase} 等待人工确认。")
            break

    if phases_run == 0:
        click.echo("\n📋 没有可执行的阶段。使用 'status' 查看详情。")


@cli.command()
@click.option("--project", "-p", required=True, type=str, help="项目目录路径")
def status(project: str):
    """查看项目当前状态。"""
    project_path = Path(project)
    store = StateStore(project_path)
    state = store.load()

    if state is None:
        click.echo(f"❌ 项目状态文件不存在: {project_path / 'state.json'}")
        sys.exit(1)

    click.echo("=" * 60)
    click.echo(f"  项目 ID:    {state.project_id}")
    click.echo(f"  创建时间:   {state.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    click.echo(f"  更新时间:   {state.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    click.echo(f"  当前阶段:   阶段 {state.current_phase}")
    click.echo(f"  原始需求:   {state.original_requirement[:80]}...")
    click.echo("=" * 60)

    for i in range(1, 8):
        phase = state.phases[str(i)]
        status_icon = {
            "pending": "⏳", "in_progress": "🔄",
            "completed": "✅", "blocked": "🚫",
        }.get(phase.status, "❓")

        artifact_keys = list(phase.artifacts.keys())
        click.echo(
            f"  {status_icon} 阶段 {i}: {phase.status:12s} "
            f"| 辩论: {phase.current_round} 轮 "
            f"| 未解决: {len(phase.unresolved_items)} 项"
            f"{' | 产物: ' + ', '.join(artifact_keys) if artifact_keys else ''}"
        )

        if phase.unresolved_items:
            for item in phase.unresolved_items:
                click.echo(f"       ↳ 待裁决: {item.challenge.get('item', 'N/A')} — {item.reason}")

    # 检查是否有待处理的人工操作
    click.echo()
    pending = state.get_current_phase()
    if pending.unresolved_items:
        click.echo(f"⚠️  阶段 {state.current_phase} 有待处理的人工裁决。")
        click.echo(f"   创建 answers.json 文件后运行 resume --answers answers.json")


@cli.command()
@click.option("--project", "-p", required=True, type=str, help="项目目录路径")
@click.option("--phase", type=int, required=True, help="目标阶段编号 (1-7)")
def jump(project: str, phase: int):
    """跳转到指定阶段（需确认）。"""
    if not 1 <= phase <= 7:
        click.echo("❌ 阶段编号必须在 1-7 之间")
        sys.exit(1)

    project_path = Path(project)
    store = StateStore(project_path)
    state = store.load()

    if state is None:
        click.echo(f"❌ 项目不存在: {project}")
        sys.exit(1)

    old_phase = state.current_phase
    state.current_phase = phase
    state.phases[str(phase)].status = IN_PROGRESS
    store.save(state)

    click.echo(f"✅ 已从阶段 {old_phase} 跳转到阶段 {phase}")


# ------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------

def _phase_name(num: int) -> str:
    """获取阶段名称。"""
    names = {
        1: "需求精炼",
        2: "项目规划",
        3: "蓝图设计",
        4: "单元开发",
        5: "环节闭环",
        6: "变更控制",
        7: "里程碑会议",
    }
    return names.get(num, f"阶段{num}")


def _apply_answers(state, answers: dict[str, str], phase_state) -> None:
    """将人工答案应用到未解决的争议项上。"""
    from proagent.models.state import HumanDecision

    decisions = []
    for i, item in enumerate(phase_state.unresolved_items):
        ref = str(item.challenge.get("item", f"item_{i}"))
        choice = answers.get(ref, answers.get(f"adjudicate_{i}", "a"))

        if choice == "a":
            decisions.append(HumanDecision(
                item_reference=ref, decision="approved",
                notes="采纳挑战方意见"))
        elif choice == "r":
            decisions.append(HumanDecision(
                item_reference=ref, decision="rejected",
                notes="接受提案方方案"))
        else:
            decisions.append(HumanDecision(
                item_reference=ref, decision="overridden", notes=choice))

    phase_state.human_decisions = decisions
    phase_state.unresolved_items = []  # 清除未解决项
    phase_state.status = IN_PROGRESS


def _check_confirm_answer(
    answers: dict[str, str] | None, phase_state
) -> bool:
    """检查是否提供了确认答案（用于解除 confirm 导致的阻塞）。

    在 answers 中查找 "confirm" 键，值为 "yes"/"y"/"true"/"1" 时返回 True。
    也支持 "confirm_phase_N" 格式的键。
    """
    if not answers:
        return False

    # 通用确认键
    confirm_val = answers.get("confirm", "").lower()
    if confirm_val in ("yes", "y", "true", "1"):
        return True

    # 阶段特定确认键
    phase_key = f"confirm_phase_{phase_state.phase_number}"
    phase_val = answers.get(phase_key, "").lower()
    if phase_val in ("yes", "y", "true", "1"):
        return True

    return False


if __name__ == "__main__":
    cli()
