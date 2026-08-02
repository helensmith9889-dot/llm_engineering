"""模块：agent.py（社区贡献中文注释版，逻辑未改）
"""

import logging

class Agent:
    """
    An abstract superclass for Agents
    Used to log messages in a way that can identify each Agent
    """

    # 【注】Foreground colors
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # 【注】Background color
    BG_BLACK = '\033[40m'
    
    # 【注】Reset code to return to default color
    RESET = '\033[0m'

    name: str = ""
    color: str = '\033[37m'

    def log(self, message):
        """
        Log this as an info message, identifying the agent
        """
        color_code = self.BG_BLACK + self.color
        message = f"[{self.name}] {message}"
        logging.info(color_code + message + self.RESET)
