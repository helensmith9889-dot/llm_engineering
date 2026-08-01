"""
临时（Ephemeral）Modal 定价函数：每次调用都在 GPU 上重新加载微调模型。

与 pricer_service / pricer_service2 的关系：
  - 本文件：@app.function —— 无状态；冷启动要重新下模型，适合实验
  - pricer_service.py：同为 function 形态的服务版
  - pricer_service2.py：@app.cls + @modal.enter —— 容器保活时模型只加载一次，
    供 SpecialistAgent 通过 modal.Cls.from_name 远程调用

技术栈：Llama-3.2-3B 基座 + BitsAndBytes 4bit 量化 + PEFT/LoRA 微调适配器。
这是 Ensemble 里 Specialist 路线的云端实现雏形。
"""

import modal
from modal import Image

# Setup

app = modal.App("pricer")
image = Image.debian_slim().pip_install(
    "torch", "transformers", "bitsandbytes", "accelerate", "peft"
)
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
    在 Modal GPU 上对商品描述做一次微调模型推理，返回估计美元价格。

    流程：拼 QUESTION/PREFIX prompt → 4bit 加载基座 → 挂 LoRA → generate → 解析数字。

    参数:
        description: 商品描述文本
    返回:
        解析出的浮点价格；解析失败则为 0
    """
    import re
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, set_seed
    from peft import PeftModel

    PREFIX = "Price is $"
    QUESTION = "What does this cost to the nearest dollar?"

    prompt = f"{QUESTION}\n\n{description}\n\n{PREFIX}"

    # Quant Config：4bit NF4 量化，显著降低显存，T4 即可跑 3B+LoRA
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

    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, quantization_config=quant_config, device_map="auto"
    )

    # 把 Hugging Face 上的 LoRA 适配器叠到基座上（指定 revision 保证可复现）
    fine_tuned_model = PeftModel.from_pretrained(base_model, FINETUNED_MODEL, revision=REVISION)

    set_seed(42)
    inputs = tokenizer.encode(prompt, return_tensors="pt").to("cuda")
    with torch.no_grad():
        outputs = fine_tuned_model.generate(inputs, max_new_tokens=5)
    result = tokenizer.decode(outputs[0])
    # 模型应续写在 "Price is $" 之后；取后半段再抠数字
    contents = result.split("Price is $")[1]
    contents = contents.replace(",", "")
    match = re.search(r"[-+]?\d*\.\d+|\d+", contents)
    return float(match.group()) if match else 0
