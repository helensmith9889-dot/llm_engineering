---
user: 'topic="Transformer Architecture" audience="technical professional" length="concise"'
---

# Transformer 架构

**快速摘要（2–4 句）：**  
> Transformer 是 2017 年提出的神经网络架构，用注意力机制取代循环结构，深刻改变了 NLP。其效率与可扩展性催生了 GPT 等大语言模型。  

**细微差别 / 注意点：**  
- 扩展性好，但需要大量算力。  
- 注意力对序列长度是二次复杂度（限制上下文长度）。  
- 相较简单模型更难解释。  

**核心概念：**  
- **自注意力（Self-attention）：** 让 token 彼此关注。  
- **位置编码（Positional encoding）：** 注入顺序信息。  
- **编码器/解码器块：** 模块化结构，适用于翻译等任务。  

**直观例子 / 演示：**  
> 读句子 “The cat sat on the mat.” 时，注意力会让模型更重视 *cat ↔ sat* 这类联系，而不是无关词。  

**何时有用 / 局限：**  
- 用途：翻译、摘要、代码生成。  
- 局限：计算密集，不太适合极长序列。  

**简洁学习路径（4–7 步）：**  
1. 复习前馈网络与 RNN 基础。  
2. 阅读 “Attention is All You Need”（Vaswani et al., 2017）。  
3. 学习带注释的 Transformer 代码（约 10 小时）。  
4. 在玩具数据上训练迷你 Transformer。  
5. 了解 scaling laws 与 LLM。  

**练习（2–4，含难度）：**  
1. [简单] 用通俗语言解释自注意力。  
2. [中等] 用 Python 实现缩放点积注意力。  

**参考与引用**  
1. Vaswani et al. *Attention Is All You Need* (2017).  
2. Illustrated Transformer — https://jalammar.github.io/illustrated-transformer/  

**后续提示（建议）：**  
- "Write PyTorch code for a single attention head."  
- "Compare Transformers vs RNNs for translation."  
