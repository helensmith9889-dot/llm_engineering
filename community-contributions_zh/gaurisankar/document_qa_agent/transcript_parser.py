import os
import sys
import types
import fitz  # PyMuPDF
from docx import Document


def read_document(file_path: str) -> str:
    """PDF、DOCX 和 TXT 文件的统一文档阅读器。

    参数：
        file_path (str)：文件的路径

    返回：
        str：提取的文本"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # 使用 rsplit 安全地处理目录名中带有点的文件名/路径
    ext = file_path.rsplit(".", 1)[-1].lower()

    if ext == "pdf":
        return _read_pdf(file_path)
    elif ext == "docx":
        return _read_docx(file_path)
    elif ext == "txt":
        return _read_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: .{ext}")


# -------- PDF --------
def _read_pdf(file_path: str) -> str:

    text = []
    with fitz.open(file_path) as doc:
        for page in doc:
            text.append(page.get_text())

    return "\n".join(text)


# -------- DOCX --------
def _read_docx(file_path: str) -> str:

    doc = Document(file_path)
    text = [para.text for para in doc.paragraphs]

    return "\n".join(text)


# -  -  -  -  TXT  -  -  -  -
def _read_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def get_file_path() -> str:
    file_path = input("Enter the file path: ").strip()
    return file_path


class CallableTranscriptParser(types.ModuleType):
    """使模块本身可调用。
    调用时，提示输入文件路径（或接受文件路径）并读取记录。"""

    def __call__(self, file_path: str = None) -> str:
        """参数：
            file_path（str，可选）：文档的路径。
                默认为 None，这将提示用户。

        返回：
            str：从文档中提取的文本。"""
        if file_path is None:
            file_path = get_file_path()
        return read_document(file_path)


sys.modules[__name__].__class__ = CallableTranscriptParser


def main():
    """独立入口点：读取文档并打印其内容。"""

    def print_transcript(file_path: str):
        transcript = read_document(file_path)
        print(transcript)

    file_path = get_file_path()
    print_transcript(file_path)


if __name__ == "__main__":
    main()
