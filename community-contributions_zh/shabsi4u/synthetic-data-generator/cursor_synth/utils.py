"""中文注释版：逻辑与标识符保持不变，仅增加/翻译注释便于小白阅读。"""
import json
import re
from typing import Any, Optional

def safe_json_load(text: str) -> Optional[Any]:
    """
    Attempt to parse JSON. Heuristics:
      1) direct json.loads
      2) extract first [...] block
      3) extract first {...} block
      4) try to find JSON after common prefixes
    Returns parsed object or None.
    """
    # 首先清理文本
    text = text.strip()
    
    # 调试：打印我们要解析的内容
    print(f"DEBUG: Attempting to parse JSON from text (length: {len(text)})")
    print(f"DEBUG: First 200 chars: {text[:200]}")
    
    # 首先，尝试删除 <think> 标签并提取其后的内容
    if '<think>' in text:
        print(f"DEBUG: Found <think> tag in text")
        # 寻找 </think> 标签
        think_end = text.find('</think>')
        if think_end != -1:
            text_after_think = text[think_end + 8:].strip()
            print(f"DEBUG: Found </think> tag, trying content after: {text_after_think[:200]}")
            text = text_after_think
        else:
            # 未找到结束标记，请尝试提取 <think> 之后的所有内容
            think_start = text.find('<think>')
            if think_start != -1:
                # 尝试找到思考的终点（寻找类似 JSON 的内容）
                potential_json_start = text.find('[', think_start)
                if potential_json_start != -1:
                    text = text[potential_json_start:].strip()
                    print(f"DEBUG: No </think> tag found, trying content after <think>: {text[:200]}")
                else:
                    print(f"DEBUG: No </think> tag and no JSON found after <think>")
    
    try:
        result = json.loads(text)
        print(f"DEBUG: Direct JSON parse successful")
        return result
    except Exception as e:
        print(f"DEBUG: Direct JSON parse failed: {e}")

    # 首先尝试找到 JSON 数组（对于我们的用例来说最常见）
    # 使用更积极的正则表达式来查找数组，包括嵌套数组
    arr_match = re.search(r'(\[[\s\S]*?\])', text, flags=re.S)
    if arr_match:
        try:
            result = json.loads(arr_match.group(1))
            print(f"DEBUG: Array regex match successful")
            return result
        except Exception as e:
            print(f"DEBUG: Array regex match failed: {e}")
            # 尝试寻找更简单的数组模式
            simple_arr_match = re.search(r'(\[.*?\])', text, flags=re.S)
            if simple_arr_match:
                try:
                    result = json.loads(simple_arr_match.group(1))
                    print(f"DEBUG: Simple array regex match successful")
                    return result
                except Exception as e2:
                    print(f"DEBUG: Simple array regex match failed: {e2}")

    # 尝试查找 JSON 对象
    obj_match = re.search(r'(\{.*?\})', text, flags=re.S)
    if obj_match:
        try:
            result = json.loads(obj_match.group(1))
            print(f"DEBUG: Object regex match successful")
            return result
        except Exception as e:
            print(f"DEBUG: Object regex match failed: {e}")

    # 尝试在常见前缀（例如“Here is the JSON:”或“```json”）之后查找 JSON
    json_patterns = [
        r'(?:Here is the JSON:|```json|JSON:|Output:)\s*(\[.*?\])',
        r'(?:Here is the JSON:|```json|JSON:|Output:)\s*(\{.*?\})',
    ]
    
    for pattern in json_patterns:
        match = re.search(pattern, text, flags=re.S | re.I)
        if match:
            try:
                result = json.loads(match.group(1))
                print(f"DEBUG: Pattern match successful")
                return result
            except Exception as e:
                print(f"DEBUG: Pattern match failed: {e}")
                continue

    print(f"DEBUG: All parsing attempts failed")
    return None
