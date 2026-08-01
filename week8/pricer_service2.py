"""
Modal 定价服务（Class 版）：SpecialistAgent 实际对接的 Pricer 远程类。

相对 pricer_service.py（纯 function）的升级点——为什么生产更常用 Class：
  1. @app.cls：把「加载模型」放在 @modal.enter 的 setup()，容器启动时执行一次
  2. @modal.method price()：后续请求复用已加载的 tokenizer / base / LoRA，延迟更低
     （function 版每次冷启动都可能重新 from_pretrained，浪费时间与带宽）
  3. Volume 缓存 Hugging Face 权重（HF_HUB_CACHE），减少重复下载
  4. min_containers：0 表示闲置后缩容（省钱）；改为 1 可常驻保暖（更贵但更低延迟）

冷启动 vs 热启动（初学者）：
  - 冷：没有现成容器 → 拉镜像、挂卷、跑 setup() 加载模型 → 再推理（慢）
  - 热：容器还在，模型已在 GPU 内存 → 直接 price()（快）

多智能体链路：
  EnsembleAgent → SpecialistAgent → modal.Cls.from_name("pricer-service", "Pricer")
                                 → 本文件 Pricer.price.remote(description)
"""

import modal
from modal import Volume, Image
# Setup - define our infrastructure with code!

app = modal.App("pricer-service")
image = Image.debian_slim().pip_install(
    "huggingface", "torch", "transformers", "bitsandbytes", "accelerate", "peft"
)

# This collects the secret from Modal.
# Depending on your Modal configuration, you may need to replace "huggingface-secret" with "hf-secret"
secrets = [modal.Secret.from_name("huggingface-secret")]

GPU = "T4"
BASE_MODEL = "meta-llama/Llama-3.2-3B"
PROJECT_NAME = "price"
HF_USER = "ed-donner"  # your HF name here! Or use mine if you just want to reproduce my results.
RUN_NAME = "2025-11-28_18.47.07"
PROJECT_RUN_NAME = f"{PROJECT_NAME}-{RUN_NAME}"
REVISION = "b19c8bfea3b6ff62237fbb0a8da9779fc12cefbd"
FINETUNED_MODEL = f"{HF_USER}/{PROJECT_RUN_NAME}"
CACHE_DIR = "/cache"

# Change this to 1 if you want Modal to be always running, otherwise it will go cold after 2 mins
# 0 = 省钱（闲置缩到 0）；1 = 至少保持 1 个容器热着，减少用户等待
MIN_CONTAINERS = 0

# 与 items.py / 训练数据一致的提示词前缀（字面量勿改）
PREFIX = "Price is $"
QUESTION = "What does this cost to the nearest dollar?"

# 持久卷：跨容器调用缓存 HF 模型文件，避免每次冷启动都从网上下完整权重
hf_cache_volume = Volume.from_name("hf-hub-cache", create_if_missing=True)


@app.cls(
    image=image.env({"HF_HUB_CACHE": CACHE_DIR}),
    secrets=secrets,
    gpu=GPU,
    timeout=1800,
    min_containers=MIN_CONTAINERS,
    volumes={CACHE_DIR: hf_cache_volume},
)
class Pricer:
    """
    Modal 远程定价类：setup 加载一次模型，price 方法可被反复 remote 调用。

    本地侧典型用法（示意）：
      Pricer = modal.Cls.from_name("pricer-service", "Pricer")
      price = Pricer().price.remote("...商品描述...")
    """

    @modal.enter()
    def setup(self):
        """
        容器进入时回调：配置 4bit 量化并加载基座 + LoRA 到 self.*。

        @modal.enter 类似「容器生命周期的 __init__ 之后」：
        只在冷启动（或新容器）时付出加载成本，后续 method 调用直接推理。
        模型句柄挂在 self 上，才能在多次 price() 之间复用。
        """
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
        from peft import PeftModel

        # Quant Config：与 function 版相同的 4bit 设置
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
        )

        # Load model and tokenizer — 结果存 self，供 price() 复用
        self.tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = "right"
        self.base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL, quantization_config=quant_config, device_map="auto"
        )
        self.fine_tuned_model = PeftModel.from_pretrained(
            self.base_model, FINETUNED_MODEL, revision=REVISION
        )

    @modal.method()
    def price(self, description: str) -> float:
        """
        对描述做生成式定价并解析首个数字。

        @modal.method：把实例方法暴露成可 .remote() / .local() 调用的端点。
        这里不再加载模型，只做 tokenize → generate → 解析。

        参数:
            description: 商品描述（Ensemble 侧通常已经过 Preprocessor）
        返回:
            估计价格；解析失败返回 0
        """
        import re
        import torch
        from transformers import set_seed

        set_seed(42)
        prompt = f"{QUESTION}\n\n{description}\n\n{PREFIX}"

        inputs = self.tokenizer.encode(prompt, return_tensors="pt").to("cuda")
        with torch.no_grad():
            outputs = self.fine_tuned_model.generate(inputs, max_new_tokens=5)
        result = self.tokenizer.decode(outputs[0])
        contents = result.split("Price is $")[1]
        contents = contents.replace(",", "")
        match = re.search(r"[-+]?\d*\.\d+|\d+", contents)
        return float(match.group()) if match else 0
