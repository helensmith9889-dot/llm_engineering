# HackTrack – AI 驱动的黑客松发现平台

## 背景

HackTrack 最初是 AI Engineer Core Track 课程第 1 周「网页抓取 + 本地 LLM」练习的延伸。

最初目标是：抓取网站信息，并用本地 LLM 生成摘要。随着不断试验，项目逐渐发展成一个完整的 Flask Web 应用，用于发现和推荐黑客松（Hackathon）。

## 功能

* 从 Devpost 聚合黑客松信息
* 用 MySQL 存储数据（黑客松详情、用户兴趣等）
* 支持关键词搜索
* 可按领域筛选（网络安全、AI 等）
* 根据用户兴趣提供个性化推荐
* 通过 Ollama 本地托管的 Llama 3.2 模型生成 AI 洞察

## 技术栈

* Python
* Flask
* MySQL
* BeautifulSoup
* Ollama（Llama 3.2）
* HTML/CSS

## 我学到了什么

本项目帮助我获得了以下实践经验：

* 网页抓取与数据采集
* 数据库设计
* 推荐系统
* 本地 LLM 集成
* 全栈应用开发

## 代码仓库

GitHub：
https://github.com/Abhijith24001/HackTrack

## 未来改进

后续版本将从更多来源聚合黑客松，改进用户界面，并扩展推荐能力。
