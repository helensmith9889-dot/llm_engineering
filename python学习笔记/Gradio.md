# Gradio — Interface 的 inputs / outputs

> 来源：`week2/day2_zh.ipynb` 里的 `shout` + `gr.Interface(...).launch()`  
> 相关 Python 基础：[`基础语法.md`](基础语法.md)（import、`def`）

## 这段代码在干什么？

先有一个普通函数，再让 Gradio 给它套一层网页界面：

```python
def shout(text):
    print(f"转大写 {text}")
    return text.upper()

gr.Interface(fn=shout, inputs="textbox", outputs="textbox", flagging_mode="never").launch()
```

- `gr.Interface(...)`：搭好界面（还没真正开网页）
- `.launch()`：启动本地 Web 服务（常见地址如 `http://127.0.0.1:7860`）并打开演示页

---

## `inputs` 和 `outputs` 分别对应什么？

它们**不是**去读 `shout` 源码里的变量名，而是告诉 Gradio：界面上有什么控件，以及怎么和函数的**参数 / 返回值**对接。

| Gradio 参数 | 界面上是什么 | 接到函数的哪一边 |
|-------------|--------------|------------------|
| `inputs="textbox"` | 一个输入文本框 | 填进 `shout` 的**第一个参数** `text` |
| `outputs="textbox"` | 一个输出文本框 | 显示 `shout` 的**返回值** |
| `fn=shout` | （不是控件） | 用户点提交时要调用的函数 |
| `flagging_mode="never"` | 关掉「举报/标记」按钮 | 入门可先不管 |

`"textbox"` 只是组件类型名字（「用文本框」），不是变量名。

对应到函数：

```python
def shout(text):          # 参数 text  ←── 来自 inputs
    return text.upper()   # return 值  ──→ 送给 outputs
```

---

## 为什么可以「获取到」shout 的输入输出？

不是 `shout` 自己去读网页，而是 **Gradio 当中间人**：

1. 你把函数交给它：`fn=shout`
2. 用户点提交时，Gradio **替你调用** `shout(...)`
3. 调用时把输入框的值当作参数传进去
4. 调用完把 `return` 的结果填到输出框

所以 `shout` 仍然只是普通 Python 函数：收参数、`return` 结果。Gradio 负责「界面 ↔ 函数」的接线。

```
用户在输入框打字 "hello"
        ↓
Gradio 取出字符串
        ↓
调用 shout("hello")   ← 相当于帮你写了 shout(输入框的内容)
        ↓
拿到返回值 "HELLO"
        ↓
写进输出文本框
```

和 notebook 里直接写 `shout("hello")` 的差别：

- **直接调用**：只有你自己在代码里试，没有界面
- **`Interface(...).launch()`**：多了一个浏览器页面，在页面上输入、点按钮也能调同一个函数

---

## 对齐规则（以后多参数也适用）

- `inputs` 的数量 / 顺序 ≈ 函数**参数**的数量 / 顺序
- `outputs` 的数量 / 顺序 ≈ **返回值**的数量 / 顺序

例如：

```python
def add(a, b):
    return a + b

gr.Interface(fn=add, inputs=["number", "number"], outputs="number")
```

两个输入框 → `a`、`b`；一个输出框 ← `return`。  
`shout` 只有一个参数、一个返回值，所以 `inputs` / `outputs` 各写一个 `"textbox"` 就对齐了。

---

## 进阶：用 `gr.Textbox(...)` 自定义控件

字符串 `"textbox"` 够用，但想改标签、行数时，要先建组件，再传给 `inputs` / `outputs`：

```python
message_input = gr.Textbox(label="Your message:", info="Enter a message to be shouted", lines=7)
message_output = gr.Textbox(label="Response:", lines=8)

view = gr.Interface(
    fn=shout,
    inputs=[message_input],
    outputs=[message_output],
    flagging_mode="never"
)
view.launch()
```

| 写法 | 含义 |
|------|------|
| `inputs="textbox"` | 快捷写法：默认样式的文本框 |
| `inputs=[message_input]` | 用你配置好的 `gr.Textbox` 对象 |

`message_output = gr.Textbox(label="Response:", lines=8)` 的意思：

- 创建一个**输出用**文本框
- `label="Response:"`：框上方显示的标题
- `lines=8`：显示高度约 8 行（方便看长回复）

接线逻辑不变：函数 `return` 的字符串 → 显示在 `message_output` 里。

---

## 小练习（加深理解）

1. 若写成 `gr.Interface(fn=shout, inputs="textbox", outputs="textbox")` 但不写 `.launch()`，界面会出现吗？
2. 把 `shout` 改成两个参数（例如 `def shout(text, suffix):`），`inputs` 要怎么改才不会对不上？
3. `inputs="textbox"` 里的 `"textbox"` 必须和参数名 `text` 一样吗？为什么？
4. `message_output = gr.Textbox(...)` 之后，为什么还要写进 `outputs=[message_output]`？只创建变量够不够？

---

# 流式输出：`stream=True` 与 `yield`

> 来源：`week2/day2_zh.ipynb` 里的 `stream_gpt`  
> 想系统复习生成器：课程 `guides/` 里的 Intermediate Python（`yield`）

## 这段代码在干什么？

不要等模型整段说完再显示，而是**边生成边吐字**：

```python
def stream_gpt(prompt):
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
    ]
    # 开启 stream=True：模型一边生成，一边把增量文本推过来
    stream = openai.chat.completions.create(
        model='qwen3:8b',
        messages=messages,
        stream=True
    )
    result = ""
    # 按流式 chunk 拼接；delta.content 是本次新增的一小段字
    for chunk in stream:
        result += chunk.choices[0].delta.content or ""
        yield result
```

流程：

```
用户 prompt
    → 调 API（stream=True）
    → 一次次收到小片段 chunk
    → 拼进 result
    → 每拼一次就 yield 一次「当前完整结果」
    → Gradio 每次收到就刷新输出框 → 像打字机
```

---

## `stream=True`：流式输出

### 不开流式（默认）

```python
response = openai.chat.completions.create(..., stream=False)  # 或不写
text = response.choices[0].message.content
```

- 等模型**全部生成完**才返回
- 拿到一整段字符串
- 界面往往「卡住 → 突然整段出现」

### 开流式

```python
stream = openai.chat.completions.create(..., stream=True)
```

- API **不会**一次性返回整段话
- 返回一个**可迭代对象**：可用 `for chunk in stream` 一块块拿
- 每一块叫 **chunk（数据块）**，通常只带**新增**的几个字

| 模式 | 像什么 |
|------|--------|
| 非流式 | 等快递整箱到了再拆 |
| 流式 | 一页一页传真过来，边收边读 |

变量名 `stream` =「一条正在流动的回复流」，不是最终那一个字符串。

---

## `chunk` 和 `delta.content`

```python
for chunk in stream:
    result += chunk.choices[0].delta.content or ""
```

| 部分 | 含义 |
|------|------|
| `chunk` | 这一次推过来的一小包数据 |
| `chunk.choices[0]` | 第一个候选回复（一般只用这个） |
| `.delta` | **增量**：相对上一包，**新多出来**的部分 |
| `.delta.content` | 增量里的文字；有时是 `None`（例如结束信号） |
| `or ""` | 若是 `None`，当成空字符串，避免 `+= None` 报错 |

假设最终要说 `你好世界`，流可能像：

```
chunk1: "你"
chunk2: "好"
chunk3: "世"
chunk4: "界"
```

`result` 依次变成：`"你"` → `"你好"` → `"你好世"` → `"你好世界"`。

注意：`delta.content` 是**新增片段**；`result` 才是**从开头到现在的全文**。

---

## `yield`：生成器（和 `return` 对比）

### 普通函数 + `return`

```python
def message_gpt(prompt):
    ...
    return 整段文字   # 函数到此结束，只交一次结果
```

调用一次 → 拿回**一个**值 → 函数结束。

### 带 `yield` 的函数 = 生成器函数

```python
yield result
```

含义不是「结束并只返回一次」，而是：

1. **暂停**函数，把当前的 `result` 交出去
2. 外面用完这一份后，函数从暂停处**继续跑**
3. 再 `yield` 下一次……直到 `for` 循环结束

所以 `stream_gpt` 被调用一次，却会**连续交出很多个**越来越长的字符串：

```
第 1 次 yield → "你"
第 2 次 yield → "你好"
第 3 次 yield → "你好世"
第 4 次 yield → "你好世界"
```

### 为什么 Gradio 需要 `yield`？

- 你每 `yield` 一次，Gradio 就用最新值**刷新输出框**
- 若只用 `return`，通常只能在全部结束后更新一次，看不到「打字」效果

`stream=True` = 从 API 一块块收；`yield` = 一块块交给界面。两件事配合才完整。

---

## 为什么要先 `result = ""` 再累加？

```python
result = ""
for chunk in stream:
    result += chunk.choices[0].delta.content or ""
    yield result   # 每次交出「目前为止的全部」
```

也可以每次只 `yield` 增量，但 Gradio `Interface` 常见用法是：**每次 yield 完整当前文本**，输出框始终显示全文，不会只显示最后几个字。

---

## 一张图串起来

```
prompt
  │
  ▼
API (stream=True) ──► chunk1 "你" ──► result="你"      ──yield──► 界面显示「你」
                  ──► chunk2 "好" ──► result="你好"    ──yield──► 界面显示「你好」
                  ──► chunk3 "世" ──► result="你好世"  ──yield──► …
                  ──► chunk4 "界" ──► result="你好世界"──yield──► 最终全文
```

---

## 和 `message_gpt`（同步）对比

| | `message_gpt`（同步） | `stream_gpt`（流式） |
|--|--|--|
| API | 默认 / `stream=False` | `stream=True` |
| 拿到什么 | 一次拿到整段 `message.content` | 循环拿 `delta.content` |
| 交结果 | `return` 一次 | 多次 `yield` |
| 界面感觉 | 等一会，整段出现 | 像打字机逐字出现 |

---

## 小练习（流式 / yield）

1. 若把 `yield result` 改成 `return result`，循环还能跑几圈？界面还像打字机吗？
2. 若改成 `yield chunk.choices[0].delta.content or ""`（只 yield 增量），输出框可能出现什么奇怪现象？
3. `or ""` 去掉后，某一包 `delta.content` 为 `None` 时会怎样？

---

# ChatInterface：多轮聊天回调 `chat(message, history)`

> 来源：`week2/day3_zh.ipynb`  
> 列表推导式 / `h` 的 Python 语法见：[`基础语法.md`](基础语法.md)（「列表推导式」一节）

## 这段代码在干什么？

```python
def chat(message, history):
    history = [{"role": h["role"], "content": h["content"]} for h in history]
    messages = [{"role": "system", "content": system_message}] + history + [{"role": "user", "content": message}]
    response = openai.chat.completions.create(model=MODEL, messages=messages)
    return response.choices[0].message.content
```

挂到界面上：

```python
gr.ChatInterface(fn=chat, type="messages").launch()
```

用户发一条新消息时，Gradio 调用 `chat(...)`；你 `return` 的字符串就是助手回复。

---

## 两个参数分别是什么？

| 参数 | 含义 |
|------|------|
| `message` | **刚发来的这一句**用户输入（字符串） |
| `history` | **之前的对话列表**（不含当前这句；由 Gradio 维护并传入） |

`type="messages"` 时，`history` 大致长这样：

```python
[
  {"role": "user", "content": "你好"},
  {"role": "assistant", "content": "你好！有什么可以帮你？"},
  {"role": "user", "content": "今天星期几？"},
  {"role": "assistant", "content": "今天是……"},
]
```

---

## 为什么要整理 `history`？

```python
history = [{"role": h["role"], "content": h["content"]} for h in history]
```

Gradio 传来的字典里有时还带别的字段；OpenAI 的 `messages` 通常只要 `role` + `content`。  
这一行是在 **清洗**：只保留需要的两键，避免多余字段进 API。

（`h` 是循环变量 = 历史里的一条消息，详见基础语法笔记。）

---

## 拼完整 `messages`

```python
messages = [{"role": "system", "content": system_message}] + history + [{"role": "user", "content": message}]
```

| 部分 | 作用 |
|------|------|
| system | 人设 / 规则（如「必须中文回答」） |
| `history` | 以前的 user/assistant 来回（模型才能「记得」上文） |
| 当前 `message` | 用户刚说的这句 |

```
[system] + [旧 user, 旧 assistant, ...] + [当前 user]
```

---

## 和 day2 `Interface` 的差别

| | day2 `Interface` | day3 `ChatInterface` |
|--|--|--|
| 场景 | 单次 prompt / 工具型页面 | 多轮聊天 |
| 历史 | 一般不带 | 用 `history` 传入 |
| 回调形态 | `fn(输入...)` | `chat(message, history)` |

---

## 小练习（ChatInterface）

1. 若不把 `history` 拼进 `messages`，连问两句「我叫小明」「我叫什么？」，模型容易怎样？
2. 当前这句为什么单独用 `message`，而不已经在 `history` 里？
3. `return` 的必须是字符串吗？若 `return` 整个 `response` 对象，界面会怎样？
