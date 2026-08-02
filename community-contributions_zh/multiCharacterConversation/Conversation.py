"""中文注释版：逻辑与标识符保持原文，便于 import 与运行。"""
from dataclasses import dataclass
from tokenize import String
from typing import List, Optional
from openai import OpenAI

def noop(*args, **kwargs):
    pass

@dataclass
class ConversationMessage:
    """代表多方对话中的单个消息。"""
    speaker: str 
    content: str
    role: str = "user"


class Character:
    """代表对话中由法学硕士支持的角色。"""

    def __init__(
        self,
        name: str,
        system_prompt: str,
        client: OpenAI,
        model: str = "gpt-4.1-mini",
        emit=None
    ) -> None:
        """:param name：人类可读的角色名称（说话者标签）。
        :param system_prompt: 定义角色行为的系统提示。
        :param client: 初始化的 OpenAI 客户端实例。
        :param model: 该角色使用的模型名称。"""
        self.name = name
        self.system_prompt = system_prompt
        self.client = client
        self.model = model
        self.emit = emit or noop

    def _build_user_prompt(self, messages: List[ConversationMessage]) -> str:
        """将现有对话消息转换为单个用户提示
        清楚地识别谁说了什么。"""
        lines = []
        for msg in messages:
            lines.append(f"{msg.speaker}: {msg.content}")
        history_text = "\n".join(lines)

        prompt = (
            "Here is the conversation so far:\n\n"
            f"{history_text}\n\n"
            f"You are {self.name}. Reply with your next message in this conversation."
        )
        return prompt

    def respond(
        self,
        conversation_messages: List[ConversationMessage],
        conversation_system_prompt: Optional[str] = None,
    ) -> ConversationMessage:
        """根据到目前为止的整个对话，生成该角色的下一条消息。
        返回一个新的 ConversationMessage 实例。"""
        if conversation_system_prompt:
            system_content = (
                conversation_system_prompt.strip() + "\n\n" + self.system_prompt.strip()
            )
        else:
            system_content = self.system_prompt.strip()

        user_prompt = self._build_user_prompt(conversation_messages)

        self.emit(user_prompt)
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_prompt},
            ],
        )

        reply_text = completion.choices[0].message.content.strip()

        return ConversationMessage(
            speaker=self.name,
            content=reply_text,
            role="assistant",
        )


class Conversation:
    """管理多角色对话并进行循环轮流。"""

    def __init__(self, system_prompt: str, characters: List[Character], emit=None) -> None:
        """:param system_prompt: 描述整体对话上下文的系统提示。
        :param 字符：参与对话的字符实例列表。"""
        if not characters:
            raise ValueError("Conversation must be constructed with at least one Character.")

        self.system_prompt = system_prompt
        self.characters = characters
        self.messages: List[ConversationMessage] = []
        self._round_start_index = 0  # which character starts the next round
        self.emit = emit or noop 

    def add_message(
        self,
        speaker: str,
        content: str,
        role: str = "user",
    ):
        """将外部消息或初始消息添加到对话中。
        对于播种对话很有用。"""
        msg = ConversationMessage(speaker=speaker, content=content, role=role)
        self.messages.append(msg)  
        self.emit(f"message: {msg.content}")      

    def round(self) -> List[ConversationMessage]:
        """执行一轮对话。

        每个角色都只有一轮响应，按照循环顺序。
        在连续调用“round()”时，*起始*字符会旋转，
        所以每个人都有机会领导。

        返回本轮生成的新消息列表。"""
        new_messages: List[ConversationMessage] = []
        num_chars = len(self.characters)

        indices = [
            (self._round_start_index + offset) % num_chars
            for offset in range(num_chars)
        ]

        for idx in indices:
            character = self.characters[idx]
            reply = character.respond(
                conversation_messages=self.messages,
                conversation_system_prompt=self.system_prompt,
            )
            self.emit(f"response from {character.name}: {reply.content}")
            self.messages.append(reply)
            new_messages.append(reply)

        # 提前下一轮的起始指数
        self._round_start_index = (self._round_start_index + 1) % num_chars

        return new_messages
