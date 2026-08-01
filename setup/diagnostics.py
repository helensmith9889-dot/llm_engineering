"""
环境诊断工具（Environment Diagnostics）——面向 LLM Engineering 课程的环境自检脚本。

本文件用于在课程开始前/排错时，自动检查本机 Python 环境是否就绪，并把结果
同时打印到终端和写入 report.txt，方便发给助教或导师排查。

主要检查内容：
1. 系统信息（操作系统、CPU、内存、磁盘空间）
2. 当前目录与写权限（pathlib / os）
3. Git 仓库状态（是否克隆正确、当前提交、远程地址）
4. .env 文件与 OPENAI_API_KEY 是否存在
5. Anaconda / Conda 环境是否激活
6. 虚拟环境（venv / virtualenv）是否激活
7. 网络连通性与 SSL（HTTPS、带宽粗测）
8. 环境变量与 Python 搜索路径（sys.path）
9. 常见命名冲突（如本地 openai.py 遮蔽官方包）与临时目录可写性

为什么初学者需要它：
- 课程依赖 API Key、conda/venv、网络与若干 Python 包；任一项配置错误都会导致
  notebook 报错，但错误信息往往不够直观。
- 本工具把“环境是否 OK”整理成一份可读报告，帮助你快速定位是系统、依赖、
  密钥还是网络问题，而不是在 notebook 里反复试错。
"""

import os
import sys
import platform
import subprocess
import shutil
import time
import ssl
import tempfile
from pathlib import Path
from datetime import datetime

class Diagnostics:
    """课程环境诊断器（Diagnostics）。

    按步骤收集本机环境信息，区分「错误」（errors，通常会阻塞课程运行）
    与「警告」（warnings，可能引起异常行为），并写入 report.txt。

    使用方式：直接运行本文件（见文件末尾 ``if __name__ == "__main__"``），
    或在 notebook / 其他脚本中实例化后调用 ``run()``。
    """

    FILENAME = 'report.txt'
    
    def __init__(self):
        """初始化诊断器：清空结果列表；若已有旧报告则删除，避免结果混杂。"""
        self.errors = []
        self.warnings = []
        # 每次运行都从空白报告开始，避免读到上次的诊断结果
        if os.path.exists(self.FILENAME):
            os.remove(self.FILENAME)

    def log(self, message):
        """同时输出到终端并追加写入报告文件。

        Args:
            message: 要记录的一行文本（不含换行符亦可，写入时会补 ``\\n``）。
        """
        print(message)
        # encoding='utf-8' 保证中文/特殊符号在各平台都能正确写入
        with open(self.FILENAME, 'a', encoding='utf-8') as f:
            f.write(message + "\n")

    def start(self):
        """记录诊断开始时间戳。"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log(f"Starting diagnostics at {now}\n")

    def end(self):
        """记录诊断结束时间，并提示用户如何把报告发给导师。"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log(f"\n\nCompleted diagnostics at {now}\n")
        print("\nPlease send these diagnostics to me at ed@edwarddonner.com")
        print(f"Either copy & paste the above output into an email, or attach the file {self.FILENAME} that has been created in this directory.")
    

    def _log_error(self, message):
        """记录一条严重问题（error）：写入日志并加入 ``self.errors``。

        Args:
            message: 错误描述（不要带 ``ERROR:`` 前缀，本方法会自动添加）。
        """
        self.log(f"ERROR: {message}")
        self.errors.append(message)

    def _log_warning(self, message):
        """记录一条警告（warning）：写入日志并加入 ``self.warnings``。

        Args:
            message: 警告描述（不要带 ``WARNING:`` 前缀，本方法会自动添加）。
        """
        self.log(f"WARNING: {message}")
        self.warnings.append(message)

    def run(self):
        """按固定顺序执行全部诊断步骤，并汇总错误/警告后结束。

        步骤顺序：系统信息 → 文件系统 → Git → .env → Conda → venv
        → 网络/SSL → 环境变量 → 额外检查（命名冲突、临时目录）。
        无副作用地“只读检查”为主；写权限/临时文件测试会短暂创建再删除文件。
        """
        self.start()
        self._step1_system_info()
        self._step2_check_files()
        self._step3_git_repo()
        self._step4_check_env_file()
        self._step5_anaconda_check()
        self._step6_virtualenv_check()
        self._step7_network_connectivity()
        self._step8_environment_variables()
        self._step9_additional_diagnostics()

        # 汇总区：先警告后错误，方便初学者优先看到“必须修”的问题
        if self.warnings:
            self.log("\n===== Warnings Found =====")
            self.log("The following warnings were detected. They might not prevent the program from running but could cause unexpected behavior:")
            for warning in self.warnings:
                self.log(f"- {warning}")

        if self.errors:
            self.log("\n===== Errors Found =====")
            self.log("The following critical issues were detected. Please address them before proceeding:")
            for error in self.errors:
                self.log(f"- {error}")

        if not self.errors and not self.warnings:
            self.log("\n✅ All diagnostics passed successfully!")

        self.end()

    def _step1_system_info(self):
        """步骤 1：收集操作系统（OS）、硬件架构、内存与磁盘空间。

        使用 ``platform`` 识别 Windows / macOS（Darwin）/ Linux；
        可选依赖 ``psutil`` 读取可用内存（RAM）；用 ``shutil.disk_usage`` 检查磁盘。
        可用内存 < 2GB 或剩余磁盘 < 5GB 时记为警告（训练/下载模型时更容易失败）。
        """
        self.log("===== System Information =====")
        try:
            system = platform.system()
            self.log(f"Operating System: {system}")

            # platform.system() 在 macOS 上返回 "Darwin"
            if system == "Windows":
                release, version, csd, ptype = platform.win32_ver()
                self.log(f"Windows Release: {release}")
                self.log(f"Windows Version: {version}")
            elif system == "Darwin":
                release, version, machine = platform.mac_ver()
                self.log(f"MacOS Version: {release}")
            else:
                self.log(f"Platform: {platform.platform()}")

            self.log(f"Architecture: {platform.architecture()}")
            self.log(f"Machine: {platform.machine()}")
            self.log(f"Processor: {platform.processor()}")

            try:
                import psutil
                ram = psutil.virtual_memory()
                # 字节 → GB：除以 1024^3
                total_ram_gb = ram.total / (1024 ** 3)
                available_ram_gb = ram.available / (1024 ** 3)
                self.log(f"Total RAM: {total_ram_gb:.2f} GB")
                self.log(f"Available RAM: {available_ram_gb:.2f} GB")

                if available_ram_gb < 2:
                    self._log_warning(f"Low available RAM: {available_ram_gb:.2f} GB")
            except ImportError:
                self._log_warning("psutil module not found. Cannot determine RAM information.")

            # "~" 展开为当前用户主目录，检查该分区剩余空间
            total, used, free = shutil.disk_usage(os.path.expanduser("~"))
            free_gb = free / (1024 ** 3)
            self.log(f"Free Disk Space: {free_gb:.2f} GB")

            if free_gb < 5:
                self._log_warning(f"Low disk space: {free_gb:.2f} GB free")

        except Exception as e:
            self._log_error(f"System information check failed: {e}")

    def _step2_check_files(self):
        """步骤 2：检查当前工作目录、写权限，并列出目录内容。

        写权限测试：用 ``pathlib.Path``（面向对象的路径库）创建临时隐藏文件
        ``.test_write_permission``，成功后立即删除。若无法创建，说明当前目录
        不可写，后续生成 report.txt 或保存 notebook 输出也可能失败。
        """
        self.log("\n===== File System Information =====")
        try:
            current_dir = os.getcwd()
            self.log(f"Current Directory: {current_dir}")

            # Check write permissions
            # Path 支持用 / 拼接路径；touch 创建空文件；unlink 删除文件
            test_file = Path(current_dir) / ".test_write_permission"
            try:
                test_file.touch(exist_ok=True)
                test_file.unlink()
                self.log("Write permission: OK")
            except Exception as e:
                self._log_error(f"No write permission in current directory: {e}")

            self.log("\nFiles in Current Directory:")
            try:
                for item in sorted(os.listdir(current_dir)):
                    self.log(f" - {item}")
            except Exception as e:
                self._log_error(f"Cannot list directory contents: {e}")

        except Exception as e:
            self._log_error(f"File system check failed: {e}")

    def _step3_git_repo(self):
        """步骤 3：通过子进程（subprocess）调用 git，检查仓库信息。

        ``subprocess.run`` 会在本机启动外部命令并捕获标准输出/错误。
        依次查询：仓库根目录、当前提交（commit）、远程 origin URL。
        未安装 git、不在仓库内、或未配置 origin 时记为警告而非崩溃。
        """
        self.log("\n===== Git Repository Information =====")
        try:
            # text=True：把 stdout/stderr 当作字符串而不是字节
            result = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                git_root = result.stdout.strip()
                self.log(f"Git Repository Root: {git_root}")

                result = subprocess.run(['git', 'rev-parse', 'HEAD'],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    self.log(f"Current Commit: {result.stdout.strip()}")
                else:
                    self._log_warning(f"Could not get current commit: {result.stderr.strip()}")

                result = subprocess.run(['git', 'remote', 'get-url', 'origin'],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    self.log(f"Remote Origin: {result.stdout.strip()}")
                else:
                    self._log_warning("No remote 'origin' configured")
            else:
                self._log_warning("Not a git repository")
        except FileNotFoundError:
            # 系统找不到 git 可执行文件（未安装或不在 PATH 中）
            self._log_warning("Git is not installed or not in PATH")
        except Exception as e:
            self._log_error(f"Git check failed: {e}")

    def _step4_check_env_file(self):
        """步骤 4：在 Git 仓库根目录查找 ``.env``，并检查是否含 OPENAI_API_KEY。

        ``.env`` 是本地密钥文件，通常不应提交到 Git；课程用它存放 API Key。
        本步骤只检查「是否存在以 ``OPENAI_API_KEY=`` 开头的行」，不会打印密钥内容。
        同时用 ``os.walk`` 扫描仓库内是否有多余的 ``.env``（容易造成加载错文件）。
        """
        self.log("\n===== Environment File Check =====")
        try:
            result = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                git_root = result.stdout.strip()
                env_path = os.path.join(git_root, '.env')

                if os.path.isfile(env_path):
                    self.log(f".env file exists at: {env_path}")
                    try:
                        # any(...)：只要有一行以 OPENAI_API_KEY= 开头即视为找到（不读出密钥值）
                        with open(env_path, 'r') as f:
                            has_api_key = any(line.strip().startswith('OPENAI_API_KEY=') for line in f)
                        if has_api_key:
                            self.log("OPENAI_API_KEY found in .env file")
                        else:
                            self._log_warning("OPENAI_API_KEY not found in .env file")
                    except Exception as e:
                        self._log_error(f"Cannot read .env file: {e}")
                else:
                    self._log_warning(".env file not found in project root")

                # Check for additional .env files
                # 子目录里再放一个 .env 时，不同工具可能加载到不同文件，易踩坑
                for root, _, files in os.walk(git_root):
                    if '.env' in files and os.path.join(root, '.env') != env_path:
                        self._log_warning(f"Additional .env file found at: {os.path.join(root, '.env')}")
            else:
                self._log_warning("Git root directory not found. Cannot perform .env file check.")
        except FileNotFoundError:
            self._log_warning("Git is not installed or not in PATH")
        except Exception as e:
            self._log_error(f"Environment file check failed: {e}")

    def _step5_anaconda_check(self):
        """步骤 5：检查 Anaconda / Conda 环境是否已激活。

        Conda 是常见的科学计算包管理器；激活环境后通常会设置环境变量
        ``CONDA_PREFIX``（当前环境路径）与 ``CONDA_EXE``（conda 可执行文件）。
        若已激活，再调用 ``_check_python_packages`` 检查课程所需包。
        """
        self.log("\n===== Anaconda Environment Check =====")
        try:
            conda_prefix = os.environ.get('CONDA_PREFIX')
            if conda_prefix:
                self.log("Anaconda environment is active:")
                self.log(f"Environment Path: {conda_prefix}")
                self.log(f"Environment Name: {os.path.basename(conda_prefix)}")

                # 未设置 CONDA_EXE 时回退为命令名 'conda'（依赖 PATH）
                conda_exe = os.environ.get('CONDA_EXE', 'conda')
                result = subprocess.run([conda_exe, '--version'],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    self.log(f"Conda Version: {result.stdout.strip()}")
                else:
                    self._log_warning("Could not determine Conda version")

                self._check_python_packages()
            else:
                self.log("No active Anaconda environment detected")
        except Exception as e:
            self._log_error(f"Anaconda environment check failed: {e}")

    def _step6_virtualenv_check(self):
        """步骤 6：检查虚拟环境（venv / virtualenv）是否已激活。

        虚拟环境把项目依赖隔离在独立目录，避免污染系统 Python。
        激活后通常存在环境变量 ``VIRTUAL_ENV``。若既无 venv 也无 Conda，记警告
        （课程强烈建议在隔离环境中运行）。
        """
        self.log("\n===== Virtualenv Check =====")
        try:
            virtual_env = os.environ.get('VIRTUAL_ENV')
            if virtual_env:
                self.log("Virtualenv is active:")
                self.log(f"Environment Path: {virtual_env}")
                self.log(f"Environment Name: {os.path.basename(virtual_env)}")

                self._check_python_packages()
            else:
                self.log("No active virtualenv detected")

            # 两种隔离环境都未激活时提醒（仍可能在 base/系统 Python 上误跑）
            if not virtual_env and not os.environ.get('CONDA_PREFIX'):
                self._log_warning("Neither virtualenv nor Anaconda environment is active")
        except Exception as e:
            self._log_error(f"Virtualenv check failed: {e}")

    def _check_python_packages(self):
        """检查当前 Python 解释器版本，以及课程所需包是否已安装。

        使用 ``pkg_resources.working_set`` 枚举已安装发行版及其版本号。
        同时检查易冲突的包名对（如同时安装 ``openai`` 与 ``openai-python``），
        这类冲突会导致 ``import openai`` 行为异常。
        """
        self.log("\nPython Environment:")
        self.log(f"Python Version: {sys.version}")
        self.log(f"Python Executable: {sys.executable}")

        required_packages = ['openai', 'python-dotenv', 'requests', 'gradio', 'transformers']

        try:
            import pkg_resources
            # key 通常是小写的发行版名称，version 为已安装版本字符串
            installed = {pkg.key: pkg.version for pkg in pkg_resources.working_set}

            self.log("\nRequired Package Versions:")
            for package in required_packages:
                if package in installed:
                    self.log(f"{package}: {installed[package]}")
                else:
                    self._log_error(f"Required package '{package}' is not installed")

            # Check for potentially conflicting packages
            problem_pairs = [
                ('openai', 'openai-python'),
                ('python-dotenv', 'dotenv')
            ]

            for pkg1, pkg2 in problem_pairs:
                if pkg1 in installed and pkg2 in installed:
                    self._log_warning(f"Potentially conflicting packages: {pkg1} and {pkg2}")
        except ImportError:
            self._log_error("Could not import 'pkg_resources' to check installed packages")
        except Exception as e:
            self._log_error(f"Package check failed: {e}")

    def _step7_network_connectivity(self):
        """步骤 7：检查 SSL 版本、HTTPS 连通性，并粗测上下行带宽。

        SSL/TLS 是 HTTPS 的加密层；版本过旧可能导致访问 OpenAI 等 API 失败。
        先用 ``requests`` 访问公共网站验证基本联网；再用 ``speedtest-cli``
        做带宽测试（download/upload，单位换算为 Mbps）。
        任一测试 URL 成功即视为基本连通；全部失败则记错误并提前返回。
        """
        self.log("\n===== Network Connectivity Check =====")
        try:
            self.log(f"SSL Version: {ssl.OPENSSL_VERSION}")
    
            import requests
            import speedtest  # Importing the speedtest-cli library
    
            # Basic connectivity check
            urls = [
                'https://www.google.com',
                'https://www.cloudflare.com'
            ]
    
            connected = False
            for url in urls:
                try:
                    start_time = time.time()
                    response = requests.get(url, timeout=10)
                    elapsed_time = time.time() - start_time
                    # 4xx/5xx 会抛异常，从而进入下方 except
                    response.raise_for_status()
                    self.log(f"✓ Connected to {url}")
                    self.log(f"  Response time: {elapsed_time:.2f}s")
    
                    if elapsed_time > 2:
                        self._log_warning(f"Slow response from {url}: {elapsed_time:.2f}s")
                    connected = True
                    break
                except requests.exceptions.RequestException as e:
                    self._log_warning(f"Failed to connect to {url}: {e}")
                else:
                    # try/except/else：try 正常结束（未抛异常）时执行
                    self.log("Basic connectivity OK")
    
            if not connected:
                self._log_error("Failed to connect to any test URLs")
                return
    
            # Bandwidth test using speedtest-cli
            self.log("\nPerforming bandwidth test using speedtest-cli...")
            try:
                st = speedtest.Speedtest()
                st.get_best_server()
                download_speed = st.download()  # Bits per second
                upload_speed = st.upload()      # Bits per second
    
                download_mbps = download_speed / 1e6  # Convert to Mbps
                upload_mbps = upload_speed / 1e6
    
                self.log(f"Download speed: {download_mbps:.2f} Mbps")
                self.log(f"Upload speed: {upload_mbps:.2f} Mbps")
    
                if download_mbps < 1:
                    self._log_warning("Download speed is low")
                if upload_mbps < 0.5:
                    self._log_warning("Upload speed is low")
            except speedtest.ConfigRetrievalError:
                self._log_error("Failed to retrieve speedtest configuration")
            except Exception as e:
                self._log_warning(f"Bandwidth test failed: {e}")
    
        except ImportError:
            self._log_error("Required packages are not installed. Please install them using 'pip install requests speedtest-cli'")
        except Exception as e:
            self._log_error(f"Network connectivity check failed: {e}")


    def _step8_environment_variables(self):
        """步骤 8：检查 PYTHONPATH、``sys.path``，并用 dotenv 加载后验证 API Key。

        ``PYTHONPATH`` / ``sys.path`` 决定 ``import`` 时从哪些目录找模块。
        ``load_dotenv()`` 会把项目 ``.env`` 中的键值写入进程环境变量；
        随后检查 ``OPENAI_API_KEY`` 是否存在，并做简单格式校验（以 ``sk-proj-`` 开头等）。
        """
        self.log("\n===== Environment Variables Check =====")
        try:
            # Check Python paths
            pythonpath = os.environ.get('PYTHONPATH')
            if pythonpath:
                self.log("\nPYTHONPATH:")
                # os.pathsep 在 Windows 为 ';'，在 Unix 为 ':'
                for path in pythonpath.split(os.pathsep):
                    self.log(f" - {path}")
            else:
                self.log("\nPYTHONPATH is not set.")

            self.log("\nPython sys.path:")
            for path in sys.path:
                self.log(f" - {path}")

            # Check OPENAI_API_KEY
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.environ.get('OPENAI_API_KEY')
            if api_key:
                self.log("OPENAI_API_KEY is set after calling load_dotenv()")
                # 仅做粗略格式检查，不输出密钥本身
                if not api_key.startswith('sk-proj-') or len(api_key)<12:
                    self._log_warning("OPENAI_API_KEY format looks incorrect after calling load_dotenv()")
            else:
                self._log_warning("OPENAI_API_KEY environment variable is not set after calling load_dotenv()")
        except Exception as e:
            self._log_error(f"Environment variables check failed: {e}")

    def _step9_additional_diagnostics(self):
        """步骤 9：额外检查——模块命名冲突与临时目录（temp）可写性。

        若当前目录或 ``sys.path`` 上存在名为 ``openai.py`` / ``dotenv.py`` 的文件，
        Python 可能优先导入它们，从而“遮蔽”真正安装的第三方包（常见初学者坑）。
        同时用 ``tempfile.NamedTemporaryFile`` 验证系统临时目录可写
        （部分库下载缓存会依赖它）。
        """
        self.log("\n===== Additional Diagnostics =====")
        try:
            # Get the site-packages directory paths
            # site-packages：pip/conda 安装第三方包的标准目录
            import site
            site_packages_paths = site.getsitepackages()
            if hasattr(site, 'getusersitepackages'):
                site_packages_paths.append(site.getusersitepackages())
    
            # Function to check if a path is within site-packages
            def is_in_site_packages(path):
                # commonpath 相等说明 path 落在某个 site-packages 目录树下
                return any(os.path.commonpath([path, sp]) == sp for sp in site_packages_paths)
    
            # Check for potential name conflicts in the current directory and sys.path
            conflict_names = ['openai.py', 'dotenv.py']
    
            # Check current directory
            current_dir = os.getcwd()
            for name in conflict_names:
                conflict_path = os.path.join(current_dir, name)
                if os.path.isfile(conflict_path):
                    self._log_warning(f"Found '{name}' in the current directory, which may cause import conflicts: {conflict_path}")
    
            # Check sys.path directories
            for path in sys.path:
                if not path or is_in_site_packages(path):
                    continue  # Skip site-packages and empty paths
                for name in conflict_names:
                    conflict_file = os.path.join(path, name)
                    if os.path.isfile(conflict_file):
                        self._log_warning(f"Potential naming conflict: {conflict_file}")
    
            # Check temp directory
            try:
                # with 退出时 NamedTemporaryFile 会自动删除临时文件
                with tempfile.NamedTemporaryFile() as tmp:
                    self.log(f"Temp directory is writable: {os.path.dirname(tmp.name)}")
            except Exception as e:
                self._log_error(f"Cannot write to temp directory: {e}")
    
        except Exception as e:
            self._log_error(f"Additional diagnostics failed: {e}")


# 作为脚本直接运行时：创建诊断器并执行全部检查
if __name__ == "__main__":
    diagnostics = Diagnostics()
    diagnostics.run()
