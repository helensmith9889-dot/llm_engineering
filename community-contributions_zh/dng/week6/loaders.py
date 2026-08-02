import os
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

from datasets import load_dataset
from parser import parse
from tqdm import tqdm

CHUNK_SIZE = 1000

cpu_count = os.cpu_count()
WORKERS = max(cpu_count - 1, 1)


class ShippingContractLoader:
    def __init__(self):
        self.dataset = None

    def from_datapoint(self, datapoint):
        """尝试从此数据点创建 ShippingContract
        返回运输合同"""
        return parse(datapoint)

    def from_chunk(self, chunk):
        """根据数据集中的这部分元素创建 ShippingContracts 列表"""
        batch = [self.from_datapoint(datapoint) for datapoint in chunk]
        return [contract for contract in batch if contract is not None]

    def chunk_generator(self):
        """迭代数据集，一次生成数据点块"""
        size = len(self.dataset)
        for i in range(0, size, CHUNK_SIZE):
            yield self.dataset.select(range(i, min(i + CHUNK_SIZE, size)))

    def load_in_parallel(self, workers):
        """使用并发.futures 来分担处理数据点块的工作 -
        这会显着加快处理速度，但会占用您的计算机！"""
        results = []
        chunk_count = (len(self.dataset) // CHUNK_SIZE) + 1
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for batch in tqdm(
                pool.map(self.from_chunk, self.chunk_generator()), total=chunk_count
            ):
                results.extend(batch)
        return results

    def load(self, workers=WORKERS):
        """加载此数据集； Workers参数指定有多少个进程
        应该致力于加载和清理数据"""
        start = datetime.now()
        print("Loading dataset", flush=True)
        self.dataset = load_dataset(
            "MongoDB/supply_chain_contracts_dataset_small",
            split="train",
            trust_remote_code=True,
        )
        results = self.load_in_parallel(workers)
        finish = datetime.now()
        print(
            f"Completed with {len(results):,} datapoints in {(finish - start).total_seconds() / 60:.1f} mins",
            flush=True,
        )
        return results
