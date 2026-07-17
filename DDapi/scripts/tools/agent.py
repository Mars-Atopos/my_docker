'''
小白机器人 - Agent模块
功能：创建LangChain Agent，提供chat()函数
'''

import json
import redis
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, messages_from_dict
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent

import config
from tools.tools import create_tools
from tools.memory_store import MemoryStore

# 初始化记忆
memory = MemoryStore()

# 创建工具
tools = create_tools(memory)

# 创建提示模板
prompt = ChatPromptTemplate.from_messages([
    ("system", config.system_text),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# 创建Agent
llm = config.llm
agent = create_tool_calling_agent(llm, tools, prompt)

# 创建执行器
executor = AgentExecutor(
    agent=agent,
    tools=tools,
    handle_parsing_errors=True,
    max_iterations=5,
    verbose=False,
)

# Redis聊天历史实现
class RedisChatMessageHistory(BaseChatMessageHistory):
    """Redis聊天历史，key 前缀 lc:，与 MemoryStore 的 mem: 前缀区分"""

    def __init__(self, session_id, redis_url, key_prefix="lc:", ttl=None, max_history=20):
        self.session_id = session_id
        self.key_prefix = key_prefix
        self.ttl = ttl
        self.max_history = max_history
        self.redis_client = redis.from_url(redis_url)

    @property
    def _key(self):
        return f"{self.key_prefix}{self.session_id}:history"

    @property
    def messages(self):
        """获取所有消息"""
        raw = self.redis_client.lrange(self._key, 0, -1)
        if not raw:
            return []
        messages_data = [json.loads(item) for item in raw]
        return messages_from_dict(messages_data)

    def add_message(self, message):
        """添加消息"""
        data = {
            "type": message.type,
            "data": {
                "content": message.content,
                "additional_kwargs": message.additional_kwargs,
                "type": message.type,
            }
        }
        self.redis_client.rpush(self._key, json.dumps(data, ensure_ascii=False))
        self.redis_client.ltrim(self._key, -self.max_history, -1)
        if self.ttl:
            self.redis_client.expire(self._key, self.ttl)

    def clear(self):
        """清空历史"""
        self.redis_client.delete(self._key)

# 创建带历史记录的链
def get_session_history(session_id):
    return RedisChatMessageHistory(
        session_id=session_id,
        redis_url=config.redis_url,
        key_prefix="lc:",
        ttl=None,
        max_history=20,
    )

chain_with_history = RunnableWithMessageHistory(
    runnable=executor,
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)

def _format_recent_for_context(history_messages, n=10):
    """将 LangChain 消息格式化为 prompt 可读的最近对话文本"""
    recent = history_messages[-(n * 2):] if len(history_messages) > n * 2 else history_messages
    if not recent:
        return ""
    lines = []
    for msg in recent:
        role = "用户" if isinstance(msg, HumanMessage) else "小白"
        lines.append(f"{role}: {msg.content}")
    return "\n".join(lines)

def chat(user_id, message):
    """处理一轮对话"""
    session_id = memory.get_session_id(user_id)

    # 从 LangChain 读取最近对话，传给 MemoryStore 组装上下文
    history = get_session_history(session_id)
    recent_text = _format_recent_for_context(history.messages)
    memory_context = memory.build_context(user_id, recent_history=recent_text)

    # 构建完整消息
    if memory_context:
        full_message = f"{memory_context}\n\n用户说: {message}"
    else:
        full_message = message

    # 调用Agent（LangChain 自动保存对话历史）
    config_dict = {"configurable": {"session_id": session_id}}
    result = chain_with_history.invoke({"input": full_message}, config=config_dict)

    return result["output"]
