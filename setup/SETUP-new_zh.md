# LLM Engineering - Master AI and LLMs

## PC、Mac 和 Linux 安装说明

_如果你是在 Cursor 中查看本文件，请在左侧资源管理器中右键点击文件名，选择「Open preview」，即可查看格式化后的版本。_

欢迎，正在成长中的 LLM engineers！

我得先坦白：搭建一套能站在 AI 前沿工作的强大环境，并不像我希望的那么简单。对大多数人来说，这些说明会很顺利；但有些情况下，不知什么原因，你会碰到问题。请不要犹豫，随时联系我——我在这里就是为了帮你尽快跑起来。没有什么比感觉 _卡住_ 更糟的了。在 Udemy 里给我留言，或发邮件给我，我会很快帮你解卡！

Email: ed@edwarddonner.com  
LinkedIn: https://www.linkedin.com/in/eddonner/  

## 中文学习路径小贴士（建议先看）

如果你打算跟着中文版材料学习，先记住这几条，能少踩不少坑：

1. **优先打开中文版文件**  
   同目录下带 `_zh` 后缀的就是中文版，例如 `*_zh.md`、`*_zh.ipynb`。英文原版仍然保留，方便对照。  
   在 Cursor 左侧资源管理器里点 notebook 时，请认准带 `_zh` 的文件名，不要误点成没有 `_zh` 的英文版（例如应打开 `day1_zh.ipynb`，而不是 `day1.ipynb`）。

2. **`.env` 与 `environment.yml` 分别是什么**  
   - **`.env`**：放 API Key 的本地配置文件（例如 `OPENAI_API_KEY=...`）。**不要**把它提交到 Git；后面第 4 步会详细教你怎么创建。  
   - **`environment.yml`**：conda 环境的依赖清单。按本说明里的 conda / uv 方式安装即可，一般**不用**手改这个文件。

3. **Week5 RAG 知识库（英文演示 vs 中文对照）**  
   `week5/knowledge-base/` 里，课程演示**默认加载英文** `.md` 文件。同目录也有 `*_zh.md` 中文译本，方便你阅读理解内容。  
   如果你改成加载中文文件，检索效果和练习答案可能与课程演示不一致。初学建议：**先跟英文知识库把流程跑通**，中文版当作对照阅读即可。

## 第 0 步——开始之前——先解决那些让很多人栽跟头的「GOTCHAS」：

忽略这一节风险自负！关于安装的问题里，有 80% 都能被这些非常常见的系统问题解释掉。

1. PC 用户：权限。请先看这篇关于 Windows 权限的 [教程](https://chatgpt.com/share/67b0ae58-d1a8-8012-82ca-74762b0408b0)。如果你遇到没有权限 / 许可 / 能力去运行脚本或安装软件的错误，请先读这篇。ChatGPT 可以告诉你关于 Windows Permissions 你需要知道的一切。

2. 杀毒软件、防火墙、VPN。它们可能干扰安装和网络访问；必要时可暂时禁用。用手机热点来验证是不是网络问题。

3. PC 用户：邪恶的 Windows 文件名 260 字符限制——这里有完整的 [解释和修复方法](https://chatgpt.com/share/67b0afb9-1b60-8012-a9f7-f968a5a910c7)！ 

4. PC 用户：如果你以前没在电脑上用过 Data Science 相关包，可能需要安装 Microsoft Build Tools。说明见 [这里](https://chatgpt.com/share/67b0b762-327c-8012-b809-b4ec3b9e7be0)。也有同学提到，[这些说明](https://github.com/bycloudai/InstallVSBuildToolsWindows) 对 Windows 11 用户可能有帮助。 

5. Mac 用户：如果你是第一次在 Mac 上开发，可能需要安装 XCode developer tools。说明见 [这里](https://chatgpt.com/share/67b0b8d7-8eec-8012-9a37-6973b9db11f5)。

6. 公司安全策略导致的 SSL 及其他网络问题：如果你遇到 SSL 问题（比如 API Connection 问题、证书问题），或从 Ollama 下载文件时报错（Cloudflare 错误），请看 [这里](https://edwarddonner.com/faq) 的 Q15

## 第 1 步——安装 git、创建 projects 目录、安装 Cursor

这是唯一需要 PC 用户和 Mac/Linux 用户分开操作的部分！请选择下面对应的小节，然后在第 2 步会合……

___

**第 1 步——PC 用户：**

1. **安装 Git**（如果还没装）：

- 打开一个新的 Powershell Prompt（开始菜单 >> Powershell）。如果遇到权限错误，可尝试右键点击并选择「以管理员身份运行」打开 Powershell
- 运行命令 `git`，看它是返回命令说明，还是报错
- 如果报错，从 https://git-scm.com/download/win 下载 Git
- 运行安装程序并按提示操作，使用默认选项（多按几次 OK！）

2. **按需创建 projects 目录**

- 像上一步一样打开一个新的 Powershell。你应该在主目录里，类似 `C:\Users\YourUserName`
- 你有 projects 目录吗？输入 `cd projects` 看看
- 如果报错，就创建一个：`mkdir projects`，然后 `cd projects`
- 现在你应该在 `C:\Users\YourUserName\projects`
- 你也可以放在任何方便的位置，但请避开 OneDrive 上的目录

3. **执行 git clone：**

在 `projects` 文件夹的命令提示符中输入下面的 clone 命令。如果提示长文件名错误，请先做本文顶部「gotchas」部分的第 3 条，然后重启电脑；你可能还需要运行：`git config --system core.longpaths true`

clone 命令如下：

`git clone https://github.com/ed-donner/llm_engineering.git`

这会在你的 projects 文件夹里创建一个新的 `llm_engineering` 目录，并下载课程代码。  
执行 `cd llm_engineering` 进入该目录。这个 `llm_engineering` 目录就是所谓的「项目根目录」（project root directory）。

4. **Cursor** 按需安装 Cursor 并打开项目：

访问 https://cursor.com

点击 Download for Windows。然后运行安装程序。全部接受并选默认选项即可。

然后到开始菜单，输入 cursor。Cursor 会启动，你可能需要回答一些问题。然后你应该会看到「new window」界面，可以点击「Open Project」。如果没有，到 File 菜单 >> New Window，再点击「Open Project」。

[重要：你的 Cursor 界面和我的不一样？解决方案在这里（绕过新启动屏）](https://edwarddonner.com/avatar?q=54)  

在你的 projects 目录中找到 llm_engineering 目录。双击 llm_engineering，直到你看到它的内容。然后点击 Open 或 Open Folder。

Cursor 随后应打开 llm_engineering。如果你在左上角看到大写的 LLM_ENGINEERING，就说明状态很好。

___

**第 1 步——MAC/LINUX 用户**

1. **安装 Git**（如果还没装）：

打开 Terminal：在 Mac 上，打开 Finder，进入 Applications >> Utilities >> Terminal。在 Linux 上，你们本来就生活在 Terminal 里……几乎不需要我教！

- 运行 `git --version`，你应该能看到 git 版本号。如果没有，系统通常会提示如何安装，或者按本文顶部的 gotcha #5 操作。

2.  **按需创建 projects 目录**

- 像上一步一样打开一个新的 Terminal。输入 `pwd` 查看当前位置。你应该在主目录里，类似 `/Users/username`
- 你有 projects 目录吗？输入 `cd projects` 看看
- 如果报错，就创建一个：`mkdir projects`，然后 `cd projects`
- 如果现在再执行 `pwd`，你应该在 `/Users/username/projects`
- 你也可以放在任何方便的位置，但请避开 iCloud 上的目录

3. **执行 git clone：**

在 Projects 文件夹的命令提示符中输入：

`git clone https://github.com/ed-donner/llm_engineering.git`

这会在你的 projects 文件夹里创建一个新的 `llm_engineering` 目录，并下载课程代码。  
执行 `cd llm_engineering` 进入该目录。这个 `llm_engineering` 目录就是所谓的「项目根目录」（project root directory）。

4. **Cursor** 按需安装 Cursor 并打开项目：

访问 https://cursor.com

点击 Download for Mac OS。或 Linux。然后运行安装程序。全部接受并选默认选项即可。

然后到开始菜单，输入 cursor。Cursor 会启动，你可能需要回答一些问题。然后你应该会看到「new window」界面，可以点击「Open Project」。如果没有，到 File 菜单 >> New Window，再点击「Open Project」。

[重要：你的 Cursor 界面和我的不一样？解决方案在这里（绕过新启动屏）](https://edwarddonner.com/avatar?q=54)  

在你的 projects 目录中找到 llm_engineering 目录。双击 llm_engineering，直到你看到它的内容。然后点击 Open。

Cursor 随后应打开 llm_engineering。如果你在左上角看到大写的 LLM_ENGINEERING，就说明状态很好。

___

## 第 2 步：安装超棒的 **uv**，然后执行 `uv sync`

本课程我们使用 uv——快到飞起的包管理器。它在 Data Science 世界里真的火起来了——而且理由充分。

它又快又可靠。你会爱上它的！

首先，在 Cursor 里选择 View >> Terminal，打开 Cursor 内的 Terminal 窗口。输入 `pwd` 确认你在项目根目录。

然后输入 `uv --version` 看 uv 是否已安装。如果出现版本号，太好了！如果报错，请按这里的说明安装 uv——我推荐用最顶部的 Standalone Installer 方式，不过任何方式都行。在 Cursor 的安装终端里运行命令。如果一种方式不行，就换另一种。

https://docs.astral.sh/uv/getting-started/installation/

安装完 uv 后，你需要在 Cursor 里打开一个新的终端窗口（加号，或 Ctrl+Shift+反引号），`uv --version` 才会生效。请检查一下！

安装或使用 uv 有任何问题，请看我 FAQ 页面上的 [Q11](https://edwarddonner.com/faq/#11)，有完整说明。

### 安装好之后：

运行 `uv self update`，确保你用的是最新版 uv。

然后只需运行：  
`uv sync`  
uv 会以飞一般的速度装好一切。有问题请看我 FAQ 页面上的 [Q11](https://edwarddonner.com/faq/#11)。

你现在拥有一个完整规格的环境了！！

用 uv 又简单又快：  
1. 不用 `pip install xxx`，改用 `uv add xxx`  
2. 你永远不需要手动激活环境——uv 会帮你搞定。  
3. 不用 `python xxx`，改用 `uv run xxx`

___

## 第 3 步——可选——设置 OpenAI 账号

替代方案：免费替代见 guides 文件夹中的 Guide 9！

前往 https://platform.openai.com

- 点击 Sign Up 创建账号（如果还没有）。你可能需要先点几下按钮创建 Organization——填合理的默认值即可。如果不清楚 ChatGPT 和 OpenAI API 的区别，见 Guides 文件夹中的 Guide 4。
- 点击右上角的 Settings 图标，然后在左侧导航栏点 Billing。
- 确保 Auto-Recharge 是关闭的。按需点击「Add to Credit Balance」，选择 \$5 的预付金额，并务必添加正确的支付方式
- 仍在 Settings 中，在左侧边栏选择 API keys（靠近顶部）
- 按「Create new secret key」——选择「Owned by you」，起任意名称，项目选「Default project」，Permissions 保持 All
- 按「Create secret key」，你会看到新密钥。按 Copy 把它复制到剪贴板。

___

## 第 4 步——使用 OpenAI 或 Gemini 等模型时需要；如果只用 Ollama 则不需要——创建（并保存）你的 .env 文件

**这一节请务必认真！**——密钥相关的任何失误都极难排查！！很多学生因为其中某一步做错而大量来问我……最重要的是：改完文件后一定要保存。

1. 创建你的 `.env` 文件

- 回到 Cursor
- 在左侧 File Explorer 中，在所有文件下方的空白处右键，选择「New File」，把文件命名为 `.env`
- 我怎么强调都不为过：文件名必须精确地叫 `.env`——就这四个字符，不多不少。不能是 ".env.txt"，不能是 "john.env"，不能是 "openai.env"，也不能是别的任何名字！并且它必须在项目根目录下。

如果你在想我为什么这么唠叨：有很多人、很多人（尽管我反复恳求）还是把文件命名成别的东西，还觉得没问题。不行！它必须叫 `.env`，并且放在 llm_engineering 目录里 😂

2. 填写你的 `.env` 文件，然后保存：

在左侧选中该文件。右侧应该是一个空白文件。在右侧文件内容中输入：

`OPENAI_API_KEY=`

然后粘贴！你现在应该会看到类似这样的内容：

`OPENAI_API_KEY=sk-proj-lots-and-lots-of-digits`

当然，那里应该是你的真实密钥，而不是字面的 "sk-proj-lots-and-lots-of-digits"..

现在一定要保存文件！File >> Save，或 Ctrl+S（PC），或 Command+S（Mac）。很多人忘了保存。你需要保存文件！

你应该会在 .env 文件旁看到一个禁止标志——别担心……这是好事！如果你想了解原因，见 [这里](https://edwarddonner.com/faq) 的 Q7。

__

## 第 5 步——安装 Cursor 扩展、打开 Day 1、设置 Kernel，然后出发！

（如果 Cursor 提示你安装推荐扩展，直接同意！这对这一步是个很好的快捷方式。）

- 打开 View 菜单，选择 Extensions。  
- 搜索 "python" 找到 Python 扩展。选择由 "ms-python" 或 "anysphere" 制作的 Python 扩展，若未安装则安装。  
- 搜索 "jupyter"，选择由 "ms-toolsai" 制作的扩展，若未安装则安装。

现在进入 View >> Explorer。打开 week1 文件夹，点击 `day1.ipynb`。

- 看到右上角附近写着「Select Kernel」了吗？点它……然后选「Python Environments」
- 选择带星标的最上面那个选项，内容应类似 `.venv (Python 3.12.x) .venv/bin/python Recommended`
- 如果没有出现，请到 Setup 文件夹中的 troubleshooting lab。

# 恭喜！！你做到了！课程剩下的部分都很轻松 😂

**中文路径提醒：** 之后每周打开 notebook / 说明时，请优先选同目录下的 `*_zh.ipynb` / `*_zh.md`；英文原版可作对照。Week5 知识库初学建议先用英文 `.md` 跑通演示（详见上方「中文学习路径小贴士」）。

**最后一点说明：**

课程很早（第 2 天），我会演示一款很酷、很受欢迎的产品：Claude Code。它是一款 AI 编程工具，和我们课程里用的 Cursor 类似。我只是把它当作 Agentic AI 实战的例子；它并不是本课程明确覆盖的工具，尤其是我们本来就在用 Cursor。但如果你想自己用 Claude Code，Anthropic 的 Quick Start 指南在 [这里](https://docs.claude.com/en/docs/claude-code/quickstart)。
