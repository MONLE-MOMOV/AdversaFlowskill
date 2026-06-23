"""项目计划模型 —— 阶段 2 产物。

定义 ProjectPlan 及其子结构：TechStack, Task, ProjectPhase, Risk。
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TechStack(BaseModel):
    """技术栈定义。"""

    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    infrastructure: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)


class Task(BaseModel):
    """项目任务定义。"""

    id: str
    title: str
    phase_id: str  # 所属环节
    priority: str = "medium"  # high | medium | low
    dependencies: list[str] = Field(default_factory=list)  # 依赖的任务 ID 列表
    estimated_effort: str = ""  # 预估工作量，如 "3人天"
    assigned_role: str = ""  # 分配的 AI 员工角色


class Risk(BaseModel):
    """项目风险。"""

    id: str
    description: str
    severity: str = "medium"  # high | medium | low
    probability: str = "medium"
    mitigation: str = ""
    contingency: str = ""


class RoleAssignment(BaseModel):
    """AI 员工角色分配。"""

    role_name: str  # 如 "前端员工"、"后端员工"、"测试员工"
    tasks: list[str] = Field(default_factory=list)  # 负责任务 ID 列表
    description: str = ""


class ProjectPhase(BaseModel):
    """项目环节定义。"""

    id: str
    name: str
    description: str = ""
    tasks: list[str] = Field(default_factory=list)  # 所含任务 ID 列表
    order: int = 0


class ProjectPlan(BaseModel):
    """项目计划 —— 阶段 2 的最终产物。"""

    title: str
    implementation_approach: str = ""  # 总体实现方式
    tech_stack: TechStack = Field(default_factory=TechStack)
    phases: list[ProjectPhase] = Field(default_factory=list)
    tasks: list[Task] = Field(default_factory=list)
    role_assignments: list[RoleAssignment] = Field(default_factory=list)
    risk_register: list[Risk] = Field(default_factory=list)
    plan_frozen: bool = False  # 人工确认后设为 True

    def to_summary(self) -> str:
        """生成计划摘要。"""
        lines = [
            f"# 项目计划: {self.title}",
            f"",
            f"## 总体实现方式",
            f"{self.implementation_approach}",
            f"",
            f"## 技术栈",
            f"- 语言: {', '.join(self.tech_stack.languages) or '未指定'}",
            f"- 框架: {', '.join(self.tech_stack.frameworks) or '未指定'}",
            f"- 数据库: {', '.join(self.tech_stack.databases) or '未指定'}",
            f"- 基础设施: {', '.join(self.tech_stack.infrastructure) or '未指定'}",
            f"- 工具: {', '.join(self.tech_stack.tools) or '未指定'}",
            f"",
            f"## 项目环节 ({len(self.phases)} 个)",
        ]
        for p in sorted(self.phases, key=lambda x: x.order):
            lines.append(f"- {p.id}: {p.name}")
            if p.description:
                lines.append(f"  {p.description}")
        lines.append(f"")
        lines.append(f"## 任务 ({len(self.tasks)} 个)")
        for t in self.tasks:
            lines.append(f"- [{t.priority.upper()}] {t.id}: {t.title}")
            lines.append(f"  环节: {t.phase_id} | 预估: {t.estimated_effort}")
            if t.dependencies:
                lines.append(f"  依赖: {', '.join(t.dependencies)}")
        lines.append(f"")
        lines.append(f"## AI 员工配置 ({len(self.role_assignments)} 个)")
        for ra in self.role_assignments:
            lines.append(f"- {ra.role_name}: {ra.description}")
            lines.append(f"  负责: {', '.join(ra.tasks)}")
        lines.append(f"")
        lines.append(f"## 风险登记册 ({len(self.risk_register)} 项)")
        for r in self.risk_register:
            lines.append(f"- [{r.severity.upper()}] {r.id}: {r.description}")
            if r.mitigation:
                lines.append(f"  缓解: {r.mitigation}")
        return "\n".join(lines)
