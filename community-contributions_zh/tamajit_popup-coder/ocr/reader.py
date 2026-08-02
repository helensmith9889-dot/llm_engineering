"""中文注释版：逻辑与标识符保持不变，仅增加/翻译注释便于小白阅读。"""
# 小白提示：下面代码逻辑未改，仅补充中文注释便于阅读
import pytesseract
from PIL import Image
pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract" # if tesseract not found

def extract_text(image_path) :
    try :
        img = Image.open(image_path).convert("L")
        text = pytesseract.image_to_string(img)
        return text
    
    except Exception as e :
        return f"[ERROR] ocr failed : {e}"