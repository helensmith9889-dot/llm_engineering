# 决策分析 Web 应用

基于贝叶斯网络（Bayesian Network）的决策分析 Streamlit 应用。

## 开发者

由 **Sina Bahrami** 创建并维护。

## 许可证

本项目以 **Business Source License 1.1 (BSL 1.1)** 发布。
- **变更日期（Change Date）：** 2027-12-31 — 届时许可证自动转为 MIT。
- **未来许可证（Change License）：** MIT。

## 如何运行
1. 创建 `.env`，写入 OpenAI 及其他 LLM 的 API Key（可在 `config.py` 的 `APP_CONFIG` 中改用其他 API）
2. 用 `python -m venv venv` 创建虚拟环境并激活
3. 用 `pip install -r requirements.txt` 安装依赖
4. 运行：`streamlit run app.py`

## 完整版
完整代码请访问 GitHub 仓库：
[https://github.com/sbahrami/bn_decision_maker](https://github.com/sbahrami/bn_decision_maker)
