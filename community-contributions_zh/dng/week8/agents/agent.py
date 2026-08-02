import logging

class Agent:
    """Agent 的抽象超类
    用于以可以识别每个代理的方式记录消息"""

    # 前景色
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # 背景颜色
    BG_BLACK = '\033[40m'
    
    # 重置代码以返回默认颜色
    RESET = '\033[0m'

    name: str = ""
    color: str = '\033[37m'

    def log(self, message):
        """将此记录为信息消息，用于识别代理"""
        color_code = self.BG_BLACK + self.color
        message = f"[{self.name}] {message}"
        logging.info(color_code + message + self.RESET)