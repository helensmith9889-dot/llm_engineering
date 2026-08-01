"""
批量 API 调用模块：为「价格预测」数据准备服务的产品摘要生成。

在微调（fine-tuning）一条 LLM 定价模型之前，我们通常需要把杂乱的商品原文
整理成简洁、统一的摘要。本模块用 Groq 的 Batch API，把上千条商品描述
打包成 JSONL 文件，异步提交给模型处理——比一条条实时调用更便宜、更稳。

与 LLM 训练的关系：
- 这里产出的 summary 会作为后续训练样本的「输入文本」；
- 批量（batch）处理是大规模数据管道的常见模式，和训练时的 mini-batch 概念类似，
  但目的是「异步完成 API 任务」，不是「梯度更新」。
"""

import os
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path
import json
import pickle
from tqdm.notebook import tqdm

# 从 .env 加载 API Key，override=True 表示环境变量优先被覆盖
load_dotenv(override=True)
groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# 用于生成产品摘要的模型名（字符串字面量保持不变）
MODEL = "openai/gpt-oss-20b"
# 本地存放待上传 JSONL 的文件夹名
BATCHES_FOLDER = "batches"
# 下载批量结果的文件夹名
OUTPUT_FOLDER = "output"
# 用 pickle 持久化 Batch 对象列表的状态文件路径
state = Path("batches.pkl")

# 系统提示：约束模型只输出固定字段的简洁产品描述
SYSTEM_PROMPT = """Create a concise description of a product. Respond only in this format. Do not include part numbers.
Title: Rewritten short precise title
Category: eg Electronics
Brand: Brand name
Description: 1 sentence description
Details: 1 sentence on features"""


class Batch:
    """
    表示一次「批量摘要任务」的切片（slice）。

    思路：把全部商品列表按 BATCH_SIZE 切开，每片对应一个 JSONL 文件 +
    一次 Groq Batch 作业。类属性 `batches` 保存所有切片，便于统一提交/拉取。
    """

    # 每个 JSONL 文件包含多少条商品（1000 是常见批量大小）
    BATCH_SIZE = 1_000

    # 类级别列表：存放所有 Batch 实例，便于 create/run/fetch/save
    batches = []

    def __init__(self, items, start, end, lite):
        """
        初始化一个批次切片。

        参数:
            items: 完整商品列表（共享引用，摘要写回同一列表）
            start / end: 本批次在 items 中的半开区间 [start, end)
            lite: True 用 lite/ 目录，False 用 full/——区分小样与全量实验
        """
        self.items = items
        self.start = start
        self.end = end
        # 文件名用起止索引标识，方便追踪
        self.filename = f"{start}_{end}.jsonl"
        # 上传后 Groq 返回的文件 ID
        self.file_id = None
        # 提交后返回的 batch 作业 ID
        self.batch_id = None
        # 作业完成后输出文件的 ID
        self.output_file_id = None
        # 本批次是否已把摘要写回 items
        self.done = False
        # lite / full 决定本地目录树，避免小样与全量结果混在一起
        folder = Path("lite") if lite else Path("full")
        self.batches = folder / BATCHES_FOLDER
        self.output = folder / OUTPUT_FOLDER
        # parents=True：中间目录不存在也创建；exist_ok=True：已存在不报错
        self.batches.mkdir(parents=True, exist_ok=True)
        self.output.mkdir(parents=True, exist_ok=True)

    def make_jsonl(self, item):
        """
        把单个商品转成 Batch API 要求的一行 JSON。

        custom_id 用 item.id，方便结果回来后按 id 写回正确商品。
        body 里是标准 chat completions 请求体。
        """
        body = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": item.full},
            ],
            "reasoning_effort": "low",
        }
        line = {
            "custom_id": str(item.id),
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": body,
        }
        return json.dumps(line)

    def make_file(self):
        """把本批次的 [start, end) 商品写成 JSONL 文件（每行一个请求）。"""
        batch_file = self.batches / self.filename
        with batch_file.open("w", encoding="utf-8") as f:
            for item in self.items[self.start : self.end]:
                f.write(self.make_jsonl(item))
                f.write("\n")

    def send_file(self):
        """上传 JSONL 到 Groq Files API，purpose='batch' 表示供批量作业使用。"""
        batch_file = self.batches / self.filename
        with batch_file.open("rb", encoding="utf-8") as f:
            response = groq.files.create(file=f, purpose="batch")
        self.file_id = response.id

    def submit_batch(self):
        """
        用已上传的 input_file_id 创建 Batch 作业。

        completion_window='24h'：允许在 24 小时内完成（异步、可排队）。
        """
        response = groq.batches.create(
            completion_window="24h",
            endpoint="/v1/chat/completions",
            input_file_id=self.file_id,
        )
        self.batch_id = response.id

    def is_ready(self):
        """
        查询作业状态；若已 completed，记下 output_file_id 并返回 True。

        批量作业常见状态：validating / in_progress / completed / failed 等。
        """
        response = groq.batches.retrieve(self.batch_id)
        status = response.status
        if status == "completed":
            self.output_file_id = response.output_file_id
        return status == "completed"

    def fetch_output(self):
        """下载批量结果 JSONL 到本地 output 目录。"""
        output_file = str(self.output / self.filename)
        response = groq.files.content(self.output_file_id)
        response.write_to_file(output_file)

    def apply_output(self):
        """
        解析结果文件：按 custom_id 把模型生成的摘要写回 items[id].summary。

        这是数据管道的「写回」步骤——之后训练/评估都会用到 summary。
        """
        output_file = str(self.output / self.filename)
        with open(output_file, "r", encoding="utf-8") as f:
            for line in f:
                json_line = json.loads(line)
                id = int(json_line["custom_id"])
                summary = json_line["response"]["body"]["choices"][0]["message"]["content"]
                self.items[id].summary = summary
        self.done = True

    @classmethod
    def create(cls, items, lite):
        """
        按 BATCH_SIZE 把整表切成多个 Batch，填入 cls.batches。

        类方法：操作的是「整条流水线」，不是单个切片。
        """
        for start in range(0, len(items), cls.BATCH_SIZE):
            end = min(start + cls.BATCH_SIZE, len(items))
            batch = Batch(items, start, end, lite)
            cls.batches.append(batch)
        print(f"Created {len(cls.batches)} batches")

    @classmethod
    def run(cls):
        """对所有批次：写文件 → 上传 → 提交作业（不等待完成）。"""
        for batch in tqdm(cls.batches):
            batch.make_file()
            batch.send_file()
            batch.submit_batch()
        print(f"Submitted {len(cls.batches)} batches")

    @classmethod
    def fetch(cls):
        """轮询未完成的批次；就绪则下载并写回摘要。"""
        for batch in tqdm(cls.batches):
            if not batch.done:
                if batch.is_ready():
                    batch.fetch_output()
                    batch.apply_output()
        finished = [batch for batch in cls.batches if batch.done]
        print(f"Finished {len(finished)} of {len(cls.batches)} batches")

    @classmethod
    def save(cls):
        """
        把 Batch 列表 pickle 到磁盘，便于中断后续跑。

        技巧：临时把 batch.items 置 None，避免把整表商品重复序列化进文件；
        写完后再把共享的 items 引用挂回去。
        """
        items = cls.batches[0].items
        for batch in cls.batches:
            batch.items = None
        with state.open("wb", encoding="utf-8") as f:
            pickle.dump(cls.batches, f)
        for batch in cls.batches:
            batch.items = items
        print(f"Saved {len(cls.batches)} batches")

    @classmethod
    def load(cls, items):
        """从 pickle 恢复 batches，并把外部传入的 items 重新挂到每个 Batch 上。"""
        with state.open("rb", encoding="utf-8") as f:
            cls.batches = pickle.load(f)
        for batch in cls.batches:
            batch.items = items
        print(f"Loaded {len(cls.batches)} batches")
