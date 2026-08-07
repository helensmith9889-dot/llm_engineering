# 教学注释标准（Teaching Annotate）

样板：`abdoul/第1周练习.ipynb`（对照官方 `week1/day1_zh.ipynb`）

## 硬规则

1. **只改** notebook 单元格的 `source`（markdown / code）。
2. **禁止**清空或改写：`outputs`、`execution_count`、cell `metadata`、notebook 顶层 metadata（除非修损坏 JSON）。
3. **禁止**改可执行逻辑：控制流、API 调用参数、变量名、函数名保持原样。
4. **可运行英文必须保留**：
   - 标识符、库名、方法名（`OpenAI`、`load_dotenv`、`MODEL_GPT`…）
   - 影响行为的字符串：prompt、model id、URL、路径、依赖程序判断的错误文案
5. **给人看的英文要中文化**：
   - Markdown 单元格（理念、步骤、说明）→ 简体中文教学向
   - 代码里旧的浅注 `# 【注】...` / 英文注释 → 改成中文教学旁注
6. **注释密度**：几乎每个有意义的语句上一行都有中文说明（讲「是什么 / 为什么」），可夹带英文术语对照（如 Environment Variables）。不要只在单元格顶写一句「逻辑保持原样」。
7. **不强制跑 API**；改完用语法/AST 校验即可。

## 推荐写法

```python
# 从 dotenv 导入 load_dotenv：把 .env 里的密钥读进环境变量，避免把密钥写进代码
from dotenv import load_dotenv

# 加载 .env（override 视原代码而定，不要擅自加减参数）
load_dotenv()
```

Markdown 可补：练习目标、和本课哪一周概念相关、怎么跑——须全中文。

## 禁止

- `outputs = []` / 删除 `display_data` / 重置 `execution_count` 来「清理笔记本」
- 翻译 system/user prompt 字符串
- 重命名变量「为了更中文」
- 改写算法或「顺手重构」

## 完成后自检

- [ ] 每个分配文件的 `outputs` 条数与改前一致
- [ ] 代码格中文 `#` 注释明显增加，且逐行级
- [ ] Markdown 无大段未译英文说明（专有名词可保留）
- [ ] `ast.parse` 代码可通过；逻辑与改前一致（去掉注释/教学 docstring 后对比）
