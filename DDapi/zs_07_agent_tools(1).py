
import os
from datetime import datetime
import time
from typing import Any

from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
# https://app.tavily.com/home
from langchain_redis.chat_message_history import RedisChatMessageHistory
from pydantic import BaseModel, Field
import requests
from tavily import TavilyClient
from ulid import ULID
import util
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from dotenv import load_dotenv
load_dotenv()
# 初始化 Tavily 客户端
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
token = "59db1fc76ae03c88824a80efe0dcd10d"
union_id = "GGaudRG79v5jHq5tyw1cKAiEiE"
# 定义搜索工具
@tool
def search_web(query: str) -> str:
    """搜索互联网获取最新信息。
    Args:
        query: 搜索关键词。
    用于新闻、天气、实时事件等需要联网查询的问题。
    """
    try:
        print("search_web---------------")
        # 调用搜索工具，查询关键词，获取最多 3 条结果
        result = tavily_client.search(query, max_results=3)
        sumaries = [item["content"] for item in result.get("results", [])]
        return "\n".join(sumaries) if sumaries else "未找到相关的信息"
    except Exception as e:
        return f"搜索失败：{str(e)}"

class TodoInput(BaseModel):
    subject: str = Field(description="待办事项标题")
    dueTime: int = Field(None, description="所有时间统一采用 UTC+8 北京时间；时间戳单位为毫秒；示例时间戳：1617675000000；本机Windows系统当前毫秒时间戳：{}".format(int(time.time() * 1000)))
    description: str = Field(None, description="待办事项描述")
    priority: int = Field(0, description="优先级 10：较低 20：普通 30：紧急 40：非常紧急")


# # DingTalk API 客户端
class DingTalkClient:
    def __init__(self):
        self.app_key = os.getenv("client_id")
        self.app_secret = os.getenv("client_secret")
        self.union_id = os.getenv("union_id")
        
    def get_access_token(self) -> str:
        if not all([self.app_key, self.app_secret, self.union_id]):
            raise ValueError("钉钉配置信息不完整")
            
        try:
            response = requests.post(
                "https://api.dingtalk.com/v1.0/oauth2/accessToken",
                json={"appKey": self.app_key, "appSecret": self.app_secret}
            )
            response.raise_for_status()
            token = response.json().get("accessToken")
            print("DingTalk Token:", token)
            if not token:
                raise ValueError("获取钉钉访问令牌失败")
            return token
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"获取访问令牌失败: {str(e)}")

@tool
def todo_task(todo: TodoInput) -> str:
    """创建一个待办事项
    Args:
        todo: 包含待办事项信息的对象
    Returns:
        str: 创建结果消息
    """
    token = DingTalkClient().get_access_token()
    todo_data = {
        "subject": todo.subject,
        "notifyConfigs": {"dingNotify": "1"}
    }
    if todo.dueTime:
        todo_data["dueTime"] = todo.dueTime
    # todo_data["executorIds"] = [client.union_id]
    # todo_data["participantIds"] = [client.union_id]
    try:
        response = requests.post(
            f"https://api.dingtalk.com/v1.0/todo/users/{union_id}/tasks",
            headers={
                "Content-Type": "application/json",
                "x-acs-dingtalk-access-token": token
            },
            json=todo_data
        )
        # 判断 HTTP 请求返回码是否为错误状态码
        response.raise_for_status()
        print("success:", todo_data)
        return f"成功创建待办事项: {todo.subject}"
    except requests.exceptions.RequestException as e:
        print("创建待办事项失败")
        return f"创建待办事项失败: {str(e)}"

class LongBufferMemory(RedisChatMessageHistory):
    """长期记忆：覆写父类的方法，对信息可以做筛选"""
    def add_message(self, message):
        super().add_message(message)
        print(message)
        

def get_session_history(session_id: str) -> LongBufferMemory:
    return LongBufferMemory(
        session_id=session_id,
        redis_url="redis://:123456@localhost:6379/0",
        key_prefix="chat:",
        ttl=None,
    )


prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "搜索互联网获取最新信息,调用search_web 用于新闻、天气、实时事件"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

llm = util.get_model()
tools = [search_web, todo_task]
agent = create_tool_calling_agent(llm, tools, prompt)
executor = AgentExecutor(
    agent=agent,
    tools=tools,
    handle_parsing_errors=True,
    max_iterations=3,
)

chain_with_history = RunnableWithMessageHistory(
    runnable=executor,
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)

config = {"configurable": {"session_id": "user-001"}}
ret = chain_with_history.invoke({"input": "创建一个7月13日10点关于放假的待办"}, config=config)
print(ret)
