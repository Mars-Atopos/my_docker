#!/usr/bin/env python
'''
小白机器人 - 启动入口
功能：启动钉钉消息监听服务
'''

import dingtalk_stream
import config
from tools.processMsg import PrivateMessageHandler

def main():
    credential = dingtalk_stream.Credential(config.client_id, config.client_secret)
    client = dingtalk_stream.DingTalkStreamClient(credential)
    client.register_callback_handler(
        dingtalk_stream.chatbot.ChatbotMessage.TOPIC,
        PrivateMessageHandler()
    )
    client.start_forever()

if __name__ == '__main__':
    main()
