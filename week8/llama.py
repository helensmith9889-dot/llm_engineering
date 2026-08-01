"""
在 Modal GPU 上运行基础 Llama 文本生成（尚未接 LoRA 微调）。

本文件是通往 Specialist 定价服务的中间练习：
  hello.py（无 GPU）→ 本文件（GPU + transformers）→ pricer_ephemeral / pricer_service
                                                      （4bit + PEFT 微调权重）

要点：
  - secrets：从 Modal 注入 Hugging Face token，才能拉 gated 模型
  - gpu="T4"：申请一块 T4；timeout 拉长以免下载模型超时
  - generate 只续写少量 new tokens，用于验证端到端通路
"""

import modal
from modal import Image

# Setup

app = modal.App("llama")
image = Image.debian_slim().pip_install("torch", "transformers", "accelerate")
# huggingface-secret 需事先在 Modal 控制台 / CLI 创建
secrets = [modal.Secret.from_name("huggingface-secret")]
GPU = "T4"
MODEL_NAME = "meta-llama/Llama-3.2-3B"


@app.function(image=image, secrets=secrets, gpu=GPU, timeout=1800)
def generate(prompt: str) -> str:
    """
    在远程 GPU 上加载 Llama-3.2-3B，对 prompt 生成最多 5 个新 token。

    参数:
        prompt: 输入提示文本
    返回:
        解码后的完整序列字符串（含原始 prompt + 续写）

    依赖均在函数内 import：保证只在装好库的容器镜像中执行。
    """
    from transformers import AutoTokenizer, AutoModelForCausalLM, set_seed

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # device_map="auto"：accelerate 自动把层放到可用 GPU
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, device_map="auto")

    set_seed(42)
    inputs = tokenizer.encode(prompt, return_tensors="pt").to("cuda")
    outputs = model.generate(inputs, max_new_tokens=5)
    return tokenizer.decode(outputs[0])
