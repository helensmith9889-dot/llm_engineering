"""
数据加载器：从 Amazon Reviews 2023 元数据中并行抽取商品 Item。

微调与 DNN 训练都依赖「干净、可复现」的数据集。本模块按品类加载
Hugging Face 上的 raw_meta_* 子集，切成 chunk，用多进程调用 parser.parse
过滤并结构化——这是 LLM 工程里典型的 ETL（抽取-转换-加载）第一步。

与 DataLoader 的区别：
- 这里的 ItemLoader 是「离线灌入原始语料」；
- PyTorch DataLoader 是「训练时按 batch 送张量」。两者都叫 loader，阶段不同。
"""

from datetime import datetime
from tqdm import tqdm
from datasets import load_dataset
from concurrent.futures import ProcessPoolExecutor
from pricer.parser import parse
import os

# 每个进程一次处理多少条原始记录
CHUNK_SIZE = 1000

# 留 1 个核给系统，至少用 1 个 worker
cpu_count = os.cpu_count()
WORKERS = max(cpu_count - 1, 1)


class ItemLoader:
    """
    按 Amazon 品类名加载并清洗商品列表。

    流程：load_dataset → 分块 → 多进程 parse → 返回 Item 列表。
    """

    def __init__(self, category):
        """
        参数:
            category: 品类字符串，例如 "Electronics"，对应 raw_meta_{category}
        """
        self.category = category
        self.dataset = None

    def from_datapoint(self, datapoint):
        """
        尝试把一条原始元数据转成 Item。
        成功则返回 Item；不符合价格/长度等规则则返回 None（由 parse 决定）。
        """
        return parse(datapoint, self.category)

    def from_chunk(self, chunk):
        """
        处理一个 Dataset 切片：对每条调用 from_datapoint，丢掉 None。

        在 ProcessPoolExecutor 的子进程里执行，实现真正的并行 CPU 清洗。
        """
        batch = [self.from_datapoint(datapoint) for datapoint in chunk]
        return [item for item in batch if item is not None]

    def chunk_generator(self):
        """
        生成器：按 CHUNK_SIZE 依次 yield 子 Dataset。

        用 select(range(...)) 避免一次性把全部索引逻辑写死在内存循环里。
        """
        size = len(self.dataset)
        for i in range(0, size, CHUNK_SIZE):
            yield self.dataset.select(range(i, min(i + CHUNK_SIZE, size)))

    def load_in_parallel(self, workers):
        """
        用 concurrent.futures 把各 chunk 分给多个进程。

        注意：会占满 CPU，笔记本上可能短暂卡顿——这是用算力换清洗速度。
        """
        results = []
        chunk_count = (len(self.dataset) // CHUNK_SIZE) + 1
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for batch in tqdm(pool.map(self.from_chunk, self.chunk_generator()), total=chunk_count):
                results.extend(batch)
        return results

    def load(self, workers=WORKERS):
        """
        入口：下载/缓存指定品类的 full 划分，并行清洗后返回 Item 列表。

        trust_remote_code=True：允许数据集脚本在本地执行（该数据集需要）。
        """
        start = datetime.now()
        print(f"Loading dataset {self.category}", flush=True)
        self.dataset = load_dataset(
            "McAuley-Lab/Amazon-Reviews-2023",
            f"raw_meta_{self.category}",
            split="full",
            trust_remote_code=True,
        )
        results = self.load_in_parallel(workers)
        finish = datetime.now()
        print(
            f"Completed {self.category} with {len(results):,} datapoints in {(finish - start).total_seconds() / 60:.1f} mins",
            flush=True,
        )
        return results
