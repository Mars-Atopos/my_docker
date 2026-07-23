#!/usr/bin/env python
'''
钉钉消息解析器
功能：接收钉钉消息，调用Agent处理，发送回复
'''

from dingtalk_stream import AckMessage
import dingtalk_stream
from SDK.send_robot_private_message import get_token, send_robot_private_message
from tools.memory_store import MemoryStore
import config

# 会话重置关键词
RESET_KEYWORDS = ["新对话", "重新开始", "清除记忆", "重置"]

memory = MemoryStore()

def _is_reset_command(text):
    """检测是否为会话重置指令"""
    text = text.strip()
    return any(kw in text for kw in RESET_KEYWORDS)

class PrivateMessageHandler(dingtalk_stream.ChatbotHandler):
    """私聊消息处理器"""

    async def process(self, callback: dingtalk_stream.CallbackMessage):
        incoming_message = dingtalk_stream.ChatbotMessage.from_dict(callback.data)

        user_id = incoming_message.sender_staff_id
        message_text = incoming_message.text.content if incoming_message.text else ""

        # 检测会话重置指令
        if _is_reset_command(message_text):
            memory.reset_session(user_id)
            reply = "好的，已为你开启新对话，之前的聊天记录已清空。不过我还记得你之前告诉我的事情哦~"
        else:
            try:
                from tools.graph_agent import chat
                reply = chat(user_id, message_text)
            except Exception as e:
                import traceback
                traceback.print_exc()
                reply = f"抱歉，处理消息时出现错误: {e}"

        # 发送回复
        try:
            class Options:
                client_id = config.client_id
                client_secret = config.client_secret
                robot_code = config.robot_code
                msg = reply

            access_token = get_token(Options())
            if access_token:
                send_robot_private_message(access_token, Options(), [user_id])
        except Exception:
            pass

        return AckMessage.STATUS_OK, 'OK'
