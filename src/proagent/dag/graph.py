"""DAG 封装 —— 基于 networkx。

提供拓扑排序、就绪单元检测和环检测功能。
"""

from __future__ import annotations

import networkx as nx


class UnitGraph:
    """有向无环图，管理单元之间的依赖关系。"""

    def __init__(self):
        self._graph = nx.DiGraph()

    def add_unit(self, unit_id: str, dependencies: list[str] | None = None) -> None:
        """添加一个单元节点及其依赖边。"""
        self._graph.add_node(unit_id)
        for dep in (dependencies or []):
            self._graph.add_edge(dep, unit_id)

    def remove_unit(self, unit_id: str) -> None:
        """移除一个单元。"""
        self._graph.remove_node(unit_id)

    def topological_sort(self) -> list[str]:
        """拓扑排序。

        Returns:
            按依赖顺序排列的单元 ID 列表
        """
        try:
            return list(nx.topological_sort(self._graph))
        except nx.NetworkXUnfeasible:
            return []

    def next_available(
        self,
        completed: set[str],
        claimed: set[str] | None = None,
    ) -> list[str]:
        """获取可以开始开发的单元（依赖已满足且未认领）。

        Args:
            completed: 已完成的单元 ID 集合
            claimed: 已被认领的单元 ID 集合

        Returns:
            可开发单元列表
        """
        claimed = claimed or set()
        ready = []
        for node in self._graph.nodes:
            if node in completed or node in claimed:
                continue
            predecessors = set(self._graph.predecessors(node))
            if predecessors.issubset(completed):
                ready.append(node)
        return ready

    def all_complete(self, completed: set[str]) -> bool:
        """所有单元是否都已完成。"""
        return all(node in completed for node in self._graph.nodes)

    def validate(self) -> list[str]:
        """验证 DAG 的完整性。

        Returns:
            错误信息列表
        """
        errors = []

        if not self._graph.nodes:
            return errors

        # 环检测
        try:
            cycles = list(nx.simple_cycles(self._graph))
            for cycle in cycles:
                errors.append(f"存在循环依赖: {' → '.join(cycle)}")
        except Exception:
            pass

        return errors

    @property
    def nodes(self) -> list[str]:
        return list(self._graph.nodes)

    @property
    def edges(self) -> list[tuple[str, str]]:
        return list(self._graph.edges)

    def to_dict(self) -> dict:
        return {
            "nodes": self.nodes,
            "edges": [(u, v) for u, v in self.edges],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UnitGraph":
        graph = cls()
        for node in data.get("nodes", []):
            deps = [
                v for u, v in data.get("edges", []) if u == node
            ]
            graph.add_unit(node, deps if deps else None)
        return graph
