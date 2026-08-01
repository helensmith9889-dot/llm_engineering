"""
Frontier Agent（前沿模型定价 Agent）：RAG + 前沿 LLM 估计商品真价。

在 Ensemble 中权重最高（约 0.8），思路是 Retrieval-Augmented Generation：
  1. 用 SentenceTransformer 把商品描述编成向量（embedding）
  2. 在 Chroma 向量库里检索最相似的 5 个历史商品及其成交价
  3. 把「相似商品 + 价格」作为 context 塞进 prompt，让 gpt 等前沿模型估价

教学对照：
  - Specialist：微调模型「记住」了定价规律（参数里）
  - Frontier：检索「类似案例」再推理（知识在向量库里）
  - 两者一起用，是典型的 LLM 工程组合拳
"""

import re
from typing import List, Dict
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from agents.agent import Agent


class FrontierAgent(Agent):
    """
    前沿模型定价 Agent：连接 OpenAI、Chroma collection 与本地 embedding 模型。
    """

    name = "Frontier Agent"
    color = Agent.BLUE

    MODEL = "gpt-4o-mini"

    def __init__(self, collection):
        """
        Set up this instance by connecting to OpenAI or DeepSeek, to the Chroma Datastore,
        And setting up the vector encoding model

        参数:
            collection: Chroma collection，存放历史商品文档与 metadata（含 price）
        """
        self.log("Initializing Frontier Agent")
        self.client = OpenAI()
        # 运行时覆盖类属性，改用更新的模型名
        self.MODEL = "gpt-5.1"
        self.log("Frontier Agent is setting up with OpenAI")
        self.collection = collection
        # all-MiniLM-L6-v2：轻量句向量模型，把文本映射到可检索的向量空间
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self.log("Frontier Agent is ready")

    def make_context(self, similars: List[str], prices: List[float]) -> str:
        """
        Create context that can be inserted into the prompt

        把检索到的相似商品与价格拼成可读上下文，供 LLM「参照报价」。

        参数:
            similars: 相似商品的描述文本列表
            prices: 对应价格列表
        返回:
            插入 user prompt 的上下文段落
        """
        message = "To provide some context, here are some other items that might be similar to the item you need to estimate.\n\n"
        for similar, price in zip(similars, prices):
            message += f"Potentially related product:\n{similar}\nPrice is ${price:.2f}\n\n"
        return message

    def messages_for(
        self, description: str, similars: List[str], prices: List[float]
    ) -> List[Dict[str, str]]:
        """
        Create the message list to be included in a call to OpenAI
        With the system and user prompt

        参数:
            description: 待估价商品描述
            similars / prices: RAG 检索结果
        返回:
            OpenAI chat messages 列表（此处仅 user 角色）
        """
        message = f"Estimate the price of this product. Respond with the price, no explanation\n\n{description}\n\n"
        message += self.make_context(similars, prices)
        return [{"role": "user", "content": message}]

    def find_similars(self, description: str):
        """
        Return a list of items similar to the given one by looking in the Chroma datastore

        RAG 的 Retrieval 步骤：编码查询 → collection.query → 取 documents 与 prices。
        """
        self.log(
            "Frontier Agent is performing a RAG search of the Chroma datastore to find 5 similar products"
        )
        vector = self.model.encode([description])
        results = self.collection.query(query_embeddings=vector.astype(float).tolist(), n_results=5)
        documents = results["documents"][0][:]
        # metadata 里预先存了每个商品的 price 字段
        prices = [m["price"] for m in results["metadatas"][0][:]]
        self.log("Frontier Agent has found similar products")
        return documents, prices

    def get_price(self, s) -> float:
        """
        A utility that plucks a floating point number out of a string

        从模型回复中抠出第一个数字（去掉 $ 与逗号）。解析失败则返回 0.0。
        """
        s = s.replace("$", "").replace(",", "")
        match = re.search(r"[-+]?\d*\.\d+|\d+", s)
        return float(match.group()) if match else 0.0

    def price(self, description: str) -> float:
        """
        Make a call to OpenAI or DeepSeek to estimate the price of the described product,
        by looking up 5 similar products and including them in the prompt to give context

        参数:
            description: 商品描述
        返回:
            解析后的估计价格（美元）
        """
        documents, prices = self.find_similars(description)
        self.log(
            f"Frontier Agent is about to call {self.MODEL} with context including 5 similar products"
        )
        response = self.client.chat.completions.create(
            model=self.MODEL,
            messages=self.messages_for(description, documents, prices),
            seed=42,
            reasoning_effort="none",
        )
        reply = response.choices[0].message.content
        result = self.get_price(reply)
        self.log(f"Frontier Agent completed - predicting ${result:.2f}")
        return result
