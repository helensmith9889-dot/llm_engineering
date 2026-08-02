"""AI 使用 OpenAI 的 GPT 掌握了《地下城提取》游戏故事讲述者。"""

from typing import List

from annotated_types import MaxLen
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

from .tools import handle_tool_call, tools


# 环境初始化。
load_dotenv(override=True)

# 定义全局变量。
MODEL = 'gpt-4o-mini'

# 客户端实例化。
CLIENT = OpenAI()


# 定义 Pydantic 模型类以进行响应格式解析。
class _character_sheet(BaseModel):
    health: int
    max_health: int
    level: int
    experience: int


class _response_format(BaseModel):
    game_over: bool
    scene_description: str = Field(..., max_length=700)
    dungeon_deepness: int
    adventure_time: int
    adventurer_status: _character_sheet
    inventory_status: List[str]

    def __str__(self):
        """将响应表示为字符串。"""
        response_view = (
            f'{self.scene_description}'
            f'\n\nInventory: {self.inventory_status}'
            f'\n\nAdventurer: {self.adventurer_status}'
            f'\n\nTime: {self.adventure_time}'
            f'\n\nDeepness: {self.dungeon_deepness}'
            f'\n\nGame Over: {self.game_over}')
        return response_view


def set_description_limit(limit):  # HBD: We modify the class definition in runtime.
    """更新“_response_format”类以设置新的“scene_description”最大长度。"""
    _response_format.model_fields['scene_description'].metadata[0] = MaxLen(limit)


# 函数定义。
def narrate(message, history, system_message, client=CLIENT, model=MODEL):
    """与游戏引擎聊天。"""
    messages = ([{"role": "system", "content": system_message}] + history
                + [{"role": "user", "content": message}])
    response = client.chat.completions.parse(model=model, messages=messages, tools=tools,
                                             response_format=_response_format)
    # 处理工具调用。
    if response.choices[0].finish_reason == "tool_calls":
        message = response.choices[0].message
        tool_response = handle_tool_call(message)
        messages.append(message)
        messages.append(tool_response)
        response = client.chat.completions.parse(model=model, messages=messages,
                                                 response_format=_response_format)
    # 返回游戏的Master响应。
    return response.choices[0].message.parsed
