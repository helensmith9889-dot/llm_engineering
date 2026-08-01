"""
Agent 基类（抽象超类）：多智能体「Price is Right」扫货系统的统一日志入口。

本周核心思想是 Multi-Agent System（多智能体系统）：把「扫优惠」「估真价」
「发通知」「做规划」拆成多个专职 Agent，各自只做一件事，再由规划 Agent 编排。

本文件不负责业务逻辑，只提供：
  1. 每个 Agent 的名字与终端彩色标识（便于在日志里分辨是谁在说话）
  2. 统一的 log() 方法，把消息打上 [AgentName] 前缀并着色输出

所有具体 Agent（Scanner / Ensemble / Planning / Messaging 等）都应继承本类。
"""

import logging

class Agent:
    """
    Agent 的抽象超类（abstract superclass）。

    作用：让每个子类 Agent 在写日志时能自动带上自己的名字与颜色，
    方便在多智能体协作时一眼看出「是哪个 Agent 在执行哪一步」。

    子类通常会覆盖：
      - name: 显示名，例如 "Scanner Agent"
      - color: 前景色 ANSI 码，例如 Agent.CYAN
    """

    # 前景色（Foreground）：控制文字颜色的 ANSI escape codes
    # 终端收到这些特殊字符后会改变后续文字颜色，RESET 后恢复默认
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # 背景色（Background）：黑底，与前景色组合后对比更清晰
    BG_BLACK = '\033[40m'
    
    # 重置码：输出后终端颜色恢复默认，避免「染色」后续无关日志
    RESET = '\033[0m'

    # 子类应覆盖这两个类属性；默认白字、空名字
    name: str = ""
    color: str = '\033[37m'

    def log(self, message):
        """
        以 INFO 级别记录一条日志，并标识是哪个 Agent 发出的。

        参数:
            message: 要记录的说明文字（字符串）

        实现要点：
          - 黑底 + 本 Agent 前景色，突出显示
          - 消息前加 [self.name]，多智能体并行时不会混淆
        """
        color_code = self.BG_BLACK + self.color
        message = f"[{self.name}] {message}"
        logging.info(color_code + message + self.RESET)
