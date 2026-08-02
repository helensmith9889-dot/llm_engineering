"""AI 使用 xAI 的 Grok 掌握了地下城提取游戏场景插画。"""

import base64
import os
from io import BytesIO

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image
from xai_sdk import Client


# 环境初始化。
load_dotenv(override=True)

# 定义全局默认值。
MODEL = 'grok-2-image'
QUALITY = None

# 客户端实例化。
XAI_API_KEY = os.getenv('XAI_API_KEY')
CLIENT = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")


# 函数定义。
def draw(prompt, size=(1024, 1024), client=CLIENT, model=MODEL, quality=QUALITY):
    """根据提示生成图像。"""
    # 生成图像。
    response = client.images.generate(
        model=model, prompt=prompt, n=1,
        response_format='b64_json')
    # 处理响应。
    return Image.open(BytesIO(base64.b64decode(response.data[0].b64_json)))


# xAI SDK版本：
CLIENT_X = Client(api_key=XAI_API_KEY)


def draw_x(prompt, size=(1024, 1024), client=CLIENT_X, model=MODEL, quality=QUALITY):
    """根据提示生成图像。"""
    # 生成图像。
    response = client.image.sample(
        model=model, prompt=prompt,
        image_format='base64')
    # 处理响应。
    return Image.open(BytesIO(response.image))
