"""AI Mastered Dungeon Extraction 游戏初始化模块。"""

from logging import basicConfig, getLogger

from dotenv import load_dotenv


# 环境初始化。
load_dotenv(override=True)

# 设置全局记录器。
LOG_STYLE = '{'
LOG_LEVEL = 'INFO'
LOG_FORMAT = ('{asctime} {levelname:<8} {processName}({process}) '
              '{threadName} {name} {lineno} "{message}"')
basicConfig(level=LOG_LEVEL, style='{', format=LOG_FORMAT)

getLogger(__name__).info('INITIALIZED GAME LOGGER')
