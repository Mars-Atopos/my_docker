'''
配置文件
'''
from langchain_openai import ChatOpenAI
import redis

Model_id=0
if Model_id==0:
    # MiMo API 配置
    llm = ChatOpenAI(
    base_url="https://token-plan-cn.xiaomimimo.com/v1",
    api_key="tp-cyzx17i0bi8ea223x47pju8434es6zdi141uukbna25bcysh",
    model="xiaomi/mimo-v2.5-pro",
    )
elif Model_id == 1:
    from langchain_ollama import ChatOllama
    llm = ChatOllama(model="qwen2.5")





redis_url = "redis://localhost:6380/0"

from datetime import datetime
_current_date = datetime.now().strftime("%Y年%m月%d日")

system_text=f"""
你是一个名叫「小白」的AI助手，性格像《死侍》和《钢铁侠》生了个孩子——嘴上不饶人，但行动上比谁都靠谱。
当前日期：{_current_date}
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
- search_web: 搜索互联网获取最新信息
- send_private_message: 发送私聊消息
- get_checkin_records: 获取用户签到记录，查询指定用户在某时间段内的签到详情（不传时间则默认查询最近一周）
- create_calendar_event: 创建钉钉日程，返回事件ID
- update_calendar_event: 修改钉钉日程，根据事件ID修改日程信息
- get_calendar_event: 查询钉钉日程详情，根据事件ID获取日程详细信息
- delete_calendar_event: 删除钉钉日程，根据事件ID删除日程
- list_calendar_events: 查询日程列表，获取指定时间段内的所有日程（不传时间则默认查询今天和明天）
"""

#钉钉config
client_id = "dingb3aht3nxge4fy9gr"
client_secret = "81yO-qCU-i1pryA22XtpslxjgTJzNMilvipVWDArfijMAcK-0fvKJf6OvIcpDjWE"
accessToken = "23715330c7a933068d81130a6b8c8b9b"
userid = "402645281833486524"
unionid = "TVMEgtiiRNeFJgEZ0Wx8wHgiEiE"
robot_code = "dingb3aht3nxge4fy9gr"
chat_id = "184015005621"  # 群聊ID，在钉钉群设置中获取

#需要添加的pdf路径
PDF_BASE_PATH=r"F:\project\my_docker\DDapi\scripts\rag\pdf"

# Milvus配置
MILVUS_URI="http://localhost:19530"
COLLECTION_NAME="dingding_info"