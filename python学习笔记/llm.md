# LLM 学习笔记

> 本篇收录课程中的大模型概念（Prompt、Tools、RAG、微调、Agent 等）。  
> Python / JS 语法对照见 [`基础语法.md`](基础语法.md)；Gradio 见 [`Gradio.md`](Gradio.md)。

---

## Tools（工具调用）— 航空助手查票价

> 来源：`week2/day4_zh.ipynb`

### 一句话

Tools = **你写本地函数** + **用 JSON schema 告诉模型** + **模型决定要不要调** + **你执行并把结果塞回对话**。  
模型不会真的查票价；它只会发出「请调用某某函数」的请求。

### 流水线

1. 写本地函数，例如 `get_ticket_price(destination_city)`
2. 写 `price_function` 说明书（name / description / parameters）
3. `tools = [{"type": "function", "function": price_function}]`
4. `chat.completions.create(..., tools=tools)`
5. 若 `finish_reason == "tool_calls"` → `handle_tool_call(s)` 执行本地函数
6. 把 assistant 的 tool 请求 + `role: "tool"` 的结果追加进 `messages`
7. 再调一次模型，得到给用户的自然语言回答

```text
用户提问
  → API（带 tools）
  → 模型：finish_reason=tool_calls + 参数 JSON
  → 你的 Python：真正执行 get_ticket_price
  → 再 API（带 tool 结果）
  → 模型：最终口语回答
  → Gradio 显示
```

### Schema：给模型看的说明书

```python
price_function = {
    "name": "get_ticket_price",
    "description": "根据城市返回机票的价格",  # 函数级：什么时候用
    "parameters": {
        "type": "object",
        "properties": {
            "destination_city": {
                "type": "string",
                "description": "顾客想去的目的地城市",  # 参数级：怎么填
            },
        },
        "required": ["destination_city"],
        "additionalProperties": False,
    },
}
tools = [{"type": "function", "function": price_function}]
```

| 字段 | 作用 |
|------|------|
| `name` | 要调的函数名 |
| `description`（函数） | 整工具干什么，帮模型决定「要不要调」 |
| `parameters` + 参数 `description` | 帮模型填对参数 |
| `required` | 哪些参数必填 |

说明写清楚，填参更稳；写糊了容易填错或漏参。

### `handle_tool_call` 要点

```python
arguments = json.loads(tool_call.function.arguments)  # 模型给的是 JSON 字符串
city = arguments.get("destination_city")
price_details = get_ticket_price(city)
return {
    "role": "tool",
    "content": price_details,
    "tool_call_id": tool_call.id,  # 必须对上，模型才知道对应哪次调用
}
```

### 笔记本里的三档升级

| 阶段 | 做法 |
|------|------|
| 入门 | 只处理 `tool_calls[0]` |
| 改进 | `handle_tool_calls` 循环，一次多个工具 |
| 再改进 | `while finish_reason == "tool_calls"`，多轮工具 |

后面把字典换成 SQLite 时，**schema / chat 循环可不变**，只换 `get_ticket_price` 内部——接口稳定，后端可换。

### 小练习

1. 问「去北京多少钱」，终端是否出现 `Tool called...`？
2. 问字典里没有的城市，默认返回是什么？
3. `print(response.choices[0])`，指出 `tool_calls` 里的 `name` 和 `arguments`。
