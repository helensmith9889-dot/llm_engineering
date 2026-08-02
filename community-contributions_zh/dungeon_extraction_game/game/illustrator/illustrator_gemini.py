"""AI 掌握了使用 Google Gemini 绘制地牢提取游戏场景的插画。"""

from io import BytesIO

from dotenv import load_dotenv
from google import genai  # New Google's SDK 'genai' to replace 'generativeai'.
from PIL import Image


# 环境初始化。
load_dotenv(override=True)

# 定义全局变量。
MODEL = 'gemini-2.5-flash-image-preview'

# 客户端实例化。
CLIENT = genai.Client()


# 函数定义。
def draw(prompt, size=(1024, 1024), client=CLIENT, model=MODEL):
    """根据提示生成图像。"""
    # 生成图像。
    response = client.models.generate_content(
        model=model, contents=[prompt])
    # 处理响应。
    for part in response.candidates[0].content.parts:
        if part.text is not None:
            print(part.text)
        elif part.inline_data is not None:
            image_data = part.inline_data.data
    # 打开生成的图像。
    generated_image = Image.open(BytesIO(image_data))
    # 将图像大小调整为指定尺寸。
    resized_image = generated_image.resize(size)
    return resized_image
