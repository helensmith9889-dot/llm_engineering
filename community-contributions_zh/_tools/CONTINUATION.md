# 教学注释续跑说明

## 现状

- 标准：[`teaching_annotate_STYLE.md`](teaching_annotate_STYLE.md)
- 进度：[`teaching_annotate_progress.json`](teaching_annotate_progress.json)
- 清单：[`teaching_annotate_inventory.json`](teaching_annotate_inventory.json)
- 样板：`../abdoul/第1周练习.ipynb`
- 工具：`next_wave.py`（分配）、`merge_wave.py`（合并结果）

## 本会话已完成波次

见 `batch_results/wave*_agent*.json`。进度以 `teaching_annotate_progress.json` 的 `counts` 为准。

最近合并：`wave1`–`wave4`。下一波从 `wave5` 起：`python3 next_wave.py 4 wave5`。  
（另：已剔除 32 本官方 day 高重合翻版，状态为 `skipped`；精选见 `../优质练习/`。）

## 下一会话怎么续

在 Cursor 主会话执行：

1. 读 STYLE + progress，确认 `pending` 数量
2. `python3 community-contributions_zh/_tools/next_wave.py 4 waveN`（N 递增）
3. 对 `waveN_batches.json` 里 4 个 batch 各开一个 Task agent（指令同 STYLE，禁止改 outputs，结果写到 `batch_results/waveN_agentK.json`）
4. 等 4 个结果齐：`python3 merge_wave.py waveN`
5. 抽检 1 本/agent，再重复 2–4

顺序：week1 → week8 → 未分类（已由 progress.order 固定）。

## 硬规则提醒

- 只改 `source`，不清空 `outputs` / `execution_count`
- 可运行英文保留；教学说明与注释用中文
- 子 agent **不要**并发写 `progress.json`，由主会话 `merge_wave.py` 合并



## 进度快照（自动）

`{"done": 423, "pending": 0, "in_progress": 0, "failed": 0, "skipped": 35, "total": 458}`

- **教学注释队列已清空**（`pending=0`）
- **优质练习：25/25 已注释**
- 已合并波次：`wave1`–`wave36`、`waveQ1`–`waveQ3`
- `skipped=35`：32 官方 lab 翻版 + 3 空文件（`nate-lev/week1/第2天作业.ipynb`、`ndahan/网页摘要.ipynb`、`victorConqueror/.../03_QLoRA训练.ipynb`）
- `merge_wave.py` 支持 basename / ROOT 绝对路径消解
- 续跑仅需处理新增 community notebook（重新 inventory / 入 progress）或抽检质量


