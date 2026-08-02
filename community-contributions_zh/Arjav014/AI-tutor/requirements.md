# 需求与依赖说明

本文说明 **AI 导师** 项目的系统、库与环境要求。

## 1. 系统要求
- **Python：** 建议 `3.12+`（已在 `3.12.x` 测试）
- **包管理器：** [uv](https://github.com/astral-sh/uv)（强烈推荐，安装快、环境隔离好）

---

## 2. Python 包依赖
项目依赖如下（见 `requirements.txt`）：

| 包 | 用途 |
| :--- | :--- |
| `openai` | 访问 OpenAI 兼容的 Gemini API |
| `python-dotenv` | 从本地 `.env` 加载环境变量（如 API Key） |
| `ipython` | 在 Jupyter 中渲染富文本（`Markdown`、`display` 等） |
| `ipykernel` | 连接 Notebook/Lab 与 Python 内核 |
| `jupyter` | Notebook 服务器界面 |

---

## 3. 环境变量与 API
要使用底层模型（`gemini-2.5-flash-lite`），需要 Gemini API Key。

1. **获取 Key：** 在 [Google AI Studio](https://aistudio.google.com/) 免费创建。
2. **配置文件：** 在 notebook 同目录创建 `.env`：
   ```env
   GOOGLE_API_KEY=your_actual_api_key_here
   ```
3. **代码中用法：** notebook 用 `python-dotenv` 动态加载：
   ```python
   load_dotenv(override=True)
   api_key = os.getenv('GOOGLE_API_KEY')
   ```

---

## 4. 运行前检查
启动 notebook 时请确认：
- API Key 有效
- 网络可访问 `generativelanguage.googleapis.com`
- Python 虚拟环境已激活
