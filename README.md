# ProAgent — 多角色对抗式 AI 开发流程
# ProAgent — Multi-Role Adversarial AI Development Flow

> 通过 7 个阶段的 AI 角色结构化对抗辩论，将模糊需求转化为高质量软件交付。
> Transform vague requirements into high-quality software delivery through 7 phases of structured adversarial debate between AI roles.

---

## 简介 | About

**ProAgent** 是多角色对抗式 AI 开发流程系统：7 阶段、8 角色、最多 3 轮辩论，僵局人工裁决，Claude API 驱动。
*ProAgent — multi-role adversarial AI dev workflow: 7 phases, 8 roles, ≤3 debate rounds, human escalation on deadlock. Powered by Claude API.*

---

## 目录 | Table of Contents

1. [核心思想 | Core Concept](#核心思想--core-concept)
2. [快速开始 | Quick Start](#快速开始--quick-start)
3. [架构总览 | Architecture Overview](#架构总览--architecture-overview)
4. [阶段 1：需求精炼 | Phase 1: Requirement Refinement](#阶段-1需求精炼--phase-1-requirement-refinement)
5. [阶段 2：项目规划 | Phase 2: Project Planning](#阶段-2项目规划--phase-2-project-planning)
6. [阶段 3：蓝图设计 | Phase 3: Blueprint Design](#阶段-3蓝图设计--phase-3-blueprint-design)
7. [阶段 4：单元开发与闭环审查 | Phase 4: Unit Development & Closed-Loop Review](#阶段-4单元开发与闭环审查--phase-4-unit-development--closed-loop-review)
8. [阶段 5：环节与需求闭环 | Phase 5: Phase & Requirement Closure](#阶段-5环节与需求闭环--phase-5-phase--requirement-closure)
9. [阶段 6：蓝图变更控制 | Phase 6: Blueprint Change Control](#阶段-6蓝图变更控制--phase-6-blueprint-change-control)
10. [阶段 7：里程碑会议 | Phase 7: Milestone Meeting](#阶段-7里程碑会议--phase-7-milestone-meeting)
11. [交互模式 | Interaction Modes](#交互模式--interaction-modes)
12. [在 Claude Code 中使用 | Using in Claude Code](#在-claude-code-中使用--using-in-claude-code)
13. [项目结构 | Project Structure](#项目结构--project-structure)
14. [配置参考 | Configuration Reference](#配置参考--configuration-reference)

---

## 核心思想 | Core Concept

传统软件开发中，需求评审、方案评审、代码审查本质上都是"一个人提、另一个人审"的对抗模式。
Traditional software development — requirement reviews, design reviews, code reviews — all follow an adversarial pattern of "one proposes, another challenges."

ProAgent 把这个模式系统化为 7 个阶段的 AI 工作流——每个阶段都有**提案方（Proposer）**和**挑战方（Challenger）**两个 AI 角色。
ProAgent systematizes this pattern into a 7-phase AI workflow — each phase has a **Proposer** and a **Challenger** AI role.

双方进行最多 **3 轮**结构化辩论：提案方生成草案 → 挑战方逐条审查 → 提案方回应并修订 → 判定收敛或继续。
The two sides engage in up to **3 rounds** of structured debate: Proposer generates a draft → Challenger reviews item by item → Proposer responds and revises → Judge determines convergence or continuation.

3 轮后仍无法达成一致的争议，标记为**待人工裁决**，连同已达一致的内容一并提交。
Issues still unresolved after 3 rounds are flagged for **human adjudication**, submitted alongside the agreed-upon content.

```
模糊需求                    需求基线                  项目计划                  DAG蓝图
Vague Requirement  →  Requirement Baseline  →  Project Plan  →  DAG Blueprint
                              │                         │                      │
     [AI产品经理↔AI产品审核]   [AI项目经理↔AI项目审核]   [AI架构师↔AI架构审核]   [AI员工↔AI单元审查]
     [PM ↔ Reviewer]         [PM ↔ Plan Reviewer]     [Architect ↔ Arch Rev]  [Dev ↔ Unit Rev]

        ↓                         ↓                      ↓                      ↓
    逐单元交付                 闭环确认                  变更控制               里程碑报告
    Unit Delivery    →   Closure Confirmed   →   Change Control   →   Milestone Report
```

---

## 快速开始 | Quick Start

### 环境要求 | Requirements

- Python 3.10 或更高版本 | Python 3.10 or higher
- Anthropic API Key（通过环境变量 `ANTHROPIC_API_KEY` 设置）| Set via `ANTHROPIC_API_KEY` env var

### 安装 | Installation

```bash
# 安装依赖 | Install dependencies
pip install --break-system-packages anthropic pydantic click networkx pyyaml rich

# 设置 API Key | Set API key
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 三步启动 | Three-Step Start

```bash
# 1. 创建项目 | Create project
PYTHONPATH=/home/pan/projects/proagent/src python3 -m proagent.main start \
  --project ./my-project \
  --requirement "构建一个 Ubuntu 下的雷霆战机游戏"

# 2. 查看状态 | Check status
PYTHONPATH=/home/pan/projects/proagent/src python3 -m proagent.main status \
  --project ./my-project

# 3. 推进流水线 | Advance pipeline
PYTHONPATH=/home/pan/projects/proagent/src python3 -m proagent.main resume \
  --project ./my-project --mode claude_code
```

### CLI 命令参考 | CLI Command Reference

| 命令 | Command | 说明 | Description |
|------|---------|------|-------------|
| `start` | `start` | 创建新项目，初始化 7 阶段状态 | Create a new project, initialize 7-phase state |
| `status` | `status` | 查看所有阶段的进度和产物 | View all phase progress and artifacts |
| `resume` | `resume` | 从当前阶段继续推进流水线 | Continue advancing the pipeline from current phase |
| `jump` | `jump` | 跳转到指定阶段（需确认）| Jump to a specific phase (requires confirmation) |

---

## 架构总览 | Architecture Overview

### 对抗辩论引擎 | Adversarial Debate Engine

每个阶段的对抗辩论由统一的引擎驱动，是系统最核心的可复用组件。
Each phase's adversarial debate is driven by a unified engine — the system's most core reusable component.

```
                    ┌──────────────────────┐
                    │   当前上下文 (Context)  │
                    │   已有产物 + 需求基线   │
                    └──────────┬───────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
              │  Round 1: Proposer 生成草案     │
              │  AI 角色获得专属系统提示词       │
              │  输出：结构化 JSON 产物          │
              └────────────┬───────────────────┘
                           │
                           ▼
              ┌────────────────────────────────┐
              │  Round 1: Challenger 逐条审查   │
              │  AI 角色获得对立系统提示词       │
              │  输出：[{item, severity, ...}]   │
              └────────────┬───────────────────┘
                           │
                           ▼
              ┌────────────────────────────────┐
              │  Round 1: Proposer 回应质疑     │
              │  逐条 accept/reject/defer       │
              │  输出：修订后的产物 + 回应理由    │
              └────────────┬───────────────────┘
                           │
                           ▼
              ┌────────────────────────────────┐
              │  Judge 判定（规则引擎，非 LLM）  │
              │  · 全 accept → 收敛             │
              │  · 有 reject → 检查僵局         │
              │  · 僵局 + 达最大轮数 → 升级     │
              └────────────┬───────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
         收敛 Converged           未解决 Unresolved
              │                         │
              ▼                         ▼
    ┌──────────────────┐    ┌──────────────────────┐
    │  更新产物          │    │  人工裁决              │
    │  Update artifact  │    │  Human adjudication   │
    │  进入下一阶段      │    │  争议标记 + 等待确认    │
    │  Next phase       │    │  Flag + await confirm │
    └──────────────────┘    └──────────────────────┘
```

**判定逻辑 | Judgment Logic**：
- `accept`（提案方接受建议）→ 该项解决 | The item is resolved
- `reject`（提案方拒绝）→ 检查是否与上一轮相同，相同则为僵局 | Check if same as previous round → deadlock
- `defer`（提案方推迟）→ 若达最大轮数则升级，否则进入下一轮 | Escalate if max rounds reached, otherwise continue
- 3 轮后仍有未解决项 → 强制升级人工裁决 | Force escalate to human after 3 rounds

### 状态管理 | State Management

整个流程的状态保存在单个 JSON 文件中，随时可中断和恢复。
The entire pipeline state is stored in a single JSON file, interruptible and resumable at any time.

```json
{
  "schema_version": 1,
  "project_id": "proj_20260623_125803_4e2758",
  "current_phase": 2,
  "original_requirement": "构建一个 Ubuntu 下的雷霆战机游戏",
  "phases": {
    "1": {
      "status": "completed",
      "current_round": 2,
      "artifacts": {
        "requirement_doc": { "...": "..." },
        "baseline_confirmed": true
      },
      "debate_history": [ "..." ],
      "unresolved_items": []
    },
    "2": {
      "status": "in_progress",
      "current_round": 0,
      "artifacts": {},
      "unresolved_items": []
    }
  }
}
```

- 原子写入（`.tmp` → `os.replace()`），不会出现写一半的损坏文件 | Atomic write — no partial writes
- 每次修改前自动备份 | Auto-backup before each mutation
- Pydantic 模型保证数据结构一致性 | Pydantic models guarantee data structure consistency

---

## 阶段 1：需求精炼 | Phase 1: Requirement Refinement

**角色 | Roles**：
- 提案方 Proposer：**AI 产品经理** | AI Product Manager
- 挑战方 Challenger：**AI 产品审核** | AI Product Reviewer

**输入 Input**：一段模糊的自然语言需求描述 | A vague natural language requirement description

**流程 Flow**：

1. AI 产品经理将模糊需求转化为结构化需求草案。
   The AI Product Manager transforms the vague requirement into a structured requirement draft.
2. 草案包含：功能点（含优先级和业务价值）、用户场景（persona + 目标 + 步骤 + 预期结果）、验收标准（可独立测试的通过条件）、非功能约束（性能/安全/可扩展性/可用性/合规）。
   The draft includes: features (with priority and business value), user scenarios (persona + goal + steps + expected outcome), acceptance criteria (independently testable conditions), non-functional constraints (performance/security/scalability/availability/compliance).
3. AI 产品审核逐条审查：需求是否完备？是否存在歧义？是否与业务目标一致？是否可测试？功能间是否一致？
   The AI Product Reviewer checks item by item: Is the requirement complete? Is there ambiguity? Is it aligned with business goals? Is it testable? Is there consistency between features?
4. 产品经理逐条回应：accept（接受并修改）/ reject（拒绝并给出理由）/ defer（标记待定）。
   The Product Manager responds to each: accept (revise accordingly) / reject (with rationale) / defer (flag for later).
5. 判定器评估收敛状态。3 轮后仍有分歧的标记为待人工裁决。
   The Judge evaluates convergence. Items still in disagreement after 3 rounds are flagged for human adjudication.
6. 人工复核整体需求文档，确认后锁定需求基线。
   Human reviews the overall requirement document and confirms the requirement baseline.

**输出 Output**：`RequirementDoc` — 需求基线，成为后续所有阶段的输入 | The requirement baseline, serving as input for all subsequent phases

**审查标准 | Review Criteria**：
- 完备性 Completeness：是否覆盖了所有用户场景？边界情况和异常路径是否考虑？| Are all user scenarios covered? Edge cases and exception paths?
- 歧义性 Ambiguity：每个需求是否只有一种理解方式？是否存在模糊表述？| Can each requirement be understood in only one way?
- 业务对齐 Business Alignment：每个功能是否服务于明确的业务目标？| Does each feature serve a clear business goal?
- 可测试性 Testability：每个验收标准是否可以客观验证？| Can each acceptance criterion be objectively verified?
- 一致性 Consistency：功能之间是否存在冲突？描述是否前后一致？| Are there conflicts between features? Is the description consistent?

---

## 阶段 2：项目规划 | Phase 2: Project Planning

**角色 | Roles**：
- 提案方 Proposer：**AI 项目经理** | AI Project Manager
- 挑战方 Challenger：**AI 项目审核** | AI Project Reviewer

**输入 Input**：阶段 1 锁定的需求基线 | The locked requirement baseline from Phase 1

**流程 Flow**：

1. AI 项目经理输出：总体实现方式（架构思路 + 核心设计决策）、技术栈与约束、任务优先级列表、项目主要环节划分、每个环节所需 AI 员工角色配置。
   The AI Project Manager outputs: overall implementation approach (architecture + key design decisions), tech stack and constraints, prioritized task list, project phase breakdown, AI role assignments per phase.
2. AI 项目审核从可行性、资源冲突、依赖风险、环节完整性、风险评估等角度发起挑战。
   The AI Project Reviewer challenges from perspectives of feasibility, resource conflicts, dependency risks, phase completeness, and risk assessment.
3. 项目经理逐轮调整计划，回应挑战方的每项质疑。
   The Project Manager adjusts the plan round by round, responding to each challenge.
4. 3 轮后仍存分歧的点提交人工裁决，通过后冻结项目计划。
   Remaining disagreements after 3 rounds go to human adjudication; the plan is frozen upon approval.

**输出 Output**：`ProjectPlan` — 冻结的项目计划，作为阶段 3 的输入 | The frozen project plan, serving as input for Phase 3

**审查标准 | Review Criteria**：
- 可行性 Feasibility：技术选型是否合理？是否考虑了替代方案的风险？| Is the tech choice reasonable? Are alternative risks considered?
- 资源冲突 Resource Conflicts：是否存在资源竞争或瓶颈？AI 员工配置是否合理？| Are there resource competitions or bottlenecks? Are role assignments reasonable?
- 依赖风险 Dependency Risks：关键路径上的依赖是否可控？是否有单点故障？| Are critical-path dependencies controllable? Any single points of failure?
- 环节完整性 Phase Completeness：是否遗漏了必要的环节？各环节边界是否清晰？| Are necessary phases missing? Are phase boundaries clear?
- 风险评估 Risk Assessment：是否充分识别并缓解了主要风险？| Are major risks fully identified and mitigated?

---

## 阶段 3：蓝图设计 | Phase 3: Blueprint Design

**角色 | Roles**：
- 提案方 Proposer：**AI 架构师** | AI Architect
- 挑战方 Challenger：**AI 架构审核** | AI Architecture Reviewer

**输入 Input**：阶段 2 冻结的项目计划 | The frozen project plan from Phase 2

**流程 Flow**：

1. AI 架构师将实现方式与约束拆解为一系列紧密关联的小单元（模块/服务/组件），构造成**有向无环图（DAG）**。
   The AI Architect decomposes the implementation approach and constraints into a series of closely related small units (modules/services/components), forming a **Directed Acyclic Graph (DAG)**.
2. 每个小单元（BlueprintUnit）必须明确包含：
   Each small unit (BlueprintUnit) must explicitly include:
   - 输入/输出定义（接口契约、数据格式）| Input/output definitions (interface contracts, data formats)
   - 实现方式与核心算法/技术选型 | Implementation approach and core algorithms/tech choices
   - 约束（性能指标、安全要求、资源限制）| Constraints (performance metrics, security requirements, resource limits)
   - 与其他单元的依赖关系（上游/下游）| Dependencies on other units (upstream/downstream)
   - 开发优先级（由 DAG 拓扑位置决定）| Development priority (determined by DAG topological position)
3. AI 架构审核验证：是否完全覆盖需求？单元粒度是否合理？接口是否兼容？非功能约束是否满足？DAG 是否无环？
   The AI Architecture Reviewer verifies: full requirement coverage? Reasonable unit granularity? Interface compatibility? Non-functional constraints satisfied? DAG cycle-free?
4. 架构师根据审核意见修订蓝图，直至通过或上交分歧。
   The Architect revises the blueprint per review feedback until approved or disagreements escalated.

**输出 Output**：`Blueprint` + `UnitDAG` — **唯一真理源**。人工批准后入库，所有下游活动必须以蓝图为准，任何偏离须通过正式变更控制。
**The single source of truth.** Once human-approved, it becomes the reference for all downstream activities; any deviation must go through formal change control.

**审查标准 | Review Criteria**：
- 需求覆盖 Requirement Coverage：是否完全覆盖了需求基线的所有功能？每个需求是否有对应的单元？| Are all baseline requirements fully covered? Does each requirement have a corresponding unit?
- 粒度合理性 Granularity：单元拆分是否过大（难以审查）或过小（碎片化）？| Are units too large (hard to review) or too small (fragmented)?
- 接口兼容性 Interface Compatibility：上下游接口是否匹配？数据格式是否一致？| Do upstream/downstream interfaces match? Are data formats consistent?
- 非功能约束 Non-Functional：性能、安全、资源约束是否在每个单元中可验证？| Are performance, security, resource constraints verifiable at the unit level?
- DAG 正确性 DAG Correctness：依赖关系是否合理？是否存在循环依赖？接口方向是否正确？| Are dependencies reasonable? Any circular dependencies? Correct interface directions?

### DAG 示例 | DAG Example

```
  ┌───────┐
  │  u1   │  API 网关 | API Gateway
  │ pri=1 │
  └──┬───┬┘
     │   │
  ┌──▼─┐ ┌▼─────┐
  │ u2 │ │  u3  │  WebSocket 服务 + 数据库层 | WebSocket Service + DB Layer
  │pri=2│ │pri=2 │
  └──┬─┘ └──┬──┘
     │      │
  ┌──▼──────▼─┐
  │    u4     │  协作编辑器组件 | Collaborative Editor Component
  │   pri=3   │
  └───────────┘

拓扑排序 | Topological Order: u1 → u2 → u3 → u4
就绪检测 | Ready Detection: u2 和 u3 在 u1 完成后可并行开发 | u2 and u3 can be developed in parallel after u1
```

---

## 阶段 4：单元开发与闭环审查 | Phase 4: Unit Development & Closed-Loop Review

**角色 | Roles**：
- 实现方 Implementer：**AI 员工** | AI Employee (Developer)
- 检查方 Checker：**AI 单元审查** | AI Unit Reviewer
- 审核方 Gatekeeper：**AI 架构师**（审核修改建议）| AI Architect (reviews modification suggestions)

**输入 Input**：阶段 3 的 DAG 蓝图 | The DAG blueprint from Phase 3

**流程 Flow**：

1. **认领单元 Claim Unit**：按蓝图拓扑排序和优先级，AI 员工认领下一个依赖已全部满足的单元。
   Following the blueprint topological order and priority, the AI Employee claims the next unit whose dependencies are all satisfied.

2. **开发实现 Develop**：严格按照蓝图的输入/输出定义和约束进行开发实现，完成后进行自测。
   Strictly implement according to the blueprint's input/output definitions and constraints; self-test upon completion.

3. **提交审查 Submit for Review**：提交代码及执行小结，说明：实现了什么、如何满足约束、遇到的问题及解决方式。
   Submit code and execution summary explaining: what was implemented, how constraints were met, problems encountered and their solutions.

4. **单元审查 Unit Review**：AI 单元审查严格对照蓝图定义进行审查，输出"通过"或含具体修改建议的反馈。
   The AI Unit Reviewer strictly reviews against the blueprint definition, outputting "pass" or feedback with specific modification suggestions.

5. **架构师审核 Architect Gate**：若需修改，修改建议先经 AI 架构师审核，确保修改不偏离蓝图整体设计。架构师审核后将指令传递给 AI 员工重做。
   If modifications are needed, suggestions first go through the AI Architect to ensure changes don't deviate from the blueprint's overall design. The Architect then passes instructions to the Developer for rework.

6. **重做循环 Rework Loop**：员工重做 → 重新自测 → 重新提交 → 审查方再次审查。同一单元最多重做 **3 次**，超过则升级为人工裁决。
   Developer reworks → re-self-tests → re-submits → Reviewer re-reviews. Maximum **3 redo cycles** per unit; beyond that, escalate to human adjudication.

7. **记录总结 Record Summary**：单元通过后，架构师记录状态，形成该单元的结构化总结（员工做了什么、架构师审核了什么、最终结果），通知项目经理。
   After the unit passes, the Architect records the status, creates a structured summary (what the developer did, what the architect reviewed, the final result), and notifies the Project Manager.

```
                 ┌─────────────────────┐
                 │  认领下一个就绪单元    │
                 │  Claim next ready    │
                 │  unit from DAG       │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │  AI 员工：开发 + 自测 │
                 │  Developer:          │
                 │  implement + test    │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │  AI 单元审查：对照蓝图 │
                 │  Unit Reviewer:      │
                 │  check vs blueprint  │
                 └──────┬──────┬───────┘
                        │      │
                   通过 Pass  需修改 Revise
                        │      │
                        │      ▼
                        │  ┌─────────────────────┐
                        │  │  AI 架构师审核修改建议  │
                        │  │  Architect reviews    │
                        │  │  modification request │
                        │  └──────────┬──────────┘
                        │             │
                        │      ┌──────┴──────┐
                        │      │             │
                        │   ≤3 次重做    >3 次重做
                        │   ≤3 redos     >3 redos
                        │      │             │
                        │      ▼             ▼
                        │  返回开发重做   升级人工裁决
                        │  Back to dev   Escalate to
                        │                 human
                        │
                        ▼
                 ┌─────────────────────┐
                 │  架构师记录总结       │
                 │  Architect records   │
                 │  unit summary        │
                 └─────────────────────┘
```

**审查标准 | Review Criteria**：
- 蓝图符合性 Blueprint Compliance：代码是否严格按照蓝图的输入/输出定义实现？| Is the code strictly implemented per blueprint I/O definitions?
- 约束满足 Constraint Satisfaction：是否满足蓝图中定义的所有非功能约束？| Are all non-functional constraints from the blueprint met?
- 代码质量 Code Quality：代码是否清晰、正确、可维护？| Is the code clear, correct, and maintainable?
- 测试覆盖 Test Coverage：自测是否充分覆盖了主要功能和边界情况？| Does self-testing adequately cover main functions and edge cases?
- 接口兼容 Interface Compatibility：输入/输出是否与上下游单元的接口定义一致？| Are I/Os consistent with upstream/downstream unit interface definitions?

---

## 阶段 5：环节与需求闭环 | Phase 5: Phase & Requirement Closure

**角色 | Roles**：
- 提案方 Proposer：**AI 项目经理**（完整性审核 | Completeness Auditor）
- 挑战方 Challenger：**AI 产品经理**（需求复核方 | Requirement Re-validator）

**输入 Input**：阶段 4 中逐渐完成的单元 + 阶段 1 的需求基线 | Incrementally completed units from Phase 4 + the requirement baseline from Phase 1

**流程 Flow**：

1. 随着单元逐步完成、集成至对应环节，AI 项目经理审核该环节内所有单元是否均已达标、环节整体是否完整。
   As units are gradually completed and integrated into their corresponding phases, the AI Project Manager audits whether all units in the phase meet standards and the phase as a whole is complete.
2. AI 产品经理从需求视角复核：该环节是否真正满足了基线需求？是否存在遗漏或偏差？
   The AI Product Manager re-validates from the requirement perspective: Does this phase truly satisfy the baseline requirements? Are there gaps or deviations?
3. 双方独立评估后若判断不一致，进行最多 3 轮对抗讨论，聚焦环节是否闭环。
   If the two sides reach different conclusions after independent evaluation, up to 3 rounds of adversarial discussion focus on whether the phase is truly closed.
4. 最终结果形成报告，并征询人类：是否有追加需求或调整？若无追加，推进下一环节；若有变更，触发蓝图变更控制（阶段 6）。
   The final result is compiled into a report, and the human is consulted: any additional requirements or adjustments? If none, advance to the next phase; if changes are needed, trigger blueprint change control (Phase 6).

**输出 Output**：闭环报告 + 追加需求标志 | Closure report + additional requirement flag

---

## 阶段 6：蓝图变更控制 | Phase 6: Blueprint Change Control

**角色 | Roles**：
- 提案方 Proposer：**AI 架构师**（变更评估方 | Change Evaluator）
- 挑战方 Challenger：**AI 架构审核**（变更阻力方 | Change Resistor）

**输入 Input**：阶段 5 产生的变更需求 | Change requirements from Phase 5

**流程 Flow**：

1. 当出现可能大范围影响蓝图的变更请求时，首先由架构师与架构审核进行 3 轮对抗，判断是否必须启动正式变更。
   When a change request that may broadly impact the blueprint arises, the Architect and Architecture Reviewer first engage in 3 rounds of debate to determine whether formal change must be initiated.
2. **若双方一致同意启动**，或 **3 轮后仍僵持不下**，则强制启动**变更委员会**。
   **If both sides agree to proceed**, or **if deadlocked after 3 rounds**, a **Change Committee** is forcibly convened.
3. 变更委员会由**全角色 AI**（从 AI 员工到产品经理）及**人类**共同组成，联合评审变更影响、可行性，并生成新蓝图版本。
   The Change Committee consists of **all AI roles** (from AI Employee to Product Manager) and **humans**, jointly reviewing change impact and feasibility, and generating a new blueprint version.
4. 新蓝图经人工批准后入库，重新发布受影响的小单元任务。旧版本蓝图保留作为历史参考。
   The new blueprint is checked in after human approval, and affected unit tasks are re-issued. The old blueprint version is retained for historical reference.

**审查标准 | Review Criteria**：
- 变更必要性 Change Necessity：变更是必须的还是可选的？能否通过现有蓝图达成？| Is the change necessary or optional? Can it be achieved through the existing blueprint?
- 影响范围 Impact Scope：将影响哪些单元？影响是否可以局部化？| Which units will be affected? Can the impact be localized?
- 可行性 Feasibility：新蓝图版本在技术和资源上是否可行？| Is the new blueprint version technically and resource-wise feasible?
- 回归风险 Regression Risk：变更是否引入新的风险？| Does the change introduce new risks?
- 一致性 Consistency：变更后的蓝图是否仍满足原始需求基线？| Does the post-change blueprint still satisfy the original requirement baseline?

---

## 阶段 7：里程碑会议 | Phase 7: Milestone Meeting

**触发时机 | Triggers**：
- 每个小单元完成时 | When each small unit is completed
- 每个环节完成时 | When each phase is completed
- 项目终了时 | At project end

**参与者 | Participants**：全体 AI 角色（产品经理、项目经理、架构师、员工代表等）及人类 | All AI roles (Product Manager, Project Manager, Architect, Employee representatives, etc.) and humans

**流程 Flow**：

1. AI 项目经理与 AI 产品经理共同生成结构化报告。
   The AI Project Manager and AI Product Manager jointly generate a structured report.
2. 报告经其他 AI 角色交叉审查，双方互审。
   The report is cross-reviewed by other AI roles, with mutual review between the two.
3. 报告中如有分歧，会议期间即时对抗最多 3 轮，仍不一致的交由人类最终裁决。
   If there are disagreements in the report, up to 3 rounds of instant debate occur during the meeting; remaining disagreements go to human final adjudication.

**输出 Output**：结构化里程碑报告，包含以下四个维度 | Structured milestone report with four dimensions：

| 维度 | Dimension | 内容 | Content |
|------|-----------|------|---------|
| 完成度总结 | Completion Summary | 已完成单元/环节 vs 计划 | Completed units/phases vs. plan |
| 偏离分析 | Deviation Analysis | 与蓝图、需求基线的差异 | Differences from blueprint and requirement baseline |
| 风险提示 | Risk Alerts | 技术、进度、资源三类风险 | Technology, schedule, and resource risks |
| 推进建议 | Go/No-Go Recommendation | 是否继续推进的建议 | Recommendation on whether to proceed |

---

## 交互模式 | Interaction Modes

ProAgent 支持三种人机交互模式，适应不同使用场景。
ProAgent supports three human-computer interaction modes for different usage scenarios.

### 1. Claude Code 模式（默认）| Claude Code Mode (Default)

```
--mode claude_code
```

在 Claude Code 对话中使用。遇到人工裁决时，CLI 打印协议标记后退出，不阻塞 stdin。
Use within Claude Code conversations. When human adjudication is needed, the CLI prints a protocol marker and exits without blocking stdin.

```
__PROAGENT_NEEDS_HUMAN__
{
  "action_type": "confirm",
  "summary": "阶段 1 完成。状态: converged\n总轮数: 2\n是否确认并继续下一阶段?"
}
__PROAGENT_END_ACTION__
```

Claude Code 读取标记后向用户展示问题，用户答复后创建 `answers.json`，重新调用 CLI 继续。
Claude Code reads the marker, presents the question to the user, creates `answers.json` after the user responds, and re-invokes the CLI to continue.

### 2. 终端交互模式 | Interactive Terminal Mode

```
--mode interactive
```

在独立终端中使用。`input()` 阻塞等待用户输入，适合直接命令行操作。
Use in a standalone terminal. `input()` blocks waiting for user input — suitable for direct command-line operation.

### 3. 文件驱动模式 | File-Driven Mode

```
--mode file_driven --answers answers.json
```

从预置 JSON 文件读取所有人工裁决答案。适合脚本、CI/CD 或无人值守场景。
Read all human adjudication answers from a pre-configured JSON file. Suitable for scripts, CI/CD, or unattended scenarios.

### answers.json 格式 | Format

```json
{
    "confirm": "yes",
    "feature-1": "a",
    "feature-2": "r",
    "adjudicate_0": "o",
    "adjudicate_1": "a"
}
```

| 键 | Key | 值 | Value | 含义 | Meaning |
|----|-----|-----|-------|---------|
| `confirm` | `confirm` | `yes` / `no` | 是否确认进入下一阶段 | Whether to confirm advancing to next phase |
| 争议项引用 Dispute ref | `feature-1` | `a` / `r` / 自定义文本 custom text | `a`=采纳挑战方 accept challenger, `r`=接受提案方 accept proposer, 其他=自定义裁决 custom adjudication |
| `adjudicate_N` | `adjudicate_N` | 同上 same | 按索引匹配裁决项 | Match by index |

---

## 在 Claude Code 中使用 | Using in Claude Code

ProAgent 注册为 Claude Code Skill，可通过 `/adversarial-dev-flow` 命令直接在对话中调用。
ProAgent is registered as a Claude Code Skill and can be invoked directly in conversation via the `/adversarial-dev-flow` command.

### 启动新项目 | Start New Project

```
/adversarial-dev-flow start --project ./my-app --requirement "构建一个 Ubuntu 下的雷霆战机游戏"
```

### 查看状态 | Check Status

```
/adversarial-dev-flow status --project ./my-app
```

### 推进流水线 | Advance Pipeline

```
/adversarial-dev-flow resume --project ./my-app
```

### 跳转阶段 | Jump Phase

```
/adversarial-dev-flow jump --project ./my-app --phase 3
```

### 完整交互流程 | Complete Interaction Flow

```
用户 User: /adversarial-dev-flow start --project ./game --requirement "雷霆战机"
Claude Code:
  ✅ 项目已创建 | Project created
  📋 当前阶段: 阶段 1 - 需求精炼 | Current phase: Phase 1 - Requirement Refinement

用户 User: /adversarial-dev-flow resume --project ./game
Claude Code:
  [执行阶段 1: LLM 调用 AI产品经理 → AI产品审核 → 3轮对抗辩论]
  [Executing Phase 1: LLM calls PM → Reviewer → 3 rounds of debate]

  __PROAGENT_NEEDS_HUMAN__
  {"action_type": "confirm", "summary": "阶段 1 完成。是否确认?"}
  __PROAGENT_END_ACTION__

  ⏸️  阶段 1 等待人工确认。请审核后答复。| Phase 1 awaiting human confirmation.

用户 User: 确认，需求看起来不错 | Confirmed, requirements look good
Claude Code:
  [创建 answers.json: {"confirm": "yes"}]
  [Created answers.json: {"confirm": "yes"}]
  [重新运行 resume --answers answers.json]
  [Re-running resume --answers answers.json]
  阶段 1 ✅ → 阶段 2 开始...
  Phase 1 ✅ → Phase 2 started...
```

---

## 项目结构 | Project Structure

```
/home/pan/projects/proagent/
├── README.md                              # 本文件 | This file
├── pyproject.toml                         # Python 项目配置 | Project config
├── .claude/skills/adversarial-dev-flow/
│   ├── SKILL.md                           # Claude Code Skill 清单 | Skill manifest
│   └── run.py                             # Skill 入口脚本 | Entry script
└── src/proagent/
    ├── __init__.py
    ├── main.py                            # CLI 入口（Click 4 命令）| CLI entry (4 commands)
    │
    ├── config/
    │   ├── settings.py                    # 全局配置 + 环境变量解析 | Global config + env parsing
    │   └── roles.py                       # 8 个 AI 角色系统提示词 | 8 AI role system prompts
    │
    ├── llm/
    │   ├── client.py                      # Anthropic SDK 封装 | Anthropic SDK wrapper
    │   └── prompts.py                     # Proposer/Challenger/Rebuttal 提示词模板
    │
    ├── engine/
    │   ├── debate.py                      # 对抗辩论引擎（核心 3 轮循环）| Core 3-round loop
    │   └── judge.py                       # 规则化收敛/僵局检测 | Rule-based convergence/deadlock
    │
    ├── models/
    │   ├── state.py                       # PipelineState 主状态（7阶段 + 持久化）| Master state
    │   ├── requirements.py                # 需求文档：Feature, Scenario, Criterion, NFR
    │   ├── plan.py                        # 项目计划：TechStack, Task, Risk, RoleAssignment
    │   ├── blueprint.py                   # 蓝图：BlueprintUnit, UnitDAG（拓扑排序 + 验证）
    │   ├── unit.py                        # 开发单元：DevUnit, ReviewResult, UnitSummary
    │   ├── change.py                      # 变更请求：ChangeRequest, Impact, Decision
    │   └── milestone.py                   # 里程碑：MilestoneReport, Deviation, RiskAlert
    │
    ├── pipeline/
    │   ├── base.py                        # BasePhase 抽象基类（统一接口 + 共享逻辑）
    │   ├── conductor.py                   # PhaseConductor 编排器（串联 7 阶段）
    │   ├── phase1_requirements.py         # 阶段 1：需求精炼 | Requirement Refinement
    │   ├── phase2_planning.py             # 阶段 2：项目规划 | Project Planning
    │   ├── phase3_blueprint.py            # 阶段 3：蓝图设计 | Blueprint Design
    │   ├── phase4_development.py          # 阶段 4：单元开发 + 审查循环 | Dev + Review Loop
    │   ├── phase5_closure.py              # 阶段 5：环节与需求闭环 | Phase Closure
    │   ├── phase6_change_control.py       # 阶段 6：蓝图变更控制 | Change Control
    │   └── phase7_milestone.py            # 阶段 7：里程碑会议 | Milestone Meeting
    │
    ├── dag/
    │   └── graph.py                       # networkx DAG：拓扑排序/就绪检测/环检测
    │
    ├── human/
    │   └── interface.py                   # 人机交互：ClaudeCode/Interactive/FileDriven 三模式
    │
    └── persistence/
        └── store.py                       # JSON 原子持久化 + 备份恢复
```

## 配置参考 | Configuration Reference

所有配置可通过环境变量覆盖。
All settings can be overridden via environment variables.

| 环境变量 | Env Variable | 默认值 | Default | 说明 | Description |
|----------|-------------|--------|---------|-------------|
| `ANTHROPIC_API_KEY` | `ANTHROPIC_API_KEY` | - | **必填 Required**，Anthropic API 密钥 |
| `PROAGENT_MODEL` | `PROAGENT_MODEL` | `claude-opus-4-8` | 使用的 LLM 模型 | LLM model to use |
| `PROAGENT_MAX_TOKENS` | `PROAGENT_MAX_TOKENS` | `16000` | 每次 LLM 调用的最大 token 数 | Max tokens per LLM call |
| `PROAGENT_THINKING_TYPE` | `PROAGENT_THINKING_TYPE` | `adaptive` | 推理模式：adaptive / disabled | Thinking mode |
| `PROAGENT_EFFORT` | `PROAGENT_EFFORT` | `high` | 推理深度：low / medium / high / xhigh / max | Reasoning depth |
| `PROAGENT_MAX_DEBATE_ROUNDS` | `PROAGENT_MAX_DEBATE_ROUNDS` | `3` | 每阶段最大对抗辩论轮数 | Max debate rounds per phase |
| `PROAGENT_MAX_UNIT_REDO` | `PROAGENT_MAX_UNIT_REDO` | `3` | 每单元最大重做次数 | Max redo cycles per unit |
| `PROAGENT_PROJECTS_DIR` | `PROAGENT_PROJECTS_DIR` | `./projects` | 项目默认存储目录 | Default project storage directory |
