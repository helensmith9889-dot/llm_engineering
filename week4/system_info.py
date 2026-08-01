"""
本机系统与工具链信息采集（教学用）

在本地跑 ML / LLM、或把 Python 热点改成 C++/Rust 加速时，
往往需要先搞清楚：操作系统、CPU、包管理器、编译器是否齐全。
本模块用「尽量安全、失败就返回空」的方式探测这些信息，
输出紧凑字典，方便交给 LLM 帮你选安装路径与编译参数。

概念提示（与本地 ML/LLM 相关）：
- 这里侧重「CPU + 系统工具链」，不是 CUDA 驱动详情；但架构（x86_64/arm64）、
  WSL、物理核数等，会影响你如何本地编译扩展、选 -j 并行度、判断能否用某些指令集。
- SIMD（如 AVX2）提示编译器可用的向量指令；本地数值/推理相关 C++ 加速时常会用到。
- WSL：Windows 子系统里的 Linux；很多课程在 WSL2 里跑 Python/LLM，探测到它很有用。
- 所有探测都 best-effort：命令不存在或超时就当没有，避免 Demo 直接崩溃。
"""

import os
import platform
import shutil
import subprocess

# ------------------------- helpers -------------------------


def _run(cmd, timeout=3):
    """
    安全地执行一条外部命令，返回 stdout 文本；失败则返回空字符串。

    参数:
        cmd: 字符串（走 shell）或参数列表（不走 shell）。
             列表形式更安全；字符串形式便于管道/重定向一类写法。
        timeout: 秒；超时则放弃，避免卡住 Gradio / Notebook。

    返回:
        str: 去掉首尾空白的标准输出；任何异常（含超时、找不到命令）都返回 ""。

    概念提示：
    - stderr 丢到 DEVNULL：探测类脚本通常只关心「有没有有用输出」。
    - text=True：得到 str 而不是 bytes，方便后续字符串处理。
    """
    try:
        if isinstance(cmd, str):
            return subprocess.check_output(
                cmd, shell=True, text=True, stderr=subprocess.DEVNULL, timeout=timeout
            ).strip()
        else:
            return subprocess.check_output(
                cmd, shell=False, text=True, stderr=subprocess.DEVNULL, timeout=timeout
            ).strip()
    except Exception:
        return ""


def _first_line(s: str) -> str:
    """
    取多行文本的第一行（去空白）；空输入返回 ""。

    参数:
        s: 任意字符串（常为命令输出）。

    返回:
        str: 第一行内容，或空字符串。
    """
    s = (s or "").strip()
    return s.splitlines()[0].strip() if s else ""


def _which(name: str) -> str:
    """
    在 PATH 中查找可执行文件路径。

    参数:
        name: 程序名，如 "gcc"、"cmake"、"rustc"。

    返回:
        str: 绝对路径；找不到则 ""（注意不是 None，便于后续布尔判断与拼接）。
    """
    return shutil.which(name) or ""


def _bool_from_output(s: str) -> bool:
    """
    把常见的「真值」命令输出解析成 bool。

    参数:
        s: 命令输出，如 "1"、"true"、"YES"。

    返回:
        bool: 仅当去掉空白后属于约定真值集合时为 True。
    """
    return s.strip() in {"1", "true", "True", "YES", "Yes", "yes"}


# ------------------------- OS & env -------------------------


def _os_block():
    """
    采集操作系统与运行环境信息。

    返回:
        dict，主要字段：
            system / arch / release / version / kernel:
                平台名、CPU 架构、版本与内核信息。
            distro: Linux 发行版（来自 /etc/os-release）；非 Linux 为 None。
            wsl: 是否看起来运行在 WSL 中。
            rosetta2_translated: macOS 上是否正以 Rosetta 翻译模式运行。
            target_triple: 编译器报告的目标三元组（如 x86_64-linux-gnu），best-effort。

    概念提示：
    - target triple 影响交叉编译与「给 LLM 的编译建议」是否匹配本机。
    - WSL 下路径、GPU 透传、包管理器行为可能与原生 Linux 不同，值得单独标出。
    """
    sysname = platform.system()  # 'Windows', 'Darwin', 'Linux'
    machine = platform.machine() or ""
    release = platform.release() or ""
    version = platform.version() or ""
    # Windows 用 release；类 Unix 优先 uname -r，失败再回退 release
    kernel = release if sysname == "Windows" else (_run(["uname", "-r"]) or release)

    distro = {"name": "", "version": ""}
    if sysname == "Linux":
        # Best-effort parse of /etc/os-release
        try:
            with open("/etc/os-release", "r") as f:
                data = {}
                for line in f:
                    if "=" in line:
                        k, v = line.rstrip().split("=", 1)
                        # 去掉 shell 风格引号，得到可读发行版名
                        data[k] = v.strip('"')
                distro["name"] = data.get("PRETTY_NAME") or data.get("NAME", "")
                distro["version"] = data.get("VERSION_ID") or data.get("VERSION", "")
        except Exception:
            pass

    # WSL / Rosetta detection (harmless if not present)
    wsl = False
    if sysname != "Windows":
        try:
            # /proc/version 在 WSL 里通常含 microsoft / wsl 字样
            with open("/proc/version", "r") as f:
                v = f.read().lower()
                wsl = ("microsoft" in v) or ("wsl" in v)
        except Exception:
            wsl = False

    rosetta = False
    if sysname == "Darwin":
        # sysctl.proc_translated=1 表示当前进程正通过 Rosetta 运行
        rosetta = _bool_from_output(_run(["sysctl", "-in", "sysctl.proc_translated"]))

    # Target triple (best effort)
    target = ""
    for cc in ("clang", "gcc"):
        if _which(cc):
            out = _run([cc, "-dumpmachine"])
            if out:
                target = _first_line(out)
                break

    return {
        "system": sysname,
        "arch": machine,
        "release": release,
        "version": version,
        "kernel": kernel,
        "distro": distro if sysname == "Linux" else None,
        "wsl": wsl,
        "rosetta2_translated": rosetta,
        "target_triple": target,
    }


# ------------------------- package managers -------------------------


def _package_managers():
    """
    探测本机可用的包管理器（用于告诉 LLM「该怎么装依赖」）。

    返回:
        list[str]: 已找到的包管理器名称列表（可能为空）。

    概念提示：
    - Windows: winget / choco / scoop
    - macOS: Xcode CLT、Homebrew(brew)、MacPorts(port)
    - Linux: apt / dnf / yum / pacman 等——本地装 CUDA toolkit、编译器时常用
    """
    sysname = platform.system()
    pms = []
    if sysname == "Windows":
        for pm in ("winget", "choco", "scoop"):
            if _which(pm):
                pms.append(pm)
    elif sysname == "Darwin":
        # xcode-select -p 有输出 ⇒ 已装 Command Line Tools
        if _run(["xcode-select", "-p"]):
            pms.append("xcode-select (CLT)")
        for pm in ("brew", "port"):
            if _which(pm):
                pms.append(pm)
    else:
        for pm in ("apt", "dnf", "yum", "pacman", "zypper", "apk", "emerge"):
            if _which(pm):
                pms.append(pm)
    return pms


# ------------------------- CPU (minimal) -------------------------


def _cpu_block():
    """
    采集最小化的 CPU 信息：品牌型号、逻辑/物理核数、SIMD 指令提示。

    返回:
        dict:
            brand: CPU 型号字符串。
            cores_logical: 逻辑核（含超线程），os.cpu_count()。
            cores_physical: 物理核（best-effort，失败则为 0）。
            simd: 探测到的 SIMD 标志列表（如 AVX2），供优化建议参考。

    概念提示（本地 ML/编译）：
    - 逻辑核常用于建议 make -j / cmake 并行任务数。
    - AVX2/AVX512 等影响本地数值库、部分推理后端能否启用向量加速。
    - 本函数不查询 GPU/CUDA；GPU 需另用 nvidia-smi 等工具。
    """
    sysname = platform.system()
    brand = ""
    # A simple brand/model read per OS; ignore failures
    if sysname == "Linux":
        brand = _run("grep -m1 'model name' /proc/cpuinfo | cut -d: -f2").strip()
    elif sysname == "Darwin":
        brand = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
    elif sysname == "Windows":
        brand = _run('powershell -NoProfile -Command "(Get-CimInstance Win32_Processor).Name"')
        if not brand:
            brand = _run("wmic cpu get Name /value").replace("Name=", "").strip()

    # Logical cores always available; physical is best-effort
    cores_logical = os.cpu_count() or 0
    cores_physical = 0
    if sysname == "Darwin":
        cores_physical = int(_run(["sysctl", "-n", "hw.physicalcpu"]) or "0")
    elif sysname == "Windows":
        cores_physical = int(
            _run('powershell -NoProfile -Command "(Get-CimInstance Win32_Processor).NumberOfCores"')
            or "0"
        )
    elif sysname == "Linux":
        # This is a quick approximation; fine for our use (parallel -j suggestions)
        try:
            # Count unique "core id" per physical id
            # lscpu -p 输出 CSV；用 (CORE,SOCKET) 去重近似物理核数
            mapping = _run("LC_ALL=C lscpu -p=CORE,SOCKET | grep -v '^#'").splitlines()
            unique = set(tuple(line.split(",")) for line in mapping if "," in line)
            cores_physical = len(unique) or 0
        except Exception:
            cores_physical = 0

    # A tiny SIMD hint set (best-effort, optional)
    simd = []
    if sysname == "Linux":
        flags = _run("grep -m1 'flags' /proc/cpuinfo | cut -d: -f2")
        if flags:
            fset = set(flags.upper().split())
            for x in ("AVX512F", "AVX2", "AVX", "FMA", "SSE4_2", "NEON", "SVE"):
                if x in fset:
                    simd.append(x)
    elif sysname == "Darwin":
        feats = (
            (
                _run(["sysctl", "-n", "machdep.cpu.features"])
                + " "
                + _run(["sysctl", "-n", "machdep.cpu.leaf7_features"])
            )
            .upper()
            .split()
        )
        for x in ("AVX512F", "AVX2", "AVX", "FMA", "SSE4_2", "NEON", "SVE"):
            if x in feats:
                simd.append(x)
    # On Windows, skip flags — brand typically suffices for MSVC /arch choice.

    return {
        "brand": brand.strip(),
        "cores_logical": cores_logical,
        "cores_physical": cores_physical,
        "simd": sorted(set(simd)),
    }


# ------------------------- toolchain presence -------------------------


def _toolchain_block():
    """
    探测 C/C++ 编译器与常见构建工具是否安装，以及简短版本行。

    返回:
        dict:
            compilers: gcc / g++ / clang / msvc_cl 的版本首行（没有则为 ""）。
            build_tools: cmake / ninja / make。
            linkers: ld.lld（LLVM 链接器）是否可用。

    概念提示：
    - 本地把 Python 扩展或性能热点编译成原生代码时，这些工具是「基础设施」。
    - MSVC 的 cl 往往只在「开发者命令行」里出现在 PATH，探测失败很常见，属正常。
    - ninja 常与 cmake 搭配，加速本地反复编译。
    """
    def ver_line(exe, args=("--version",)):
        """对可执行文件跑版本参数，只取输出第一行。"""
        p = _which(exe)
        if not p:
            return ""
        out = _run([p, *args])
        return _first_line(out)

    gcc = ver_line("gcc")
    gpp = ver_line("g++")
    clang = ver_line("clang")

    # MSVC cl (only available inside proper dev shell; handle gracefully)
    msvc_cl = ""
    cl_path = _which("cl")
    if cl_path:
        # cl 常把版本打到 stderr；这里用 shell 把 2>&1 合并后再取首行
        msvc_cl = _first_line(_run("cl 2>&1"))

    # Build tools (presence + short version line)
    cmake = ver_line("cmake")
    # ninja --version 通常只有一行版本号
    ninja = _first_line(_run([_which("ninja"), "--version"])) if _which("ninja") else ""
    make = ver_line("make")

    # Linker (we only care if lld is available)
    lld = ver_line("ld.lld")
    return {
        "compilers": {"gcc": gcc, "g++": gpp, "clang": clang, "msvc_cl": msvc_cl},
        "build_tools": {"cmake": cmake, "ninja": ninja, "make": make},
        "linkers": {"ld_lld": lld},
    }


# ------------------------- public API -------------------------


def retrieve_system_info():
    """
    汇总本机「够 LLM 做安装/编译建议」的紧凑系统信息。

    典型用途（本地 ML/LLM 工程）：
      - 选安装路径（winget/choco/scoop，Homebrew/Xcode CLT，apt/dnf/...），
      - 选编译器家族（MSVC / clang / gcc），
      - 建议较安全的优化参数（如 -O3/-march=native 或 MSVC /O2），
      - 决定构建系统（cmake+ninja）以及并行 -j 取值。

    参数:
        无。

    返回:
        dict，包含键：
            os: _os_block() 结果
            package_managers: 包管理器列表
            cpu: CPU 摘要
            toolchain: 编译器与构建工具

    概念提示：
    - 返回值 intentionally 紧凑，方便塞进 prompt，而不是完整硬件清单。
    - 若你还需要 GPU/CUDA（显存、驱动、torch.cuda.is_available），请另写探测逻辑。
    """
    return {
        "os": _os_block(),
        "package_managers": _package_managers(),
        "cpu": _cpu_block(),
        "toolchain": _toolchain_block(),
    }


def rust_toolchain_info():
    """
    探测 Rust 工具链相关信息，供本地加速 / 系统编程 Demo 使用。

    返回字段概览：
      - rustc / cargo / rustup / rust-analyzer 是否存在及其路径
      - 版本、host triple、release、commit
      - 当前/默认 toolchain、已安装 toolchains 与 targets
      - 常见环境变量（CARGO_HOME、RUSTUP_HOME、RUSTFLAGS、CARGO_BUILD_TARGET）
      - 在本机上「多半能跑」的简易命令示例

    参数:
        无。

    返回:
        dict: 见上方字段说明；installed 表示是否至少找到 rustc/cargo/rustup 之一。

    概念提示：
    - host_triple（如 aarch64-apple-darwin）决定默认编译目标，和 C 的 target triple 类似。
    - 跨平台：Windows / macOS / Linux 共用同一套探测逻辑。
    - 依赖本文件的 _run、_which、_first_line 辅助函数。
    """
    info = {
        "installed": False,
        "rustc": {"path": "", "version": "", "host_triple": "", "release": "", "commit_hash": ""},
        "cargo": {"path": "", "version": ""},
        "rustup": {
            "path": "",
            "version": "",
            "active_toolchain": "",
            "default_toolchain": "",
            "toolchains": [],
            "targets_installed": [],
        },
        "rust_analyzer": {"path": ""},
        "env": {
            "CARGO_HOME": os.environ.get("CARGO_HOME", ""),
            "RUSTUP_HOME": os.environ.get("RUSTUP_HOME", ""),
            "RUSTFLAGS": os.environ.get("RUSTFLAGS", ""),
            "CARGO_BUILD_TARGET": os.environ.get("CARGO_BUILD_TARGET", ""),
        },
        "execution_examples": [],
    }

    # Paths
    rustc_path = _which("rustc")
    cargo_path = _which("cargo")
    rustup_path = _which("rustup")
    ra_path = _which("rust-analyzer")

    info["rustc"]["path"] = rustc_path or ""
    info["cargo"]["path"] = cargo_path or ""
    info["rustup"]["path"] = rustup_path or ""
    info["rust_analyzer"]["path"] = ra_path or ""

    # Versions & verbose details
    if rustc_path:
        ver_line = _first_line(_run([rustc_path, "--version"]))
        info["rustc"]["version"] = ver_line
        # --verbose 提供 host / release / commit-hash 等键值行
        verbose = _run([rustc_path, "--version", "--verbose"])
        host = release = commit = ""
        for line in verbose.splitlines():
            if line.startswith("host:"):
                host = line.split(":", 1)[1].strip()
            elif line.startswith("release:"):
                release = line.split(":", 1)[1].strip()
            elif line.startswith("commit-hash:"):
                commit = line.split(":", 1)[1].strip()
        info["rustc"]["host_triple"] = host
        info["rustc"]["release"] = release
        info["rustc"]["commit_hash"] = commit

    if cargo_path:
        info["cargo"]["version"] = _first_line(_run([cargo_path, "--version"]))

    if rustup_path:
        info["rustup"]["version"] = _first_line(_run([rustup_path, "--version"]))
        # Active toolchain
        active = _first_line(_run([rustup_path, "show", "active-toolchain"]))
        info["rustup"]["active_toolchain"] = active

        # Default toolchain (best effort)
        # Try parsing `rustup toolchain list` and pick the line with "(default)"
        tlist = _run([rustup_path, "toolchain", "list"]).splitlines()
        info["rustup"]["toolchains"] = [t.strip() for t in tlist if t.strip()]
        default_tc = ""
        for line in tlist:
            if "(default)" in line:
                default_tc = line.strip()
                break
        if not default_tc:
            # Fallback: sometimes `rustup show` includes "default toolchain: ..."
            for line in _run([rustup_path, "show"]).splitlines():
                if "default toolchain:" in line:
                    default_tc = line.split(":", 1)[1].strip()
                    break
        info["rustup"]["default_toolchain"] = default_tc

        # Installed targets
        # --installed：只列已安装 target，避免把可选列表整表塞进 prompt
        targets = _run([rustup_path, "target", "list", "--installed"]).split()
        info["rustup"]["targets_installed"] = targets

    # Execution examples (only include what will work on this system)
    exec_examples = []
    if cargo_path:
        exec_examples.append(f'"{cargo_path}" build')
        exec_examples.append(f'"{cargo_path}" run')
        exec_examples.append(f'"{cargo_path}" test')
    if rustc_path:
        exec_examples.append(f'"{rustc_path}" hello.rs -o hello')
    info["execution_examples"] = exec_examples

    # Installed?
    info["installed"] = bool(rustc_path or cargo_path or rustup_path)

    # Fill in default homes if env vars are empty but typical locations exist
    def _maybe_default_home(env_val, default_basename):
        """
        若环境变量未设，但家目录下存在默认文件夹，则回填该路径。

        参数:
            env_val: 当前环境变量值。
            default_basename: 如 ".cargo"、".rustup"。

        返回:
            str: 有效路径或空字符串。
        """
        if env_val:
            return env_val
        home = os.path.expanduser("~") or ""
        candidate = os.path.join(home, default_basename) if home else ""
        return candidate if candidate and os.path.isdir(candidate) else ""

    info["env"]["CARGO_HOME"] = _maybe_default_home(info["env"]["CARGO_HOME"], ".cargo")
    info["env"]["RUSTUP_HOME"] = _maybe_default_home(info["env"]["RUSTUP_HOME"], ".rustup")

    return info
