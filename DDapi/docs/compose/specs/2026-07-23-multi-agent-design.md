# Multi-Agent 架构设计文档

> 日期: 2026-07-23
> 状态: 设计阶段
> 目标: 将单 Agent 架构重构为 LangGraph Multi-Agent 架构

---

## 1. 架构概述

### 1.1 当前架构（单 Agent）

```
用户消息 → agent_node (9个工具) → tools_node → save_memory_node → 回复
```

**问题：**
- 所有工具描述都发给 LLM，token 消耗高
- 工具太多容易混淆，幻觉风险高
- 改一个工具影响全局

### 1.2 目标架构（Multi-Agent）

```
用户消息 → Supervisor → 子 Agent → save_memory_node → 回复
            (路由)      (执行工具)
```

**优势：**
- 每个 Agent 只带自己的工具，token 节省 30-50%
- 专注领域，准确率高
- 各 Agent 独立，易于维护和扩展

---

## 2. Agent 定义

### 2.1 Agent 清单

| Agent | 类型 | 工具数 | 职责 |
|-------|------|--------|------|
| Supervisor | 路由 | 0 | 分析意图，选择子 Agent |
| Calendar Agent | 执行 | 5 | 日程管理（创建/修改/查询/删除/列表） |
| Checkin Agent | 执行 | 1 | 签到记录查询 |
| Knowledge Agent | 执行 | 2 | 知识库检索 + 网页搜索 |
| General Agent | 执行 | 1 | 通用对话 + 发送消息 |

### 2.2 Supervisor Agent

**职责：** 理解用户意图，路由到合适的子 Agent

**输入：** 当前消息 + 最近 N 轮历史

**输出：** 选择的 Agent 名称（字符串）

**Prompt 设计：**
```python
SUPERVISOR_PROMPT = """你是一个路由助手，负责分析用户意图并选择合适的处理 Agent。

可选的 Agent：
- calendar: 日程管理相关（会议、行程、日程安排、提醒）
- checkin: 签到考勤相关（打卡、签到记录、考勤）
- knowledge: 知识查询相关（公司制度、文档、资料、搜索）
- general: 通用对话（闲聊、问候、无法分类的问题）

请只输出 Agent 名称，不要输出其他内容。"""
```

**实现方式：**
```python
# Supervisor 不使用工具，直接让 LLM 输出分类
def supervisor_node(state):
    response = llm.invoke([
        SystemMessage(content=SUPERVISOR_PROMPT),
        *state["history"][-6:],  # 最近 3 轮历史
        HumanMessage(content=state["messages"][-1].content)
    ])
    agent_name = response.content.strip().lower()
    return {"next": agent_name}  # 路由到对应 Agent
```

### 2.3 Calendar Agent

**职责：** 处理所有日程相关请求

**工具：**
- `create_calendar_event` — 创建日程
- `update_calendar_event` — 修改日程
- `get_calendar_event` — 查询日程详情
- `delete_calendar_event` — 删除日程
- `list_calendar_events` — 查询日程列表

**Prompt 设计：**
```python
CALENDAR_PROMPT = """你是日程管理助手，帮用户查询、创建、修改、删除钉钉日程。

当前日期：{current_date}

使用规范：
- 查询日程时，如果不指定时间，默认查今天和明天
- 创建日程需要确认标题、开始时间、结束时间
- 修改/删除日程需要先获取事件ID
- 回复要简洁明了"""
```

### 2.4 Checkin Agent

**职责：** 处理签到考勤查询

**工具：**
- `get_checkin_records` — 获取签到记录

**Prompt 设计：**
```python
CHECKIN_PROMPT = """你是签到考勤助手，帮用户查询钉钉签到记录。

使用规范：
- 如果不指定时间，默认查询最近一周
- 支持查询多个用户的签到记录
- 回复要简洁，列出关键信息"""
```

### 2.5 Knowledge Agent

**职责：** 处理知识查询和搜索

**工具：**
- `search_doc` — 知识库文档检索
- `search_web` — 互联网搜索

**Prompt 设计：**
```python
KNOWLEDGE_PROMPT = """你是知识查询助手，帮用户检索内部文档和互联网信息。

使用规范：
- 优先查内部知识库，找不到再搜互联网
- 引用来源，提高可信度
- 回复要准确、有据可查"""
```

### 2.6 General Agent

**职责：** 处理通用对话和无法分类的请求

**工具：**
- `send_private_message` — 发送钉钉消息

**Prompt 设计：**
```python
GENERAL_PROMPT = """你是通用对话助手，处理闲聊、问候和无法分类的问题。

风格：
- 保持小白的人设（毒舌但暖心）
- 如果用户需求可以明确分类，建议用户重新描述
- 可以发送消息给用户"""
```

---

## 3. 状态管理

### 3.1 状态定义

```python
class AgentState(TypedDict):
    messages: Annotated[list[Any], add_messages]  # 当前对话消息
    user_id: str                                   # 用户ID
    summary: str                                   # 用户画像
    history: list                                  # Redis 中的历史消息
    next: str                                      # Supervisor 路由结果
```

### 3.2 状态流转

```
┌─────────────────────────────────────────────────────────────┐
│                        状态流转                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  START                                                      │
│    │                                                        │
│    ▼                                                        │
│  supervisor_node                                            │
│    │  设置 state["next"] = "calendar" | "checkin" | ...    │
│    │                                                        │
│    ▼                                                        │
│  条件路由                                                    │
│    ├── calendar_node ──→ tools_node ──→ supervisor_node    │
│    ├── checkin_node  ──→ tools_node ──→ supervisor_node    │
│    ├── knowledge_node ──→ tools_node ──→ supervisor_node   │
│    └── general_node  ──→ END                               │
│                                                             │
│  save_memory_node ──→ (summary_node?) ──→ END              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 共享上下文

所有 Agent 共享以下状态：
- `messages` — 当前对话的完整消息列表
- `history` — Redis 中的历史消息
- `summary` — 用户画像

这意味着：
- 用户问完日程再问签到，Checkin Agent 可以看到之前的日程对话
- 所有 Agent 都能访问用户画像，提供个性化服务

---

## 4. LangGraph 图结构

### 4.1 节点定义

```python
# 节点列表
nodes = [
    "supervisor",       # 路由节点
    "calendar_agent",   # 日程 Agent
    "checkin_agent",    # 签到 Agent
    "knowledge_agent",  # 知识 Agent
    "general_agent",    # 通用 Agent
    "tools_node",       # 工具执行节点（共享）
    "save_memory",      # 记忆保存节点
    "summary_node",     # 画像总结节点
]
```

### 4.2 边定义

```python
# 普通边
workflow.add_edge(START, "supervisor")
workflow.add_edge("save_memory", END)
workflow.add_edge("summary_node", END)

# 条件边：Supervisor 路由
workflow.add_conditional_edges(
    "supervisor",
    lambda state: state["next"],  # 根据 next 字段路由
    {
        "calendar": "calendar_agent",
        "checkin": "checkin_agent",
        "knowledge": "knowledge_agent",
        "general": "general_agent",
    }
)

# 条件边：子 Agent 决定是调用工具还是结束
for agent in ["calendar_agent", "checkin_agent", "knowledge_agent", "general_agent"]:
    workflow.add_conditional_edges(
        agent,
        should_continue,  # 判断是否有工具调用
        {
            "tools": "tools_node",
            "save_memory": "save_memory",
        }
    )

# 工具执行后回到对应 Agent
workflow.add_conditional_edges(
    "tools_node",
    lambda state: state["current_agent"],  # 记录当前 Agent
    {
        "calendar_agent": "calendar_agent",
        "checkin_agent": "checkin_agent",
        "knowledge_agent": "knowledge_agent",
        "general_agent": "general_agent",
    }
)

# 条件边：是否需要画像总结
workflow.add_conditional_edges(
    "save_memory",
    should_summarize,
    {
        "summarize": "summary_node",
        END: END,
    }
)
```

### 4.3 完整图结构

```
                    ┌─────────────────────────────────────┐
                    │              START                   │
                    └─────────────────┬───────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │           supervisor                 │
                    │   (分析意图，设置 state["next"])      │
                    └─────────────────┬───────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
              ▼                       ▼                       ▼
    ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
    │ calendar_agent   │   │ checkin_agent    │   │ knowledge_agent  │
    │ (日程工具)       │   │ (签到工具)       │   │ (知识+搜索工具)  │
    └────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘
             │                      │                       │
             │    ┌─────────────────┴───────────────────────┘
             │    │
             ▼    ▼
    ┌──────────────────────────────────────────────────────────────────┐
    │                         tools_node                               │
    │              (执行工具，返回结果给对应 Agent)                      │
    └──────────────────────────────────────────────────────────────────┘
             │                      │                       │
             ▼                      ▼                       ▼
    ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
    │ calendar_agent   │   │ checkin_agent    │   │ knowledge_agent  │
    │ (继续或结束)     │   │ (继续或结束)     │   │ (继续或结束)     │
    └────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘
             │                      │                       │
             └──────────────────────┼───────────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────────┐
                    │          save_memory                 │
                    │   (保存对话 + 更新轮数)               │
                    └─────────────────┬───────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │       should_summarize?              │
                    │   (检查是否需要画像总结)              │
                    └─────────────────┬───────────────────┘
                                      │
                           ┌──────────┴──────────┐
                           │                     │
                           ▼                     ▼
                ┌──────────────────┐   ┌──────────────────┐
                │ summary_node     │   │       END        │
                │ (LLM生成画像)    │   │                  │
                └──────────────────┘   └──────────────────┘
```

---

## 5. 并发控制

### 5.1 用户级串行

```python
import threading

# 用户锁字典
user_locks = {}
lock_dict_lock = threading.Lock()

def get_user_lock(user_id):
    """获取用户的锁"""
    with lock_dict_lock:
        if user_id not in user_locks:
            user_locks[user_id] = threading.Lock()
        return user_locks[user_id]

def chat(user_id, message):
    """处理对话（带用户级锁）"""
    lock = get_user_lock(user_id)
    with lock:
        # 同一用户的对话串行处理
        return _process_chat(user_id, message)
```

### 5.2 处理流程

```
用户A 消息1 ──→ 获取锁A ──→ 处理 ──→ 释放锁A ──→ 回复
用户A 消息2 ──→ 等待锁A ──→ 获取锁A ──→ 处理 ──→ 释放锁A ──→ 回复
用户B 消息1 ──→ 获取锁B ──→ 处理 ──→ 释放锁B ──→ 回复（与A并行）
```

---

## 6. 代码结构

### 6.1 文件组织

```
scripts/
├── main.py                    # 启动入口
├── config.py                  # 配置文件
├── tools/
│   ├── __init__.py
│   ├── tools.py               # 工具定义（保持不变）
│   ├── processMsg.py          # 消息处理器（修改）
│   ├── memory_store.py        # 记忆存储（保持不变）
│   └── agents/
│       ├── __init__.py
│       ├── supervisor.py      # Supervisor Agent
│       ├── calendar.py        # Calendar Agent
│       ├── checkin.py         # Checkin Agent
│       ├── knowledge.py       # Knowledge Agent
│       └── general.py         # General Agent
├── graph/
│   ├── __init__.py
│   ├── state.py               # 状态定义
│   ├── builder.py             # 图构建器
│   └── router.py              # 路由逻辑
└── rag/
    ├── info_index.py
    └── build_index.py
```

### 6.2 核心代码

#### state.py — 状态定义

```python
from typing import TypedDict, Annotated, Any
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list[Any], add_messages]
    user_id: str
    summary: str
    history: list
    next: str           # Supervisor 路由结果
    current_agent: str  # 当前执行的 Agent
```

#### supervisor.py — Supervisor Agent

```python
from langchain_core.messages import HumanMessage, SystemMessage
import config

SUPERVISOR_PROMPT = """你是一个路由助手，负责分析用户意图并选择合适的处理 Agent。

可选的 Agent：
- calendar: 日程管理相关（会议、行程、日程安排、提醒）
- checkin: 签到考勤相关（打卡、签到记录、考勤）
- knowledge: 知识查询相关（公司制度、文档、资料、搜索）
- general: 通用对话（闲聊、问候、无法分类的问题）

请只输出 Agent 名称，不要输出其他内容。"""

def create_supervisor_node(llm, memory):
    """创建 Supervisor 节点"""
    def supervisor_node(state):
        user_id = state["user_id"]
        history = memory.get_history_messages(user_id)
        
        response = llm.invoke([
            SystemMessage(content=SUPERVISOR_PROMPT),
            *history[-6:],  # 最近 3 轮历史
            HumanMessage(content=state["messages"][-1].content)
        ])
        
        agent_name = response.content.strip().lower()
        # 验证是否是有效的 Agent 名称
        valid_agents = ["calendar", "checkin", "knowledge", "general"]
        if agent_name not in valid_agents:
            agent_name = "general"
        
        return {"next": agent_name}
    
    return supervisor_node
```

#### calendar.py — Calendar Agent

```python
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from datetime import datetime

CALENDAR_PROMPT = """你是日程管理助手，帮用户查询、创建、修改、删除钉钉日程。

当前日期：{current_date}

使用规范：
- 查询日程时，如果不指定时间，默认查今天和明天
- 创建日程需要确认标题、开始时间、结束时间
- 修改/删除日程需要先获取事件ID
- 回复要简洁明了"""

def create_calendar_node(llm, tools):
    """创建 Calendar Agent 节点"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", CALENDAR_PROMPT),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ])
    
    chain = prompt | llm.bind_tools(tools)
    
    def calendar_node(state):
        response = chain.invoke({
            "history": state.get("history", []),
            "input": state["messages"][-1].content,
            "current_date": datetime.now().strftime("%Y-%m-%d"),
        })
        return {
            "messages": [response],
            "current_agent": "calendar_agent",
        }
    
    return calendar_node
```

#### builder.py — 图构建器

```python
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from tools.graph.state import AgentState
from tools.agents.supervisor import create_supervisor_node
from tools.agents.calendar import create_calendar_node
from tools.agents.checkin import create_checkin_node
from tools.agents.knowledge import create_knowledge_node
from tools.agents.general import create_general_node

def build_multi_agent_graph(llm, memory, checkpointer):
    """构建 Multi-Agent 图"""
    
    # 创建工具列表
    from tools.tools import create_tools
    all_tools = create_tools()
    
    # 按 Agent 分组工具
    calendar_tools = [t for t in all_tools if t.name in [
        "create_calendar_event", "update_calendar_event", 
        "get_calendar_event", "delete_calendar_event", "list_calendar_events"
    ]]
    checkin_tools = [t for t in all_tools if t.name in ["get_checkin_records"]]
    knowledge_tools = [t for t in all_tools if t.name in ["search_doc", "search_web"]]
    general_tools = [t for t in all_tools if t.name in ["send_private_message"]]
    
    # 创建节点
    supervisor = create_supervisor_node(llm, memory)
    calendar_agent = create_calendar_node(llm, calendar_tools)
    checkin_agent = create_checkin_node(llm, checkin_tools)
    knowledge_agent = create_knowledge_node(llm, knowledge_tools)
    general_agent = create_general_node(llm, general_tools)
    
    # 创建共享的 ToolNode
    tools_node = ToolNode(all_tools)
    
    # 构建图
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("supervisor", supervisor)
    workflow.add_node("calendar_agent", calendar_agent)
    workflow.add_node("checkin_agent", checkin_agent)
    workflow.add_node("knowledge_agent", knowledge_agent)
    workflow.add_node("general_agent", general_agent)
    workflow.add_node("tools_node", tools_node)
    workflow.add_node("save_memory", save_memory_node)
    workflow.add_node("summary_node", summary_node)
    
    # 添加边
    workflow.add_edge(START, "supervisor")
    
    # Supervisor 路由
    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state["next"],
        {
            "calendar": "calendar_agent",
            "checkin": "checkin_agent",
            "knowledge": "knowledge_agent",
            "general": "general_agent",
        }
    )
    
    # 子 Agent → tools 或 save_memory
    for agent in ["calendar_agent", "checkin_agent", "knowledge_agent", "general_agent"]:
        workflow.add_conditional_edges(
            agent,
            lambda state: "tools" if hasattr(state["messages"][-1], "tool_calls") 
                          and state["messages"][-1].tool_calls else "save_memory",
            {
                "tools": "tools_node",
                "save_memory": "save_memory",
            }
        )
    
    # tools → 回到对应 Agent
    workflow.add_conditional_edges(
        "tools_node",
        lambda state: state.get("current_agent", "general_agent"),
        {
            "calendar_agent": "calendar_agent",
            "checkin_agent": "checkin_agent",
            "knowledge_agent": "knowledge_agent",
            "general_agent": "general_agent",
        }
    )
    
    # save_memory → END 或 summary
    workflow.add_conditional_edges(
        "save_memory",
        lambda state: "summarize" if memory.should_summarize(state["user_id"]) else END,
        {
            "summarize": "summary_node",
            END: END,
        }
    )
    
    workflow.add_edge("summary_node", END)
    
    return workflow.compile(checkpointer=checkpointer)
```

---

## 7. 实施计划

### 7.1 阶段划分

| 阶段 | 任务 | 预计时间 |
|------|------|----------|
| 1 | 创建文件结构，定义状态 | 30分钟 |
| 2 | 实现 Supervisor Agent | 1小时 |
| 3 | 实现各子 Agent | 2小时 |
| 4 | 构建图，集成测试 | 1小时 |
| 5 | 添加并发控制 | 30分钟 |
| 6 | 端到端测试 | 1小时 |

### 7.2 依赖关系

```
阶段1 (文件结构)
    │
    ├──→ 阶段2 (Supervisor)
    │        │
    │        └──→ 阶段3 (子 Agents)
    │                 │
    │                 └──→ 阶段4 (图构建)
    │                          │
    │                          └──→ 阶段5 (并发控制)
    │                                   │
    │                                   └──→ 阶段6 (测试)
```

---

## 8. 注意事项

### 8.1 兼容性

- 保持现有工具定义不变
- 保持现有记忆系统不变
- 保持现有钉钉消息处理流程不变

### 8.2 风险点

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Supervisor 路由不准 | 用户体验差 | 添加 fallback 到 General Agent |
| 工具调用失败 | 功能不可用 | 保持现有错误处理 |
| 并发死锁 | 系统卡住 | 设置锁超时 |

### 8.3 测试策略

1. **单元测试** — 每个 Agent 独立测试
2. **集成测试** — 测试路由和工具调用
3. **端到端测试** — 模拟真实用户对话
4. **并发测试** — 多用户同时发消息

---

## 9. 附录

### 9.1 参考资料

- [LangGraph Multi-Agent](https://langchain-ai.github.io/langgraph/concepts/multi_agent/)
- [LangGraph Supervisor](https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/)

### 9.2 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-07-23 | 1.0 | 初始设计文档 |
