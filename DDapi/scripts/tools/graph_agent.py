'''
LangGraph 图智能体
使用 MessagesPlaceholder 注入对话历史
'''
from typing import TypedDict, Annotated, Any
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import config
from tools.tools import create_tools
from tools.memory_store import MemoryStore

# 初始化
memory = MemoryStore()
tools = create_tools(memory)
llm = config.llm
llm_with_tools = llm.bind_tools(tools)

# Redis Checkpointer
from langgraph.checkpoint.redis import RedisSaver
checkpointer_cm = RedisSaver.from_conn_string(config.redis_url)
checkpointer = checkpointer_cm.__enter__()
checkpointer.setup()


# 定义状态
class AgentState(TypedDict):
    messages: Annotated[list[Any], add_messages]
    user_id: str
    summary: str  # 用户画像


# 构建 prompt 模板
def build_prompt(summary=""):
    """构建带 MessagesPlaceholder 的 prompt"""
    system_msg = config.system_text
    if summary:
        system_msg += f"\n\n【用户画像】\n{summary}"
    return ChatPromptTemplate.from_messages([
        ("system", system_msg),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ])


# ------------------------节点------------------------
def agent_node(state: AgentState):
    """Agent 节点：LLM 决策是否调用工具"""
    summary = state.get("summary", "")
    prompt = build_prompt(summary)
    chain = prompt | llm_with_tools

    response = chain.invoke({
        "history": state["messages"][:-1],  # 除当前消息外的历史
        "input": state["messages"][-1].content,
    })
    return {"messages": [response]}


def save_memory_node(state: AgentState):
    """保存本轮对话到记忆系统"""
    user_id = state["user_id"]
    messages = state["messages"]

    user_msg = None
    ai_msg = None
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and ai_msg is None:
            ai_msg = msg
        elif isinstance(msg, HumanMessage) and user_msg is None:
            user_msg = msg
        if user_msg and ai_msg:
            break

    if user_msg and ai_msg:
        memory.save_turn(user_id, user_msg.content, ai_msg.content)
        memory.increment_turn(user_id)
    return {}


def summary_node(state: AgentState):
    """用户画像总结节点"""
    user_id = state["user_id"]
    current_summary = state.get("summary", "")

    prompt_text = memory.build_summary_prompt(user_id, current_summary)
    if prompt_text:
        response = llm.invoke([HumanMessage(content=prompt_text)])
        new_summary = response.content
        memory.set_summary(user_id, new_summary)
        memory.reset_turn_count(user_id)
        memory.compact_history_after_summary(user_id)
        return {"summary": new_summary}
    return {}


# ------------------------条件边------------------------
def after_save_memory(state: AgentState):
    """判断是否需要触发画像总结"""
    user_id = state["user_id"]
    if memory.should_summarize(user_id):
        return "summarize"
    return END


# ------------------------构建图------------------------
def build_graph():
    workflow = StateGraph(AgentState)

    # 定义节点
    workflow.add_node("agent_node", agent_node)
    workflow.add_node("tools_node", ToolNode(tools))
    workflow.add_node("save_memory_node", save_memory_node)
    workflow.add_node("summary_node", summary_node)

    # 定义边
    workflow.add_edge(START, "agent_node")
    workflow.add_conditional_edges(
        "agent_node",
        lambda state: "tools" if hasattr(state["messages"][-1], "tool_calls") and state["messages"][-1].tool_calls else "save_memory",
        {
            "tools": "tools_node",
            "save_memory": "save_memory_node"
        }
    )
    workflow.add_edge("tools_node", "agent_node")
    workflow.add_conditional_edges(
        "save_memory_node",
        after_save_memory,
        {
            "summarize": "summary_node",
            END: END
        }
    )
    workflow.add_edge("summary_node", END)

    return workflow.compile(checkpointer=checkpointer)


# ------------------------对外接口------------------------
graph = build_graph()


def chat(user_id: str, message: str):
    """处理一轮对话"""
    summary = memory.get_summary(user_id)
    history_messages = memory.get_history_messages(user_id)

    result = graph.invoke(
        {
            "messages": [HumanMessage(content=message)],
            "user_id": user_id,
            "summary": summary,
        },
        config={"configurable": {"thread_id": user_id}}
    )

    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage):
            return msg.content

    return "抱歉，处理消息时出现错误"
