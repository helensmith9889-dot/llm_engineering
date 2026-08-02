"""中文注释版：逻辑与标识符保持原文，便于 import 与运行。"""
import os
import subprocess
import threading
from pathlib import Path
import gradio as gr
from dotenv import load_dotenv

# 设置路径
CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent.parent.parent
INDEX_FILE = CURRENT_DIR / "navigator_index.pkl"

# 延迟初始化搜索器
searcher = None
searcher_error = None

def load_searcher():
    global searcher, searcher_error
    try:
        from searcher import CourseSearcher
        searcher = CourseSearcher()
        searcher_error = None
        return True
    except Exception as e:
        searcher = None
        searcher_error = str(e)
        return False

# 首次尝试加载搜索器
load_searcher()

# 索引器线程的锁定
indexer_lock = threading.Lock()
indexing_in_progress = False

def run_indexer_thread():
    global indexing_in_progress
    with indexer_lock:
        indexing_in_progress = True
    try:
        # 运行索引器脚本
        indexer_path = CURRENT_DIR / "indexer.py"
        python_exe = WORKSPACE_ROOT / ".venv" / "Scripts" / "python.exe"
        if not python_exe.exists():
            python_exe = "python"
            
        result = subprocess.run(
            [str(python_exe), str(indexer_path)],
            capture_output=True,
            text=True,
            cwd=str(WORKSPACE_ROOT)
        )
        if result.returncode == 0:
            load_searcher()
            status = "Success: Index built successfully! Reloaded searcher."
        else:
            status = f"Error running indexer: {result.stderr}"
    except Exception as e:
        status = f"Failed to run indexer: {e}"
    finally:
        with indexer_lock:
            indexing_in_progress = False
    return status

def trigger_indexing():
    global indexing_in_progress
    if indexing_in_progress:
        return "Indexing is already running in the background. Please wait..."
        
    thread = threading.Thread(target=run_indexer_thread)
    thread.start()
    return "Indexing started in the background. Please check back in a minute. Reloading searcher upon completion..."

def get_status_md():
    if indexing_in_progress:
        return "⏳ **System Status:** Indexing in progress in the background..."
    if searcher:
        return f"🟢 **System Status:** Connected to index containing **{len(searcher.chunks)}** codebase chunks."
    else:
        return "🔴 **System Status:** No search index found. Please click **Build/Rebuild Index** below."

# Gradio 聊天机器人处理
def chat_respond(message, history):
    global searcher
    if not searcher:
        # 尝试重新加载
        if not load_searcher():
            return history + [{"role": "assistant", "content": f"⚠️ Search index is not loaded. Error: {searcher_error or 'No index found.'}. Please build the index first using the utility tab."}]
            
    # 将历史记录格式化为搜索者期望的元组格式
    history_tuples = []
    # Gradio 5.x 中的历史记录可以是字典列表： [{'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': '...'}]
    temp_user = None
    for item in history:
        if item['role'] == 'user':
            temp_user = item['content']
        elif item['role'] == 'assistant' and temp_user is not None:
            history_tuples.append((temp_user, item['content']))
            temp_user = None

    # 得到答案
    answer = searcher.answer_question(message, top_k=4, history=history_tuples)
    
    # 返回更新的历史记录
    return history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": answer}
    ]

# 分级搜索处理
def explore_search(query, top_k):
    global searcher
    if not searcher:
        if not load_searcher():
            return f"⚠️ Search index is not loaded. Error: {searcher_error or 'No index found.'}."
            
    try:
        results = searcher.search(query, top_k=int(top_k))
        if not results:
            return "No matches found."
            
        md_output = ""
        for i, res in enumerate(results, 1):
            meta = res["chunk"]["metadata"]
            file_path = meta.get("file_path", "unknown")
            file_type = meta.get("file_type", "unknown")
            score = res["score"]
            content = res["chunk"]["content"]
            
            # 创建标题
            if file_type == "notebook":
                loc = f"Cell {meta.get('cell_index')} ({meta.get('cell_type')})"
            elif file_type == "python":
                loc = f"Lines {meta.get('line_start')}-{meta.get('line_end')}"
            else:
                loc = "Markdown Section"
                
            md_output += f"### {i}. [{file_type.upper()}] {file_path} - {loc}\n"
            md_output += f"**Relevance Score:** `{score:.4f}`\n\n"
            
            # 根据 Markdown 渲染的类型包装内容
            if file_type == "python" or (file_type == "notebook" and meta.get("cell_type") == "code"):
                md_output += f"```python\n{content}\n```\n\n"
            else:
                md_output += f"> {content.replace('\n', '\n> ')}\n\n"
            md_output += "---\n\n"
            
        return md_output
    except Exception as e:
        return f"Error during search: {e}"

# 构建自定义高级主题
theme = gr.themes.Soft(
    primary_hue="orange",
    secondary_hue="slate",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Outfit"), "sans-serif"]
)

# 自定义 CSS 实现发光黑暗美学和样式覆盖
custom_css = """
.container {
    max-width: 1100px;
    margin: 0 auto;
    padding: 20px;
}
.header-box {
    text-align: center;
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border-radius: 12px;
    padding: 30px;
    margin-bottom: 25px;
    border: 1px solid #334155;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}
.header-box h1 {
    color: #f97316 !important;
    font-size: 2.2rem;
    margin-bottom: 10px;
}
.header-box p {
    color: #94a3b8;
    font-size: 1.1rem;
}
.status-bar {
    background-color: #0f172a;
    padding: 10px 15px;
    border-radius: 8px;
    border: 1px solid #1e293b;
    margin-bottom: 20px;
}
