"""中文注释版：逻辑与标识符保持不变，仅增加/翻译注释便于小白阅读。"""
# 进口

import os
from dotenv import load_dotenv
# 从 scraper 导入 fetch_website_contents
from IPython.display import Markdown, display
from openai import OpenAI

# 如果运行此单元时出现错误，请转到故障排除笔记本！

# 在名为 .env 的文件中加载环境变量

load_dotenv(override=True)
api_key = os.getenv('OPENAI_API_KEY')

# 检查钥匙

if not api_key:
    print("No API key was found - please head over to the troubleshooting notebook in this folder to identify & fix!")
elif not api_key.startswith("sk-proj-"):
    print("An API key was found, but it doesn't start sk-proj-; please check you're using the right key - see troubleshooting notebook")
elif api_key.strip() != api_key:
    print("An API key was found, but it looks like it might have space or tab characters at the start or end - please remove them - see troubleshooting notebook")
else:
    print("API key found and looks good so far!")

# 让您预览一下——使用这些消息调用 OpenAI 就是这么简单。如有任何问题，请参阅故障排除笔记本。

def solve_problem(problem_text) :

    openai = OpenAI()


# 定义我们的系统提示符 - 您可以稍后进行实验，将最后一句更改为“用西班牙语以 markdown 方式回复”。

    system_prompt = """
    You are a top-level competitive programmer.

    The following is a coding problem extracted via OCR. It may contain noise or minor errors.

    Your task:
    1. Understand the intended problem correctly
    2. Fix any OCR mistakes mentally
    3. Provide:
    - Clean problem understanding (1-2 lines)
    - Optimal approach
    - Time & space complexity
    - Clean C++ solution
    """

    # 定义我们的用户提示

    user_prompt_prefix = """
    This is the Problem :
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_prefix + problem_text}
    ]

    response = openai.chat.completions.create(model="gpt-5-nano", messages=messages)
    return response.choices[0].message.content

   

   

