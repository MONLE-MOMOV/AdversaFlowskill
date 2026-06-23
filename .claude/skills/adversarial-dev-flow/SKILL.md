# Adversarial Development Flow

多角色对抗式 AI 开发流程 —— 通过 7 个阶段的 AI 角色结构化对抗辩论，
将模糊需求转化为高质量软件交付。

## 执行指令

当用户调用此 skill 时，你必须运行以下 Python CLI 命令。
**所有命令在 `/home/pan/projects/proagent` 目录下执行。**

### 启动新项目
```bash
PYTHONPATH=/home/pan/projects/proagent/src python3 -m proagent.main start \
  --project <项目目录> --requirement "<需求描述>"
```

### 查看项目状态
```bash
PYTHONPATH=/home/pan/projects/proagent/src python3 -m proagent.main status \
  --project <项目目录>
```

### 恢复/推进流水线（Claude Code 模式）
```bash
PYTHONPATH=/home/pan/projects/proagent/src python3 -m proagent.main resume \
  --project <项目目录> --mode claude_code
```

### Claude Code 人工裁决协议

当 `resume` 命令输出 `__PROAGENT_NEEDS_HUMAN__` 标记时，
表示流水线需要人工裁决。标记后紧跟的 JSON 描述了裁决需求：

**confirm 类型**（确认是否继续）:
```json
{
  "action_type": "confirm",
  "summary": "阶段 N 完成。状态: converged..."
}
```

**adjudicate 类型**（裁决争议项）:
```json
{
  "action_type": "adjudicate",
  "item_count": 2,
  "items": [
    {"index": 0, "item_ref": "...", "severity": "major", ...}
  ]
}
```

此时你必须：
1. 向用户展示裁决内容
2. 收集用户决定
3. 创建 `answers.json` 文件
4. 重新运行 resume（带 --answers 参数）

**answers.json 格式示例**:
```json
{
  "confirm": "yes",
  "feature-1": "a",
  "feature-2": "r"
}
```

**重新运行注入答案**:
```bash
PYTHONPATH=/home/pan/projects/proagent/src python3 -m proagent.main resume \
  --project <项目目录> --mode claude_code --answers <项目目录>/answers.json
```

## 注意事项

- 需要设置环境变量 `ANTHROPIC_API_KEY`
- 状态自动保存到 `<项目目录>/state.json`
- 每次遇到人工裁决会停止，需提供答案后继续
