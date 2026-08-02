"""AI 掌握了使用 OpenAI 的 DALL·E 3 制作的地下城提取游戏场景插画。"""

import base64
from io import BytesIO

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image


# 环境初始化。
load_dotenv(override=True)

# 定义全局默认值。
MODEL = 'dall-e-2'

# 客户端实例化。
CLIENT = OpenAI()


# 函数定义。
def draw(prompt, size=(1024, 1024), client=CLIENT, model=MODEL, quality=None):
    """根据提示生成图像。"""
    # 生成图像。
    response = client.images.generate(
        model=model, prompt=prompt, n=1,
        size=f'{size[0]}x{size[1]}',
        response_format='b64_json')
    # 处理响应。
    return Image.open(BytesIO(base64.b64decode(response.data[0].b64_json)))
