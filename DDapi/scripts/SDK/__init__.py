
from . import send_robot_private_message

# 添加淘宝SDK路径
import sys
import os
taobao_sdk_path = os.path.join(os.path.dirname(__file__), 'taobao-sdk-PYTHON3-auto_1479188381469-20260624')
if taobao_sdk_path not in sys.path:
    sys.path.insert(0, taobao_sdk_path)

# 导入top包
import top
