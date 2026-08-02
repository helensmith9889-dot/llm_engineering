"""AI掌握了地下城提取游戏的游戏模块。"""

from logging import getLogger
from typing import Callable, NamedTuple


# 定义游戏玩法的配置类。
class Gameplay_Config(NamedTuple):
    """广播接口配置类。"""
    draw_func: Callable
    narrate_func: Callable
    scene_style: str
    scene_prompt: str
    storyteller_prompt: str
    disable_img: str
    error_img: str
    error_narrator: str
    error_illustrator: str


# 定义游戏的功能。

def get_gameplay_function(config: Gameplay_Config):
    """返回预先配置的回合游戏功能。"""
    def gameplay_function(message, history):
        """生成Game Master的响应并绘制场景图像。"""
        # 请求解说。
        _logger.info(f'NARRATING SCENE...')
        try:
            response = config.narrate_func(message, history, config.storyteller_prompt)
        except Exception as ex:
            scene = config.error_img
            response = config.error_narrator.format(ex=ex)
            _logger.error(f'ERROR NARRATING SCENE: {ex}\n{message}\n{history}')
            return scene, response, history, message
        # 更新历史记录。
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response.model_dump_json()})
        # 画场景。
        if config.draw_func:
            _logger.info(f'DRAWING SCENE...')
            try:
                scene_data = {'scene_description': response.scene_description,
                              'scene_style': config.scene_style}
                scene_prompt = config.scene_prompt.format(**scene_data)
                _logger.info(f'PROMPT BODY IS: \n\n{scene_prompt}\n')
                _logger.info(f'PROMPT LENGTH IS: {len(scene_prompt)}')
                scene = config.draw_func(scene_prompt)
            except Exception as ex:
                scene = config.error_img
                response = config.error_illustrator.format(ex=ex)
                _logger.warning(f'ERROR DRAWING SCENE: {ex}')
                return scene, response, history, ''
        else:
            _logger.info(f'DRAWING DISABLED...')
            scene = config.disable_img
        return scene, response, history, ''
    return gameplay_function


_logger = getLogger(__name__)
