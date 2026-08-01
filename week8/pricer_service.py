"""
Modal 定价服务（function 版）：把微调 LLM 部署为可远程调用的云函数。

什么是 Modal？
  用 Python 代码描述「镜像依赖、GPU、密钥、超时」，然后 modal deploy 把函数放到云端。
  本地 Agent 只需 .remote(...) 调用，不必自己买 GPU 机器或写 Dockerfile——这叫
  「Infrastructure as Code（用代码定义基础设施）」。

本文件角色：
  App 名 pricer-service，与 SpecialistAgent / pricer_service2 同一服务家族。
  用 @app.function 暴露 price(description)；每次冷启动可能重新加载模型
  （function 版没有 @modal.enter 的「只加载一次」生命周期，见 pricer_service2）。

量化 + PEFT 简释（读代码前先建立直觉）：
  - 4bit 量化（BitsAndBytes）：把权重量化到 4 位，显著省显存，T4 也能跑 3B 级模型
  - PEFT / LoRA（PeftModel）：不改动整个基座，只加载一小份微调适配器权重
  - generate 后解析 "Price is $" 后面的数字 → 返回 float 价格

教学链路：Week 8 本地多智能体 → SpecialistAgent → 本服务远程推理。
"""

import modal
from modal import Image

# Setup - define our infrastructure with code!

# App：Modal 上的应用命名空间；deploy 后可用名称找到它
app = modal.App("pricer-service")
# Image：云端容器里要 pip 安装的依赖（相当于精简版 Dockerfile）
image = Image.debian_slim().pip_install(
    "torch", "transformers", "bitsandbytes", "accelerate", "peft"
)

# This collects the secret from Modal.
# Depending on your Modal configuration, you may need to replace "huggingface-secret" with "hf-secret"
# Secret：把 HF token 等敏感信息存在 Modal 控制台，运行时注入环境，避免写进代码仓库
secrets = [modal.Secret.from_name("huggingface-secret")]

# Constants

GPU = "T4"
BASE_MODEL = "meta-llama/Llama-3.2-3B"
PROJECT_NAME = "price"
HF_USER = "ed-donner"  # your HF name here! Or use mine if you just want to reproduce my results.
RUN_NAME = "2025-11-28_18.47.07"
PROJECT_RUN_NAME = f"{PROJECT_NAME}-{RUN_NAME}"
REVISION = "b19c8bfea3b6ff62237fbb0a8da9779fc12cefbd"
FINETUNED_MODEL = f"{HF_USER}/{PROJECT_RUN_NAME}"


@app.function(image=image, secrets=secrets, gpu=GPU, timeout=1800)
def price(description: str) -> float:
    """
    远程定价：4bit Llama + LoRA 微调权重，根据描述生成并解析价格。

    装饰器参数含义（初学者）：
      - image：用上面定义的依赖镜像跑这个函数
      - secrets：注入 Hugging Face 凭证以便下载模型
      - gpu：申请一块 T4
      - timeout=1800：最长跑 30 分钟（冷启动加载模型可能较慢）

    参数:
        description: 商品描述
    返回:
        估计价格（float）；解析失败时 0
    """
    # 注意：这些 import 写在函数内部——Modal 会在「云端容器」里执行函数体，
    # 本地 laptop 不一定装了 torch；依赖装在 image 里即可。
    import re
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, set_seed
    from peft import PeftModel

    # 与训练数据一致的提示格式：问题 + 描述 + 「Price is $」前缀引导模型续写数字
    PREFIX = "Price is $"
    QUESTION = "What does this cost to the nearest dollar?"

    prompt = f"{QUESTION}\n\n{description}\n\n{PREFIX}"

    # Quant Config：4bit NF4 + double quant，在消费级 GPU 上装下 3B 模型
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
    )

    # Load model and tokenizer

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # 先加载量化基座，再挂上 LoRA 微调适配器（revision 钉死某一版权重，保证可复现）
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, quantization_config=quant_config, device_map="auto"
    )

    fine_tuned_model = PeftModel.from_pretrained(base_model, FINETUNED_MODEL, revision=REVISION)

    set_seed(42)
    inputs = tokenizer.encode(prompt, return_tensors="pt").to("cuda")
    # no_grad：推理不需要梯度，省显存；max_new_tokens=5 足够生成短价格
    with torch.no_grad():
        outputs = fine_tuned_model.generate(inputs, max_new_tokens=5)
    result = tokenizer.decode(outputs[0])
    # 从续写结果里切开 PREFIX，再正则提取第一个数字
    contents = result.split("Price is $")[1]
    contents = contents.replace(",", "")
    match = re.search(r"[-+]?\d*\.\d+|\d+", contents)
    return float(match.group()) if match else 0
