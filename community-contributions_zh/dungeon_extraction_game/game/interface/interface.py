"""AI Mastered Dungeon Extraction Game Gradio 界面模块。"""

from typing import NamedTuple

import gradio as gr
from logging import getLogger


# 定义接口的配置类。
class Interface_Config(NamedTuple):
    """广播接口配置类。"""
    start_img: str
    place_img: str
    description_label: str
    title_label: str
    input_button: str
    input_label: str
    input_command: str
    game_over_field: str
    game_over_label: str
    start_scene: str


# 定义游戏的界面。
def get_interface(submit_function, config: Interface_Config):
    """创建游戏接口服务。"""
    with gr.Blocks(title=config.title_label) as ui:
        # 标题。
        gr.Markdown(config.title_label)
        # 历史的隐藏状态。
        history_state = gr.State([])
        # 场景图像。
        scene_image = gr.Image(
            label="Scene", value=config.start_img, placeholder=config.place_img,
            type="pil", show_label=False)
        # 场景描述。
        description_box = gr.Textbox(
            label=config.description_label, value=config.start_scene,
            interactive=False, show_copy_button=True)
        # 玩家的命令。
        user_input = gr.Textbox(
            label=config.input_label, placeholder=config.input_command)
        # 提交按钮。
        submit_btn = gr.Button(config.input_button)

        # 定义游戏结束控制。

        def _reset_game():
            """返回游戏重新启动的初始值。"""
            return (config.start_img, config.start_scene, [], '',
                    gr.update(interactive=True),
                    gr.update(value=config.input_button))

        def _game_over(scene, response):
            """返回游戏结束值，阻止输入字段。"""
            return (scene, response, [], config.game_over_field,
                    gr.update(interactive=False),
                    gr.update(value=config.game_over_label))

        def game_over_wrap(message, history, button_label):
            """在故事讲述者通话之前和之后检查游戏结束状态。"""
            # 之前检查游戏结束。
            print(button_label)
            print(config.game_over_label)
            if button_label == config.game_over_label:
                _logger.warning('GAME OVER STATUS. RESTARTING...')
                return _reset_game()
            # 打电话给讲故事的人。
            scene, response, history, input = submit_function(message, history)
            _logger.warning(response)
            # 检查游戏结束后。
            if response.game_over:
                _logger.info('GAME OVER AFTER MOVE. LOCKING.')
                return _game_over(scene, response)
            # 返回讲故事者的回应。
            return scene, response, history, input, gr.update(), gr.update()

        # 将函数分配给按钮单击事件。
        submit_btn.click(
            fn=game_over_wrap,
            inputs=[user_input, history_state, submit_btn],
            outputs=[scene_image, description_box, history_state, user_input,
                     user_input, submit_btn])
        # 将函数分配给输入提交事件。 （按输入键）
        user_input.submit(
            fn=game_over_wrap,
            inputs=[user_input, history_state, submit_btn],
            outputs=[scene_image, description_box, history_state, user_input,
                     user_input, submit_btn])

    return ui


_logger = getLogger(__name__)
