"""
深度神经网络（DNN）价格回归模块。

本文件用「传统深度学习」做商品定价基线，用来和后续微调的 LLM 对比：
- 输入：商品摘要文本 → HashingVectorizer 变成固定长度稀疏/哈希特征；
- 模型：带残差连接（skip connection）的多层全连接网络；
- 输出：一个标量价格。

教学要点：
- 张量（tensor）：多维数组，PyTorch 用它在 GPU/CPU 上做矩阵运算；
- DataLoader：按 mini-batch 喂数据，训练更稳、内存占用更可控；
- 目标是回归（regression），不是分类——预测连续价格。
"""

import numpy as np
from tqdm.notebook import tqdm
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from torch.optim.lr_scheduler import CosineAnnealingLR
from sklearn.feature_extraction.text import HashingVectorizer


class ResidualBlock(nn.Module):
    """
    残差块：F(x) + x。

    深层网络容易「梯度消失」——加法和恒等映射让信号更容易穿过多层，
    这是 ResNet 思想的简化版，适合全连接回归网络。
    """

    def __init__(self, hidden_size, dropout_prob):
        """
        参数:
            hidden_size: 隐藏层维度（输入输出相同，才能做 x + F(x)）
            dropout_prob: Dropout 比例，训练时随机丢神经元，减轻过拟合
        """
        super(ResidualBlock, self).__init__()
        # Sequential：按顺序执行 Linear → 归一化 → 激活 → Dropout → ...
        self.block = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.LayerNorm(hidden_size),  # 层归一化，稳定激活分布
            nn.ReLU(),
            nn.Dropout(dropout_prob),
            nn.Linear(hidden_size, hidden_size),
            nn.LayerNorm(hidden_size),
        )
        self.relu = nn.ReLU()

    def forward(self, x):
        """前向传播：保存输入作残差，再与块输出相加后过 ReLU。"""
        residual = x
        out = self.block(x)
        out += residual  # Skip connection
        return self.relu(out)


class DeepNeuralNetwork(nn.Module):
    """
    深度全连接价格回归网络。

    结构：输入层 → 若干 ResidualBlock → 输出层（1 维价格）。
    num_layers 近似控制「总深度」：去掉输入/输出后，中间残差块数为 num_layers-2。
    """

    def __init__(self, input_size, num_layers=10, hidden_size=4096, dropout_prob=0.2):
        """
        参数:
            input_size: 特征向量维度（本课为 HashingVectorizer 的 n_features）
            num_layers: 期望总层数（含输入、输出的粗略计数）
            hidden_size: 隐藏宽度；越大容量越强，也越容易过拟合
            dropout_prob: Dropout 概率
        """
        super(DeepNeuralNetwork, self).__init__()

        # First layer：把稀疏/哈希特征映射到高维隐藏空间
        self.input_layer = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout_prob),
        )

        # Residual blocks：ModuleList 可正确注册子模块参数供优化器更新
        self.residual_blocks = nn.ModuleList()
        for i in range(num_layers - 2):
            self.residual_blocks.append(ResidualBlock(hidden_size, dropout_prob))

        # Output layer：回归一个标量（价格的归一化对数目标）
        self.output_layer = nn.Linear(hidden_size, 1)

    def forward(self, x):
        """定义数据如何流过网络；训练/推理都会调用。"""
        x = self.input_layer(x)

        for block in self.residual_blocks:
            x = block(x)

        return self.output_layer(x)


class DeepNeuralNetworkRunner:
    """
    训练与推理的「编排器」：向量化文本、建 DataLoader、训练循环、保存/加载、预测。

    价格做了 log1p + 标准化，因为商品价格长尾分布（便宜的很多、很贵的很少），
    在对数空间学习更稳；推理时再反变换回美元。
    """

    def __init__(self, train, val):
        """
        参数:
            train / val: Item 列表（含 summary 与 price），分别作训练集与验证集
        """
        self.train_data = train
        self.val_data = val
        self.vectorizer = None
        self.model = None
        self.device = None
        self.loss_function = None
        self.optimizer = None
        self.scheduler = None
        self.train_dataset = None
        self.train_loader = None
        self.y_mean = None
        self.y_std = None

        # 固定随机种子，便于课程复现实验结果
        np.random.seed(42)
        torch.manual_seed(42)
        torch.cuda.manual_seed(42)

    def setup(self):
        """
        准备特征、标签张量、模型、优化器与 DataLoader。

        张量形状直觉：
        - X: (样本数, 特征维)  例如 (N, 5000)
        - y: (样本数, 1)      unsqueeze(1) 把一维变成列向量，匹配输出层
        """
        # HashingVectorizer：不建词典，哈希到固定 n_features，省内存、适合大数据
        self.vectorizer = HashingVectorizer(n_features=5000, stop_words="english", binary=True)

        # 训练集：用摘要文本拟合并变换（fit_transform）
        train_documents = [item.summary for item in self.train_data]
        X_train_np = self.vectorizer.fit_transform(train_documents)
        self.X_train = torch.FloatTensor(X_train_np.toarray())
        y_train_np = np.array([float(item.price) for item in self.train_data])
        self.y_train = torch.FloatTensor(y_train_np).unsqueeze(1)

        # 验证集：只 transform，不重新 fit，避免「偷看」验证分布
        val_documents = [item.summary for item in self.val_data]
        X_val_np = self.vectorizer.transform(val_documents)
        self.X_val = torch.FloatTensor(X_val_np.toarray())
        y_val_np = np.array([float(item.price) for item in self.val_data])
        self.y_val = torch.FloatTensor(y_val_np).unsqueeze(1)

        # log(price+1) 再按训练集均值/标准差标准化；验证集用同一套统计量
        y_train_log = torch.log(self.y_train + 1)
        y_val_log = torch.log(self.y_val + 1)
        self.y_mean = y_train_log.mean()
        self.y_std = y_train_log.std()
        self.y_train_norm = (y_train_log - self.y_mean) / self.y_std
        self.y_val_norm = (y_val_log - self.y_mean) / self.y_std

        self.model = DeepNeuralNetwork(self.X_train.shape[1])
        total_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        print(f"Deep Neural Network created with {total_params:,} parameters")

        # 优先 CUDA，其次 Apple MPS，否则 CPU
        if torch.cuda.is_available():
            self.device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            self.device = torch.device("mps")
        else:
            self.device = torch.device("cpu")

        print(f"Using {self.device}")

        self.model.to(self.device)
        # L1Loss = MAE（平均绝对误差），对异常价格不如 MSE 敏感
        self.loss_function = nn.L1Loss()
        # AdamW：带权重衰减的 Adam，常见于现代深度学习
        self.optimizer = optim.AdamW(self.model.parameters(), lr=0.001, weight_decay=0.01)
        # 余弦退火：学习率随 epoch 按余弦曲线降到 eta_min
        self.scheduler = CosineAnnealingLR(self.optimizer, T_max=10, eta_min=0)

        # TensorDataset + DataLoader：按 batch_size=64 打乱后迭代
        self.train_dataset = TensorDataset(self.X_train, self.y_train_norm)
        self.train_loader = DataLoader(self.train_dataset, batch_size=64, shuffle=True)

    def train(self, epochs=5):
        """
        标准训练循环：每个 epoch 扫一遍训练集，再在验证集上看损失与美元 MAE。

        步骤简述：清梯度 → 前向 → 算损失 → 反向传播 →（可选）裁剪梯度 → 更新参数。
        """
        for epoch in range(1, epochs + 1):
            self.model.train()  # 启用 Dropout 等训练行为
            train_losses = []

            for batch_X, batch_y in tqdm(self.train_loader):
                # 把本 mini-batch 搬到与模型相同的 device
                batch_X = batch_X.to(self.device)
                batch_y = batch_y.to(self.device)

                self.optimizer.zero_grad()  # 否则梯度会累加
                outputs = self.model(batch_X)
                loss = self.loss_function(outputs, batch_y)
                loss.backward()

                # Gradient clipping：限制梯度范数，防止一次爆炸更新
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)

                self.optimizer.step()
                train_losses.append(loss.item())

            # Validation：eval + no_grad，关闭 Dropout、不算梯度，省显存
            self.model.eval()
            with torch.no_grad():
                val_outputs = self.model(self.X_val.to(self.device))
                val_loss = self.loss_function(val_outputs, self.y_val_norm.to(self.device))

                # Convert back to original scale for meaningful metrics
                # 反标准化 + expm1，还原到美元尺度再算 MAE
                val_outputs_orig = torch.exp(val_outputs * self.y_std + self.y_mean) - 1
                mae = torch.abs(val_outputs_orig - self.y_val.to(self.device)).mean()

            avg_train_loss = np.mean(train_losses)
            print(f"Epoch [{epoch}/{epochs}]")
            print(f"Train Loss: {avg_train_loss:.4f}, Val Loss: {val_loss.item():.4f}")
            print(f"Val mean absolute error: ${mae.item():.2f}")
            print(f"Learning rate: {self.scheduler.get_last_lr()[0]:.6f}")

            self.scheduler.step()

    def save(self, path):
        """只保存模型权重 state_dict（体积小，加载时需先建好同结构模型）。"""
        torch.save(self.model.state_dict(), path)

    def load(self, path, device="mps"):
        """从磁盘加载权重并放到当前 runner 的 device 上。"""
        self.model.load_state_dict(torch.load(path, map_location=device))
        self.model.to(self.device)

    def inference(self, item):
        """
        对单个商品做推理：摘要 → 向量 → 模型 → 反变换 → 非负价格。

        返回美元价格（float）；负预测钳到 0。
        """
        self.model.eval()
        with torch.no_grad():
            vector = self.vectorizer.transform([item.summary])
            vector = torch.FloatTensor(vector.toarray()).to(self.device)
            pred = self.model(vector)[0]
            result = torch.exp(pred * self.y_std + self.y_mean) - 1
            result = result.item()
        return max(0, result)
