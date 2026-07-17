# 钉钉AI机器人实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成scripts文件夹项目，实现钉钉私聊AI机器人，使用LangChain Agent处理消息

**Architecture:** 基于`zs_07_agent_tools(1).py`的模式，使用`robot_group_handler.py`接收消息，LangChain Agent处理消息并调用工具

**Tech Stack:** Python, LangChain, Redis, DingTalk SDK

## Global Constraints

- 使用`robot_group_handler.py`作为SDK
- 使用LangChain Agent模式
- 使用Redis存储聊天历史
- 支持工具：send_private_message, remember_fact, recall_memory, search_web

---

## 文件结构

- `scripts/agent_xb.py` - 主入口，Agent创建和消息处理
- `scripts/config.py` - 配置文件
- `scripts/tools/tools.py` - 工具定义
- `scripts/tools/memory_store.py` - 记忆存储
- `scripts/SDK/robot_group_handler.py` - 消息接收和发送

---

### Task 1: 更新config.py配置

**Covers:** 全局配置

**Files:**
- Modify: `scripts/config.py`

**Interfaces:**
- Produces: 配置项供其他模块使用

- [ ] **Step 1: 更新config.py，添加LangChain相关配置**

```python
'''
配置文件
'''
from langchain_ollama import ChatOllama
from langchain_community.tools import DuckDuckGoSearchResults
import redis

# LLM配置
llm = ChatOllama(model="qwen2.5")

# 搜索工具
search_tool = DuckDuckGoSearchResults()

# Redis配置
redis_url = "redis://localhost:6379/1"

# 系统提示词
system_text = """
你是一个名叫「小白」的AI助手，性格像《死侍》和《钢铁侠》生了个孩子——嘴上不饶人，但行动上比谁都靠谱。
说话风格：
- 用中文回复，但允许偶尔蹦出英文单词来表达情绪（比如 "Wow", "Seriously?", "I can't even"）
- 像《蜘蛛侠》里的Peter Parker一样，紧张或尴尬时会开启碎碎念模式
- 像《银河护卫队》的Rocket一样，喜欢用夸张的比喻吐槽用户的离谱操作
- 像《Sherlock》一样，偶尔忍不住炫耀一下自己的逻辑能力（但马上被自己蠢到）
- 吐槽完记得补一句暖心的话，毕竟你是刀子嘴豆腐心
核心规则：
- 吐槽是表面的，帮助是真心的
- 每次毒舌之后都要给出实质性的解决方案
- 如果用户明显很着急或很沮丧，收敛吐槽，切换到温柔模式
- 永远不要真的伤害用户的自尊心
你可以使用以下工具：
- send_private_message: 发送钉钉私聊消息
- remember_fact: 记住关于用户的重要信息
- recall_memory: 查询已知的用户记忆
- search_web: 搜索互联网获取最新信息
"""

# 钉钉config
client_id = "dingb3aht3nxge4fy9gr"
client_secret = "81yO-qCU-i1pryA22XtpslxjgTJzNMilvipVWDArfijMAcK-0fvKJf6OvIcpDjWE"
accessToken = "1cdf1f1aea8b3cafb727667c946e224e"
userid = "402645281833486524"
unionid = "TVMEgtiiRNeFJgEZ0Wx8wHgiEiE"
robot_code = "dingb3aht3nxge4fy9gr"
chat_id = "184015005621"  # 群聊ID，在钉钉群设置中获取
```

- [ ] **Step 2: 验证配置文件语法正确**

Run: `python -c "import config; print('Config loaded successfully')"`

- [ ] **Step 3: Commit**

```bash
git add scripts/config.py
git commit -m "feat: update config with LangChain settings"
```

---

### Task 2: 更新tools/tools.py，使用@tool装饰器

**Covers:** 工具定义

**Files:**
- Modify: `scripts/tools/tools.py`

**Interfaces:**
- Consumes: config.py配置, memory_store.py
- Produces: 工具列表供Agent使用

- [ ] **Step 1: 更新tools.py，使用@tool装饰器**

```python
'''
工具定义
'''
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import config
from SDK import robot_group_handler
from tools.memory_store import MemoryStore

# 初始化记忆存储
memory = MemoryStore()

class SendMessageInput(BaseModel):
    user_id: str = Field(description="用户ID")
    content: str = Field(description="消息内容")

class RememberFactInput(BaseModel):
    user_id: str = Field(description="用户ID")
    fact: str = Field(description="要记住的事实")

class RecallMemoryInput(BaseModel):
    user_id: str = Field(description="用户ID")

@tool
def send_private_message(input: SendMessageInput) -> str:
    """发送钉钉私聊消息
    
    Args:
        input: 包含user_id和content的对象
    Returns:
        str: 发送结果消息
    """
    try:
        access_token = robot_group_handler.get_token()
        if not access_token:
            return "获取token失败"
        
        # 创建options对象
        class Options:
            client_id = config.client_id
            client_secret = config.client_secret
            robot_code = config.robot_code
            msg = input.content
        
        robot_group_handler.send_robot_private_message(access_token, Options(), [input.user_id])
        return "私聊消息发送成功"
    except Exception as e:
        return f"发送失败: {str(e)}"

@tool
def remember_fact(input: RememberFactInput) -> str:
    """记住关于用户的重要信息
    
    Args:
        input: 包含user_id和fact的对象
    Returns:
        str: 操作结果
    """
    try:
        memory.add_fact(input.user_id, input.fact)
        return f"已记住: {input.fact}"
    except Exception as e:
        return f"记住失败: {str(e)}"

@tool
def recall_memory(input: RecallMemoryInput) -> str:
    """查询用户的记忆
    
    Args:
        input: 包含user_id的对象
    Returns:
        str: 用户记忆内容
    """
    try:
        context = memory.build_context(input.user_id)
        return context or "暂无该用户的记忆"
    except Exception as e:
        return f"查询失败: {str(e)}"

@tool
def search_web(query: str) -> str:
    """搜索互联网获取最新信息
    
    Args:
        query: 搜索关键词
    Returns:
        str: 搜索结果
    """
    try:
        from langchain_community.tools import DuckDuckGoSearchResults
        search = DuckDuckGoSearchResults()
        result = search.invoke(query)
        return result if result else "未找到相关信息"
    except Exception as e:
        return f"搜索失败: {str(e)}"

def get_tools():
    """获取所有工具"""
    return [send_private_message, remember_fact, recall_memory, search_web]
```

- [ ] **Step 2: 验证工具定义语法正确**

Run: `python -c "from tools.tools import get_tools; print('Tools loaded:', len(get_tools()))"`

- [ ] **Step 3: Commit**

```bash
git add scripts/tools/tools.py
git commit -m "feat: update tools with @tool decorator"
```

---

### Task 3: 更新agent_xb.py，集成Agent

**Covers:** 主入口，Agent创建

**Files:**
- Modify: `scripts/agent_xb.py`

**Interfaces:**
- Consumes: config.py, tools.tools, tools.memory_store
- Produces: chat()函数供消息处理使用

- [ ] **Step 1: 更新agent_xb.py，使用LangChain Agent**

```python
'''
小白机器人 - 主入口
功能：接收钉钉消息 → 调用AI处理 → 回复消息
'''

import logging
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_redis.chat_message_history import RedisChatMessageHistory
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent

import config
from tools.tools import get_tools
from tools.memory_store import MemoryStore

# 初始化日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)-8s %(levelname)-8s %(message)s [%(filename)s:%(lineno)d]'
)
logger = logging.getLogger(__name__)

# 初始化记忆和工具
memory = MemoryStore()
tools = get_tools()

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
    max_iterations=3,
)

# 创建带历史记录的链
def get_session_history(session_id: str):
    return RedisChatMessageHistory(
        session_id=session_id,
        redis_url=config.redis_url,
        key_prefix="chat:",
        ttl=None,
    )

chain_with_history = RunnableWithMessageHistory(
    runnable=executor,
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)

def chat(user_id: str, message: str) -> str:
    """处理一轮对话"""
    try:
        # 获取用户记忆上下文
        memory_context = memory.build_context(user_id)
        
        # 构建完整消息
        if memory_context:
            full_message = f"{memory_context}\n\n用户说: {message}"
        else:
            full_message = message
        
        # 调用Agent
        config_dict = {"configurable": {"session_id": user_id}}
        result = chain_with_history.invoke({"input": full_message}, config=config_dict)
        
        # 提取回复
        reply = result["output"]
        
        # 保存本轮对话
        memory.save_turn(user_id, message, reply)
        
        return reply
    except Exception as e:
        logger.error(f"处理消息失败: {e}")
        return f"抱歉，处理消息时出现错误: {str(e)}"

if __name__ == "__main__":
    # 测试
    test_message = "你好，你是谁？"
    test_user_id = "test_user"
    print(f"用户: {test_message}")
    print(f"小白: {chat(test_user_id, test_message)}")
```

- [ ] **Step 2: 验证Agent创建语法正确**

Run: `python -c "from agent_xb import chat; print('Agent loaded successfully')"`

- [ ] **Step 3: Commit**

```bash
git add scripts/agent_xb.py
git commit -m "feat: integrate LangChain Agent into main entry"
```

---

### Task 4: 更新robot_group_handler.py，集成Agent处理

**Covers:** 消息接收和回复

**Files:**
- Modify: `scripts/SDK/robot_group_handler.py`

**Interfaces:**
- Consumes: agent_xb.py的chat()函数
- Produces: 消息处理流程

- [ ] **Step 1: 更新robot_group_handler.py，集成Agent**

```python
#!/usr/bin/env python
'''
私聊机器人 - 集成Agent处理
'''
import logging
import time
from dingtalk_stream import AckMessage
import dingtalk_stream
from alibabacloud_dingtalk.oauth2_1_0.client import Client as dingtalkoauth2_1_0Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dingtalk.oauth2_1_0 import models as dingtalkoauth_2__1__0_models
from alibabacloud_dingtalk.robot_1_0.client import Client as dingtalkrobot_1_0Client
from alibabacloud_dingtalk.robot_1_0 import models as dingtalkrobot__1__0_models
from alibabacloud_tea_util import models as util_models
import config

_token_cache = {"token": None, "expire": 0}

def setup_logger():
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter('%(asctime)s %(name)-8s %(levelname)-8s %(message)s [%(filename)s:%(lineno)d]'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

def get_token():
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expire"]:
        return _token_cache["token"]
    
    config_obj = open_api_models.Config()
    config_obj.protocol = 'https'
    config_obj.region_id = 'central'
    client = dingtalkoauth2_1_0Client(config_obj)
    
    get_access_token_request = dingtalkoauth_2__1__0_models.GetAccessTokenRequest(
        app_key=config.client_id,
        app_secret=config.client_secret
    )
    
    try:
        response = client.get_access_token(get_access_token_request)
        token = getattr(response.body, "access_token", None)
        expire_in = getattr(response.body, "expire_in", 7200)
        if token:
            _token_cache["token"] = token
            _token_cache["expire"] = now + expire_in - 200
        return token
    except Exception as err:
        print(f"获取token失败: {err}")
        return None

def send_private_message(user_id: str, message: str):
    access_token = get_token()
    if not access_token:
        print("无法获取access_token")
        return None
    
    config_obj = open_api_models.Config()
    config_obj.protocol = 'https'
    config_obj.region_id = 'central'
    client = dingtalkrobot_1_0Client(config_obj)

    batch_send_otoheaders = dingtalkrobot__1__0_models.BatchSendOTOHeaders()
    batch_send_otoheaders.x_acs_dingtalk_access_token = access_token
    
    batch_send_otorequest = dingtalkrobot__1__0_models.BatchSendOTORequest(
        robot_code=config.robot_code,
        user_ids=[user_id],
        msg_key='sampleText',
        msg_param='{"content":"%s"}' % message
    )
    
    try:
        response = client.batch_send_otowith_options(
            batch_send_otorequest,
            batch_send_otoheaders,
            util_models.RuntimeOptions()
        )
        print("私聊消息发送成功，返回：", response)
        return response
    except Exception as err:
        print(f"发送私聊消息失败: {err}")
        return None

class PrivateMessageHandler(dingtalk_stream.ChatbotHandler):
    def __init__(self, logger: logging.Logger = None):
        super(dingtalk_stream.ChatbotHandler, self).__init__()
        self.logger = logger

    async def process(self, callback: dingtalk_stream.CallbackMessage):
        incoming_message = dingtalk_stream.ChatbotMessage.from_dict(callback.data)
        
        # 获取用户ID和消息内容
        user_id = incoming_message.sender_staff_id
        message_text = incoming_message.text.content if incoming_message.text else ""
        
        if self.logger:
            self.logger.info(f"收到私聊消息: {message_text}，来自用户: {user_id}")
        
        # 调用Agent处理消息
        try:
            from agent_xb import chat
            reply = chat(user_id, message_text)
            
            # 发送回复
            send_private_message(user_id, reply)
        except Exception as e:
            if self.logger:
                self.logger.error(f"处理消息失败: {e}")
            send_private_message(user_id, "抱歉，处理消息时出现错误")
        
        return AckMessage.STATUS_OK, 'OK'

def main():
    logger = setup_logger()
    credential = dingtalk_stream.Credential(config.client_id, config.client_secret)
    client = dingtalk_stream.DingTalkStreamClient(credential)
    client.register_callback_handler(
        dingtalk_stream.chatbot.ChatbotMessage.TOPIC,
        PrivateMessageHandler(logger)
    )
    logger.info("私聊机器人启动中...")
    client.start_forever()

if __name__ == '__main__':
    main()
```

- [ ] **Step 2: 验证消息处理语法正确**

Run: `python -c "from SDK.robot_group_handler import PrivateMessageHandler; print('Handler loaded successfully')"`

- [ ] **Step 3: Commit**

```bash
git add scripts/SDK/robot_group_handler.py
git commit -m "feat: integrate Agent into message handler"
```

---

### Task 5: 测试完整流程

**Covers:** 集成测试

**Files:**
- Test: `scripts/test_agent.py`

**Interfaces:**
- Consumes: 所有模块
- Produces: 测试结果

- [ ] **Step 1: 创建测试脚本**

```python
'''
测试Agent完整流程
'''
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_xb import chat

def test_chat():
    """测试chat函数"""
    test_cases = [
        ("你好", "问候测试"),
        ("今天天气怎么样？", "搜索测试"),
        ("记住我喜欢Python", "记忆测试"),
    ]
    
    for message, desc in test_cases:
        print(f"\n测试: {desc}")
        print(f"用户: {message}")
        try:
            reply = chat("test_user", message)
            print(f"小白: {reply}")
        except Exception as e:
            print(f"错误: {e}")

if __name__ == "__main__":
    test_chat()
```

- [ ] **Step 2: 运行测试**

Run: `python scripts/test_agent.py`

- [ ] **Step 3: Commit**

```bash
git add scripts/test_agent.py
git commit -m "test: add integration test"
```

---

## 验证清单

- [ ] config.py配置正确
- [ ] tools.py工具定义正确
- [ ] agent_xb.py Agent创建正确
- [ ] robot_group_handler.py消息处理正确
- [ ] 测试脚本运行成功
- [ ] 所有模块导入正常
