"""蓝图模型 —— 阶段 3 产物。

定义 Blueprint + BlueprintUnit + UnitDAG。
蓝图是所有下游活动的唯一真理源。
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class UnitConstraints(BaseModel):
    """单元级非功能约束。"""

    performance: str = ""  # 如 "响应时间 < 100ms"
    security: str = ""  # 如 "需要 JWT 认证"
    resource_limits: str = ""  # 如 "内存 < 256MB"

    @field_validator("performance", "security", "resource_limits", mode="before")
    @classmethod
    def _coerce_to_str(cls, v: Any) -> str:
        """将 None 或非字符串值转为空字符串。"""
        if v is None:
            return ""
        if isinstance(v, str):
            return v
        return str(v)


class BlueprintUnit(BaseModel):
    """蓝图小单元 —— DAG 中的一个节点。"""

    id: str
    name: str
    description: str = ""
    input_spec: str = ""  # 输入定义（接口契约）
    output_spec: str = ""  # 输出定义（接口契约）
    implementation_approach: str = ""  # 核心算法/技术选型
    constraints: UnitConstraints = Field(default_factory=UnitConstraints)
    dependencies: list[str] = Field(default_factory=list)  # 依赖的单元 ID 列表
    priority: int = 0  # 开发优先级
    phase_id: str = ""  # 所属环节

    @field_validator("constraints", mode="before")
    @classmethod
    def _normalize_constraints(cls, v: Any) -> Any:
        """若 constraints 为 None 或 dict 则转为空 dict，由 UnitConstraints 处理默认值。"""
        if v is None:
            return {}
        return v

    def to_dict(self) -> dict[str, Any]:
        """转为字典（用于 JSON 序列化）。"""
        return self.model_dump()


class UnitDAG(BaseModel):
    """单元 DAG —— 描述单元之间的依赖关系。"""

    units: list[BlueprintUnit] = Field(default_factory=list)
    edges: list[tuple[str, str]] = Field(default_factory=list)  # (from_id, to_id)

    def get_ready_units(self, completed: set[str]) -> list[str]:
        """获取所有依赖已满足的可开发单元。

        Args:
            completed: 已完成的单元 ID 集合

        Returns:
            可以开始开发的单元 ID 列表
        """
        ready = []
        for unit in self.units:
            if unit.id in completed:
                continue
            if all(dep in completed for dep in unit.dependencies):
                ready.append(unit.id)
        return ready

    def topological_order(self) -> list[str]:
        """返回拓扑排序后的单元 ID 列表。

        Returns:
            按依赖顺序排列的单元 ID 列表
        """
        import networkx as nx

        G = nx.DiGraph()
        for unit in self.units:
            G.add_node(unit.id)
        for from_id, to_id in self.edges:
            G.add_edge(from_id, to_id)

        try:
            return list(nx.topological_sort(G))
        except nx.NetworkXUnfeasible:
            # 存在环 → 回退到优先级排序
            return sorted(
                [u.id for u in self.units],
                key=lambda uid: next(
                    (u.priority for u in self.units if u.id == uid), 0
                ),
            )

    def validate_dag(self) -> list[str]:
        """验证 DAG 的完整性。

        Returns:
            错误信息列表（空列表表示无错误）
        """
        errors = []

        unit_ids = {u.id for u in self.units}

        # 检查依赖引用
        for unit in self.units:
            for dep in unit.dependencies:
                if dep not in unit_ids:
                    errors.append(f"单元 '{unit.id}' 依赖不存在的单元 '{dep}'")

        # 检查循环依赖
        import networkx as nx
        G = nx.DiGraph()
        for unit in self.units:
            G.add_node(unit.id)
        for from_id, to_id in self.edges:
            G.add_edge(from_id, to_id)

        try:
            cycles = list(nx.simple_cycles(G))
            for cycle in cycles:
                errors.append(f"循环依赖: {' → '.join(cycle)}")
        except Exception:
            pass

        return errors


class Blueprint(BaseModel):
    """蓝图 —— 阶段 3 的最终产物。

    作为所有下游活动的唯一真理源，任何偏差须通过正式变更控制。
    """

    title: str
    version: int = 1
    description: str = ""
    units: list[BlueprintUnit] = Field(default_factory=list)
    dag: UnitDAG = Field(default_factory=UnitDAG)
    blueprint_approved: bool = False  # 人工批准后设为 True

    @classmethod
    def from_units(cls, title: str, units: list[BlueprintUnit]) -> "Blueprint":
        """从单元列表创建蓝图（自动推导 DAG 边）。"""
        edges = []
        for u in units:
            for dep in u.dependencies:
                edges.append((dep, u.id))
        dag = UnitDAG(units=units, edges=edges)
        return cls(title=title, units=units, dag=dag)

    def to_summary(self) -> str:
        """生成蓝图摘要。"""
        lines = [
            f"# 蓝图 v{self.version}: {self.title}",
            f"{self.description}",
            f"",
            f"## 单元列表 ({len(self.units)} 个)",
        ]
        for u in sorted(self.units, key=lambda x: x.priority):
            lines.append(f"- [{u.priority}] {u.id}: {u.name}")
            lines.append(f"  依赖: {u.dependencies or '无'}")
            lines.append(f"  输入: {u.input_spec}")
            lines.append(f"  输出: {u.output_spec}")
            lines.append(f"  实现: {u.implementation_approach}")
            if u.constraints.performance:
                lines.append(f"  性能: {u.constraints.performance}")
            if u.constraints.security:
                lines.append(f"  安全: {u.constraints.security}")

        order = self.dag.topological_order()
        lines.append(f"")
        lines.append(f"## 拓扑排序")
        lines.append(" → ".join(order))

        errors = self.dag.validate_dag()
        if errors:
            lines.append(f"")
            lines.append(f"## ⚠️ DAG 校验问题")
            for e in errors:
                lines.append(f"- {e}")

        return "\n".join(lines)
