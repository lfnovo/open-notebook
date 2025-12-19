# Open Notebook Agent 增强设计方案

## 1. 设计目标

将 Open Notebook 从一个被动的笔记工具升级为一个主动的 **研究助手 Agent**，具备：

- **自主搜索**: 根据用户问题自动搜索知识库
- **多步骤推理**: 执行复杂的研究任务
- **笔记管理**: 自动创建、整理和关联笔记
- **知识整合**: 跨来源整合信息并生成洞察

## 2. 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React/Next.js)                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Chat Panel  │  │ Agent Panel │  │ Tool Execution View │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              /api/agent/execute                      │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Agent                          │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │
│  │ Planner │───▶│ Executor│───▶│ Reflect │───▶│ Output  │  │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘  │
│       │              │                                      │
│       ▼              ▼                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   Tool Registry                      │    │
│  │  • search_knowledge_base    • create_note           │    │
│  │  • get_source_content       • run_transformation    │    │
│  │  • list_sources             • web_search (optional) │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## 3. 核心组件

### 3.1 工具定义 (Tools)

| 工具名称 | 功能描述 | 参数 |
|---------|---------|------|
| `search_knowledge_base` | 在知识库中搜索相关内容 | `query`, `search_type`, `limit` |
| `get_source_content` | 获取指定来源的完整内容 | `source_id` |
| `get_source_insights` | 获取来源的所有洞察 | `source_id` |
| `create_note` | 创建新笔记 | `title`, `content`, `notebook_id` |
| `update_note` | 更新现有笔记 | `note_id`, `content` |
| `list_sources` | 列出笔记本中的所有来源 | `notebook_id` |
| `run_transformation` | 执行转换（摘要/翻译/提取） | `source_id`, `transformation_type` |
| `web_search` | 网络搜索（可选） | `query` |

### 3.2 Agent 状态定义

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]  # 对话历史
    notebook_id: Optional[str]               # 当前笔记本
    task: str                                # 用户任务
    plan: Optional[List[str]]                # 执行计划
    tool_calls: List[ToolCall]               # 工具调用记录
    observations: List[str]                  # 工具执行结果
    final_answer: Optional[str]              # 最终答案
    api_key: Optional[str]                   # 用户 API Key
```

### 3.3 Agent 图流程

```
START
  │
  ▼
┌─────────────────┐
│   Plan Task     │  ← 分析任务，制定执行计划
└─────────────────┘
  │
  ▼
┌─────────────────┐
│  Execute Step   │  ← 执行计划中的一步（调用工具）
└─────────────────┘
  │
  ├──────────────────┐
  ▼                  │
┌─────────────────┐  │
│   Observe       │  │  ← 观察工具执行结果
└─────────────────┘  │
  │                  │
  ▼                  │
┌─────────────────┐  │
│   Should        │──┘  ← 是否需要继续执行？
│   Continue?     │
└─────────────────┘
  │ No
  ▼
┌─────────────────┐
│ Generate Answer │  ← 生成最终答案
└─────────────────┘
  │
  ▼
 END
```

## 4. 实现计划

### Phase 1: 工具层 ✅ 已完成
- [x] 创建 `open_notebook/graphs/agent_tools.py`
- [x] 实现核心工具函数：
  - `search_knowledge_base` - 向量/文本搜索
  - `get_source_content` - 获取来源内容
  - `get_source_insights` - 获取洞察
  - `create_note` - 创建笔记
  - `update_note` - 更新笔记
  - `list_notebook_sources` - 列出来源
  - `list_notebook_notes` - 列出笔记
  - `get_current_datetime` - 获取时间

### Phase 2: Agent 图 ✅ 已完成
- [x] 创建 `open_notebook/graphs/agent.py`
- [x] 实现 ReAct 风格的 Agent 图
- [x] 集成工具调用
- [x] 支持流式输出

### Phase 3: API 层 ✅ 已完成
- [x] 创建 `api/routers/agent.py`
- [x] `/api/agent/execute` - 同步执行
- [x] `/api/agent/stream` - SSE 流式输出
- [x] `/api/agent/tools` - 列出可用工具
- [x] BYOK 支持

### Phase 4: 前端 ✅ 已完成
- [x] 创建 `frontend/src/lib/types/agent.ts` - 类型定义
- [x] 创建 `frontend/src/lib/api/agent.ts` - API 客户端
- [x] 创建 `frontend/src/lib/hooks/useAgent.ts` - Agent Hook
- [x] 创建 `frontend/src/components/agent/AgentPanel.tsx` - Agent 面板
- [x] 更新 `ChatColumn.tsx` - 添加 Chat/Agent 模式切换
- [x] 显示思考过程和工具调用
- [x] 支持 DeepSeek / Qwen 模型选择

## 5. 使用示例

### 用户输入
```
帮我研究一下量子计算的最新进展，并整理成一份笔记
```

### Agent 执行流程
```
[思考] 用户想要研究量子计算，我需要：
1. 搜索知识库中关于量子计算的内容
2. 如果内容不足，可能需要提示用户添加来源
3. 整理搜索结果
4. 创建一份结构化的笔记

[执行] 调用 search_knowledge_base("量子计算", limit=10)
[观察] 找到 3 个相关来源：
  - source:abc123: "量子计算入门"
  - source:def456: "2024年量子计算突破"
  - source:ghi789: "量子比特技术"

[执行] 调用 get_source_insights("source:abc123")
[观察] 获取到 5 条洞察...

[执行] 调用 create_note(
  title="量子计算研究笔记",
  content="## 概述\n...",
  notebook_id="notebook:xyz"
)
[观察] 笔记创建成功，ID: note:new123

[回答] 我已经帮您整理了一份关于量子计算的研究笔记。
笔记包含以下内容：
1. 量子计算基础概念
2. 2024年最新进展
3. 关键技术突破
您可以在笔记列表中查看详情。
```

## 6. 技术考量

### 6.1 错误处理
- 工具调用失败时的重试策略
- 超时处理
- 用户中断支持

### 6.2 性能优化
- 工具调用并行化（当可能时）
- 缓存常用查询结果
- 限制最大执行步数

### 6.3 安全性
- API Key 不记录到日志
- 工具权限控制
- 输入验证

## 7. 支持的模型

当前 Agent 系统支持以下 AI 模型：

### DeepSeek
- **提供商**: deepseek
- **API Key 环境变量**: `DEEPSEEK_API_KEY`
- **模型列表**:
  - `deepseek-chat` - 日常对话，高性价比
  - `deepseek-reasoner` - 复杂推理任务

### Qwen (通义千问)
- **提供商**: openai_compatible (DashScope API)
- **API Key 环境变量**: `OPENAI_COMPATIBLE_API_KEY_LLM`
- **Base URL**: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- **模型列表**:
  - `qwen-turbo` - 快速响应
  - `qwen-plus` - 均衡性能
  - `qwen-max` - 最强能力
  - `qwen-long` - 长上下文 (100K+)

### 配置示例

参考 `.env.deepseek-qwen` 文件进行配置。

## 8. 后续扩展

- **多 Agent 协作**: 专家 Agent 分工合作
- **记忆系统**: 长期记忆和用户偏好
- **外部集成**: 网络搜索、学术数据库
- **自动化工作流**: 定时任务和触发器
