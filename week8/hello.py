"""
Modal「Hello World」入门：用代码定义云端函数，验证 Modal 部署是否畅通。

在 Week 8 多智能体扫货系统中，真正的定价微调模型跑在 Modal GPU 上
（见 pricer_service*.py）。本文件是部署练习的第一步：

  - 声明 App / Image（Debian slim + pip install requests）
  - 用 @app.function 把普通 Python 函数变成云端可调用函数
  - 函数内请求 ipinfo，返回「Hello from 城市…」，证明代码在远程机器执行

教学关键词：Serverless、Infrastructure as Code（用 Python 描述云基础设施）、region。
"""

import modal
from modal import Image

# Setup：创建名为 hello 的 Modal App，以及带 requests 的运行镜像

app = modal.App("hello")
image = Image.debian_slim().pip_install("requests")

# Hello!


@app.function(image=image)
def hello() -> str:
    """
    在 Modal 默认区域运行：查询本机公网 IP 的地理位置并返回问候语。

    注意：import requests 写在函数内部——因为依赖装在远程 image 里，
    本地可能没有该包；Modal 会在容器内执行此函数体。
    """
    import requests

    response = requests.get("https://ipinfo.io/json")
    data = response.json()
    city, region, country = data["city"], data["region"], data["country"]
    return f"Hello from {city}, {region}, {country}!!"


# New - added thanks to student Tue H.!


@app.function(image=image, region="eu")
def hello_europe() -> str:
    """
    与 hello() 相同逻辑，但强制调度到欧洲 region，便于对比 IP 归属地差异。
    """
    import requests

    response = requests.get("https://ipinfo.io/json")
    data = response.json()
    city, region, country = data["city"], data["region"], data["country"]
    return f"Hello from {city}, {region}, {country}!!"
