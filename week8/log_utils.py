"""
日志着色工具：把终端 ANSI 颜色码转成 Gradio HTML 可用的 <span style="color:...">。

「Price is Right」UI（price_is_right.py）用 QueueHandler 收集各 Agent 的彩色日志；
浏览器里不能直接理解 \\033[31m 这类 escape code，因此用 reformat() 映射成 CSS 颜色。

与 agents/agent.py 中的颜色常量对应：黑底+前景色 → 一组十六进制颜色。
"""

# Foreground colors：与 Agent 基类保持一致的 ANSI 前景色
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
MAGENTA = '\033[35m'
CYAN = '\033[36m'
WHITE = '\033[37m'

# Background color
BG_BLACK = '\033[40m'
BG_BLUE = '\033[44m'

# Reset code to return to default color：在 HTML 里对应关闭 </span>
RESET = '\033[0m'

# ANSI 组合 → 网页显示用的颜色；框架蓝底白字映射为橙色以突出
mapper = {
    BG_BLACK+RED: "#dd0000",
    BG_BLACK+GREEN: "#00dd00",
    BG_BLACK+YELLOW: "#dddd00",
    BG_BLACK+BLUE: "#0000ee",
    BG_BLACK+MAGENTA: "#aa00dd",
    BG_BLACK+CYAN: "#00dddd",
    BG_BLACK+WHITE: "#87CEEB",
    BG_BLUE+WHITE: "#ff7800"
}


def reformat(message):
    """
    将日志字符串中的 ANSI 颜色序列替换为 HTML span。

    参数:
        message: 可能含 BG_*+COLOR 与 RESET 的原始日志行
    返回:
        适合塞进 Gradio HTML 组件的字符串
    """
    for key, value in mapper.items():
        message = message.replace(key, f'<span style="color: {value}">')
    message = message.replace(RESET, '</span>')
    return message
    
    
