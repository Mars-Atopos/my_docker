# !/usr/bin/env python

import argparse
from dingtalk_stream import AckMessage
import dingtalk_stream
from alibabacloud_dingtalk.oauth2_1_0.client import Client as dingtalkoauth2_1_0Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dingtalk.oauth2_1_0 import models as dingtalkoauth_2__1__0_models
from alibabacloud_dingtalk.robot_1_0.client import Client as dingtalkrobot_1_0Client
from alibabacloud_dingtalk.robot_1_0 import models as dingtalkrobot__1__0_models
from alibabacloud_tea_util import models as util_models
import time
import config
_token_cache = {"token": None, "expire": 0}


def define_options():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--client_id', dest='client_id', required=False,default=config.client_id,
        help='app_key or suite_key from https://open-dev.digntalk.com'
    )
    parser.add_argument(
        '--client_secret', dest='client_secret', required=False,default=config.client_secret,
        help='app_secret or suite_secret from https://open-dev.digntalk.com'
    )
    parser.add_argument(
        '--robot_code', dest='robot_code', required=False,default=config.robot_code,
        help='robot_code from https://open-dev.dingtalk.com'
    )
    parser.add_argument(
        '--msg', dest='msg', default='python-getting-start say：hello',
        help='要发送的消息内容'
    )
    return parser.parse_args()


def get_token(options):
    """
    使用钉钉SDK获取access_token，带本地缓存，2小时有效，提前200秒刷新。
    :param options: 命令行参数对象，包含 client_id, client_secret
    :return: access_token字符串，获取失败返回None
    """
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expire"]:
        return _token_cache["token"]
    cfg = open_api_models.Config()
    cfg.protocol = 'https'
    cfg.region_id = 'central'
    client = dingtalkoauth2_1_0Client(cfg)
    get_access_token_request = dingtalkoauth_2__1__0_models.GetAccessTokenRequest(
        app_key=options.client_id,
        app_secret=options.client_secret
    )
    try:
        response = client.get_access_token(get_access_token_request)
        token = getattr(response.body, "access_token", None)
        expire_in = getattr(response.body, "expire_in", 7200)
        if token:
            _token_cache["token"] = token
            _token_cache["expire"] = now + expire_in - 200  # 提前200秒刷新
        return token
    except Exception:
        return None


def send_robot_private_message(access_token: str, options, user_ids: list):
    """
    使用钉钉SDK发送机器人私聊消息
    :param access_token: 已获取的 access_token
    :param options: 命令行参数对象
    :param user_ids: 用户ID列表
    :return: 发送结果或 None
    """
    import json
    robot_code = options.robot_code
    msg_key = 'sampleText'
    # 清理回复中的markdown代码块等特殊字符
    clean_msg = options.msg.replace('```', '').replace('```json', '').replace('```plaintext', '')
    msg_param = json.dumps({"content": clean_msg}, ensure_ascii=False)

    cfg = open_api_models.Config()
    cfg.protocol = 'https'
    cfg.region_id = 'central'
    client = dingtalkrobot_1_0Client(cfg)

    batch_send_otoheaders = dingtalkrobot__1__0_models.BatchSendOTOHeaders()
    batch_send_otoheaders.x_acs_dingtalk_access_token = access_token
    batch_send_otorequest = dingtalkrobot__1__0_models.BatchSendOTORequest(
        robot_code=robot_code,
        user_ids=user_ids,
        msg_key=msg_key,
        msg_param=msg_param
    )
    try:
        response = client.batch_send_otowith_options(
            batch_send_otorequest,
            batch_send_otoheaders,
            util_models.RuntimeOptions()
        )
        return response
    except Exception:
        return None


class EchoTextHandler(dingtalk_stream.ChatbotHandler):
    def __init__(self, options=None):
        super(dingtalk_stream.ChatbotHandler, self).__init__()
        self.options = options

    async def process(self, callback: dingtalk_stream.CallbackMessage):
        incoming_message = dingtalk_stream.ChatbotMessage.from_dict(callback.data)
        user_id = incoming_message.sender_staff_id
        access_token = get_token(self.options)
        if access_token:
            send_robot_private_message(access_token, self.options, [user_id])
        return AckMessage.STATUS_OK, 'OK'


def main():
    options = define_options()
    credential = dingtalk_stream.Credential(options.client_id, options.client_secret)
    client = dingtalk_stream.DingTalkStreamClient(credential)
    client.register_callback_handler(
        dingtalk_stream.chatbot.ChatbotMessage.TOPIC,
        EchoTextHandler(options)
    )
    client.start_forever()


if __name__ == '__main__':
    main()
