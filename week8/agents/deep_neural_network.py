"""
深度神经网络定价模型（DNN）及其推理封装。

在「Price is Right」Ensemble 中，NeuralNetworkAgent 调用本模块：
  商品文本 → HashingVectorizer（5000 维稀疏特征）
           → DeepNeuralNetwork（残差块堆叠）
           → 反标准化 / exp 还原 → 美元价格

教学要点：
  - ResidualBlock（残差块）：输出 = F(x) + x，缓解深层网络梯度消失
  - 价格常在 log 空间训练（更接近对数正态），推理时用 Y_MEAN / Y_STD 还原
  - Inference 类只负责预测，不包含训练循环（训练一般在 notebook 里完成）
"""

import numpy as np
from tqdm.notebook import tqdm
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from torch.optim.lr_scheduler import CosineAnnealingLR
from sklearn.feature_extraction.text import HashingVectorizer
import logging


class ResidualBlock(nn.Module):
    """
    残差块：两层全连接 + LayerNorm + Dropout，再与输入相加（skip connection）。

    直觉：网络只需学习「残差」F(x)，而不是完整映射，深层时更稳定。
    """

    def __init__(self, hidden_size, dropout_prob):
        """
        参数:
            hidden_size: 隐藏层维度（与前后层一致，才能做 x + F(x)）
            dropout_prob: Dropout 比例，减轻过拟合
        """
        super(ResidualBlock, self).__init__()
        self.block = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout_prob),
            nn.Linear(hidden_size, hidden_size),
            nn.LayerNorm(hidden_size),
        )
        self.relu = nn.ReLU()

    def forward(self, x):
        """前向：保存 residual → 过 block → 相加 → ReLU。"""
        residual = x
        out = self.block(x)
        out += residual  # Skip connection
        return self.relu(out)


class DeepNeuralNetwork(nn.Module):
    """
    深度回归网络：输入层 → 多个 ResidualBlock → 单神经元输出（log 空间价格）。
    """

    def __init__(self, input_size, num_layers=10, hidden_size=4096, dropout_prob=0.2):
        """
        参数:
            input_size: 特征向量维度（与 HashingVectorizer n_features 一致，默认 5000）
            num_layers: 总「层」概念上的深度；残差块数量为 num_layers - 2
            hidden_size: 隐藏宽度
            dropout_prob: Dropout 概率
        """
        super(DeepNeuralNetwork, self).__init__()

        # First layer：把稀疏/哈希特征映射到宽隐藏空间
        self.input_layer = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout_prob),
        )

        # Residual blocks：堆叠多个残差块加深网络
        self.residual_blocks = nn.ModuleList()
        for i in range(num_layers - 2):
            self.residual_blocks.append(ResidualBlock(hidden_size, dropout_prob))

        # Output layer：回归一个标量（训练目标通常是标准化后的 log 价格）
        self.output_layer = nn.Linear(hidden_size, 1)

    def forward(self, x):
        """前向传播：input → 各残差块 → 输出标量预测。"""
        x = self.input_layer(x)

        for block in self.residual_blocks:
            x = block(x)

        return self.output_layer(x)


# 训练时对 log(price+1) 做标准化用的均值与标准差；推理时必须用同一套常数还原
Y_STD = 1.0328539609909058
Y_MEAN = 4.434937953948975


class DeepNeuralNetworkInference:
    """
    推理封装：准备 vectorizer / 模型 / 设备，加载权重，对单条文本预测价格。
    """

    def __init__(self):
        """初始化占位属性，并固定随机种子以保证可复现（对 dropout 等行为有影响）。"""
        self.vectorizer = None
        self.model = None
        self.device = None

        np.random.seed(42)
        torch.manual_seed(42)
        torch.cuda.manual_seed(42)

    def setup(self):
        """
        构建 HashingVectorizer 与 DNN，并选择 cuda / mps / cpu 设备。

        HashingVectorizer：无需拟合词表，用哈希把 token 映射到固定维度，适合在线推理。
        """
        self.vectorizer = HashingVectorizer(n_features=5000, stop_words="english", binary=True)
        self.model = DeepNeuralNetwork(5000)
        if torch.cuda.is_available():
            self.device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            self.device = torch.device("mps")
        else:
            self.device = torch.device("cpu")

        logging.info(f"Neural Network is using {self.device}")

        self.model.to(self.device)

    def load(self, path):
        """
        从 path 加载 state_dict 到当前模型，并移动到 self.device。

        参数:
            path: 例如 deep_neural_network.pth
        """
        self.model.load_state_dict(torch.load(path, map_location=self.device))
        self.model.to(self.device)

    def inference(self, text):
        """
        对单条商品描述做价格推理。

        步骤：eval 模式 → 向量化 → 前向 → 反标准化 (pred * STD + MEAN) → exp - 1 → 截断非负。

        参数:
            text: 商品描述字符串
        返回:
            估计价格（美元，float，最小为 0）
        """
        self.model.eval()
        with torch.no_grad():
            vector = self.vectorizer.transform([text])
            vector = torch.FloatTensor(vector.toarray()).to(self.device)
            pred = self.model(vector)[0]
            # 训练目标是标准化的 log1p(price)；这里逆变换回原始美元尺度
            result = torch.exp(pred * Y_STD + Y_MEAN) - 1
            result = result.item()
        return max(0, result)
