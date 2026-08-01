# LLM Engineering - Master AI and LLMs

## 开启你为期 8 周的精通之旅

![Voyage](assets/core.jpg)

_如果你是在 Cursor 中查看本文件，请在左侧资源管理器中右键点击文件名，选择「Open preview」，即可查看格式化后的版本。_

很高兴你加入这条学习之路。接下来几周，我们会一起做出特别有成就感的项目。有的简单，有的有挑战，很多会让你大吃一惊！项目彼此递进，每周你会积累越来越深的专业能力。有一点可以肯定：一路上你会玩得很开心。

有任何问题，请在 Udemy 上问我，或发邮件到 ed@edwarddonner.com。更多详情见课程资源页顶部 [这里](https://edwarddonner.com/2024/11/13/llm-engineering-resources/)。

### 常见问题解答

[我的 Cursor 界面和你的不一样（新启动屏）](https://edwarddonner.com/avatar?q=54)  
[我能用 Gemini 或免费模型代替 OpenAI 吗？可以！](https://edwarddonner.com/avatar?q=8)  
[课程资源在哪里](https://edwarddonner.com/2024/11/13/llm-engineering-resources/)   
[这门课和你其他课程的关系？](https://edwarddonner.com/curriculum)  
[没有编程基础可以学这门课吗？](https://edwarddonner.com/avatar?q=2)  
[学完这门课能找到什么工作？](https://edwarddonner.com/avatar?q=3)  

### 开始之前

我在这里，就是为了帮你把学习效果做到最好。如果遇到任何问题，或者有改进课程的想法，请务必在平台上联系我，或直接发邮件给我（ed@edwarddonner.com）。在 LinkedIn 上认识大家、一起建设社区总是很棒的——你可以在这里找到我：  
https://www.linkedin.com/in/eddonner/   

我也在搭建一个 YouTube 频道，放一些额外内容——欢迎 [来这里看看](https://youtube.com/@edward.donner)。  
这对我来说还挺新鲜的，我也在尝试 X/Twitter：[@edwarddonner](https://x.com/edwarddonner)——如果你也在用 X，请教教我怎么玩 😂  

配合课程的资源（包括幻灯片和实用链接）在这里：  
https://edwarddonner.com/2024/11/13/llm-engineering-resources/

我的数字分身可以回答常见 FAQ（也能把我叫进来！）：  
https://edwarddonner.com/avatar/

## 第 1 周第 1 天「即时满足」指南——用 Llama 3.2，**不是** Llama 3.3

### 重要提示：请看下面关于 Llama3.3 的警告——它对家用电脑来说太大了！请坚持用 llama3.2——已有不少同学忽略了这条警告……

我们会用安装 Ollama 来开启课程，这样你能立刻看到效果！
1. 从 https://ollama.com 下载并安装 Ollama；注意在 PC 上，安装可能需要管理员权限才能正常完成
2. 在 PC 上，打开 Command prompt / Powershell（按 Win + R，输入 `cmd`，然后按 Enter）。在 Mac 上，打开 Terminal（Applications > Utilities > Terminal）。
3. 运行 `ollama run llama3.2`；机器配置较小时可试 `ollama run llama3.2:1b`——**请注意**，避开 Meta 最新的模型 llama3.3，因为它有 70B 参数，对大多数家用电脑来说实在太大了！  
4. 如果不行：你可能需要在另一个 Powershell（Windows）或 Terminal（Mac）里运行 `ollama serve`，然后再试第 3 步。在 PC 上，你可能需要在管理员权限的 Powershell 中运行。  
5. 如果在你的机器上还是不行，我已经在云端准备好了方案。这是 Google Colab，需要 Google 账号登录，但是免费的：  https://colab.research.google.com/drive/1-_f5XZPsChvfU1sJ0QqCePtIuc55LSdu?usp=sharing

有任何问题，请联系我！

## 进入安装说明之前——特别说明

课程很早（第 2 天），我会演示一款很酷、很受欢迎的产品：Claude Code。它是一款 AI 编程工具，和我们课程里用的 Cursor 类似。我只是把它当作 Agentic AI 实战的例子；它并不是本课程明确覆盖的工具，尤其是我们本来就在用 Cursor。但如果你想自己用 Claude Code，Anthropic 的 Quick Start 指南在 [这里](https://docs.claude.com/en/docs/claude-code/quickstart)。

## 好——现在进入安装说明

在做完 Ollama 快速项目、以及我自我介绍和课程介绍之后，我们就会开始完整环境的搭建。  

希望这些指南足够「防弹」——但如果遇到卡点，请立刻联系我：

安装说明（中文）：[Setup Instructions All Platforms](setup/SETUP-new_zh.md)  
英文原版对照：[setup/SETUP-new.md](setup/SETUP-new.md)

中文学习计划（按周怎么学、打开哪些 `*_zh` 文件）：[小白向 8 周学习计划（中文材料版）.md](小白向%208%20周学习计划（中文材料版）.md)

### 关于 API 费用的重要说明（可选！不想花钱完全可以不花）

课程中，我会建议你试用处于进步前沿的领先模型，也就是所谓的 Frontier 模型。我也会建议你用 Google Colab 运行开源模型。这些服务有一定费用，但我会把成本压得很低——通常一次就几美分。如果你不想用，我也会提供替代方案。

请务必监控你的 API 用量，确保花费在你舒适的范围内；下面有相关链接。整门课通常只需要花几美元就够了。有些 AI 提供商（如 OpenAI）要求最低充值，比如 \$5 或等值本币；我们实际只会花其中一小部分，而且你会有大量机会把余额用在自己的项目里。第 7 周如果你玩得开心，可以选择多花一点——我自己大概花了 \$10，结果让我非常满意！但这完全不是必须的；最重要的是专注学习。

### 付费 API 的免费替代方案

详细做法（含 Ollama、Gemini、OpenRouter 等的完整代码）见 guides 目录中的 [Guide 9](guides/09_ai_apis_and_ollama_zh.ipynb)（英文原版：[09_ai_apis_and_ollama.ipynb](guides/09_ai_apis_and_ollama.ipynb)）！

### 本仓库的组织结构

每个「周」（`week1`–`week8`）都有对应文件夹，代表课程模块，最终在第 8 周汇聚成一个强大的自主 Agentic AI 方案，并大量用到前几周的内容。  
按上面的安装说明完成后，打开 Week 1 文件夹，准备迎接快乐吧。

**中文材料怎么找：** 同目录下带 `_zh` 后缀的就是中文版，例如 `day1_zh.ipynb`、`SETUP-new_zh.md`。英文原版仍保留，方便对照。学习时请优先打开 `*_zh` 文件。

下面两个目录**不是** 8 周主课必做内容，初学可以先跳过：

#### `community-contributions/`（以及各周下的同名文件夹）

**同学作业 / 社区贡献展示区。**  
里面是大量学员按周练习、自己项目交上来的成果（各种 notebook、小应用、RAG demo 等）。  

- 用来看别人怎么做、找灵感、对照作业  
- **不是**官方 week1–8 主线教材  
- 主课做完再有空翻着玩即可  

#### `extras/`

**官方额外加餐项目**，不算 8 周主进度。例如：  

- `extras/trading/`：用微调做「交易代码生成」原型（建议 Week 7 之后再看；**不要**当真用于炒股）  
- `extras/community/`：其他扩展示例  

讲解相对少、偏自学拓展；主课跑通后再碰更合适。

**建议优先级：** `setup` + `week1`–`week8`（用 `*_zh`）→ 可选 `guides/` → 有余力再看 `extras/` → 想找灵感再逛 `community-contributions/`。

### 最重要的部分

本课程的口号是：最好的学习方式就是 **动手做（DOING）**。课上我不会把所有代码都亲手敲一遍；我会执行它们，让你看到结果。你应该跟着我一起做，或在每节课后自己跑每个单元格，检查对象，深入理解发生了什么。然后改代码，把它变成你自己的。课程里处处都有精彩的挑战。如果你愿意为自己的代码提交 Pull Request（见 guides 文件夹里的 Github 指南），我会非常高兴——我可以把你的方案分享给其他人，一起见证你的进步；额外好处是，你会因对仓库的贡献而在 GitHub 上被认可。项目固然有趣，但首要目标是 _教育性_：教你能在工作中真正落地的业务技能。

## 从第 3 周开始，我们还会用 Google Colab 来跑 GPU

你应该可以用免费档或极少花费完成课上所有项目。我个人订阅了 Colab Pro+，用得很开心——但不是必须的。

了解 Google Colab，并设置 Google 账号（如果还没有）见 [这里](https://colab.research.google.com/)

Colab 链接在 Week 3 和 Week 7 的文件夹里——打开每天的 lab，你会找到直达 Colab 的链接。

### 监控 API 费用

整门课你都可以把 API 花费压得很低；可在这些控制台监控用量：OpenAI 见 [这里](https://platform.openai.com/usage)，Anthropic 见 [这里](https://console.anthropic.com/settings/cost)。

本课程练习的费用通常都很低；如果想尽量少花，请务必始终选择最便宜的模型版本：
1. 对于 OpenAI：代码里始终使用模型 `gpt-4.1-nano`
2. 对于 Anthropic：代码里始终使用模型 `claude-3-haiku-20240307`，而不是其他 Claude 模型
3. 第 7 周时，留意我关于使用更便宜数据集的说明

如果这些行不通，或我能帮上什么忙，请务必私信我或发邮件到 ed@edwarddonner.com。我迫不及待想听你学得怎么样了。

<table style="margin: 0; text-align: left;">
    <tr>
        <td style="width: 150px; height: 150px; vertical-align: middle;">
            <img src="assets/resources.jpg" width="150" height="150" style="display: block;" />
        </td>
        <td>
            <h2 style="color:#f71;">其他资源</h2>
            <span style="color:#f71;">我整理了这个网页，放了课程相关的实用资源，包括所有幻灯片的链接。<br/>
            <a href="https://edwarddonner.com/2024/11/13/llm-engineering-resources/">https://edwarddonner.com/2024/11/13/llm-engineering-resources/</a><br/>
            请收藏这个页面，我会持续往里面加更多有用的链接。
            </span>
        </td>
    </tr>
</table>
