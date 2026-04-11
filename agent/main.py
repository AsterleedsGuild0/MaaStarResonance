import importlib
import subprocess
import sys
from pathlib import Path
import hashlib
from utils import print_info, print_warning, print_error, print_debug

# 获取：当前目录 / 项目根目录 / wheels目录 的绝对路径
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
WHEELS_DIR = PROJECT_ROOT / "deps" / "wheels"
PYPROJECT_TOML_FILEPATH = PROJECT_ROOT / "pyproject.toml"


# 计算 pyproject.toml 的 hash 值，用于判断依赖是否变更
def calculate_file_hash(file_path: Path) -> str:
    """计算文件的 SHA256 哈希值"""
    sha256_hash = hashlib.sha256()
    with file_path.open("rb") as f:
        # 逐块读取文件内容，避免一次性加载大文件
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def check_req_ready() -> bool:
    """通过尝试 import maa 来检查依赖是否安装完成"""
    try:
        import maa  # noqa: F401

        _ = maa

        print_info("maa imported successfully")
        return True
    except ImportError:
        print_error("maa import failed")
        return False


def init_python_env():
    """离线安装 pip, setuptools, wheel 以及项目依赖"""
    # 判断依赖是否有变更
    hash_file_path = PROJECT_ROOT / ".pyproject_hash"
    current_hash = calculate_file_hash(PYPROJECT_TOML_FILEPATH)
    previous_hash = ""
    if hash_file_path.exists():
        with hash_file_path.open("r") as f:
            previous_hash = f.read().strip()
    else:
        print_info("首次运行，需安装依赖")
    if current_hash == previous_hash and check_req_ready():
        print_info("依赖未变更，跳过安装步骤")
        return
    else:
        print_info("依赖有变更, 需要安装/更新依赖")
        with hash_file_path.open("w") as f:
            f.write(current_hash)

    print_info(f"===== 开始安装/更新 Python 依赖 =====")

    # 检查 python 文件夹和可执行文件
    embed_python_path = PROJECT_ROOT / "python"
    if not embed_python_path.exists():
        print_info("请先运行 install.py 脚本安装 Python 运行环境")
        print_info(
            "Please run install.py script to install Python runtime environment first."
        )
        sys.exit(1)

    python_executable = embed_python_path / "python.exe"
    if not python_executable.exists():
        print_info("无法找到 Python 可执行文件，请检查 python 文件夹是否正确")
        print_info(
            "Cannot find Python executable, please check if the python folder is correct."
        )
        sys.exit(1)

    # 检查 pip 安装脚本
    get_pip_script = PROJECT_ROOT / "deps" / "get-pip.py"
    if not get_pip_script.exists():
        print_info("无法找到 get-pip.py，请检查 deps 文件夹是否正确")
        print_info(
            "Cannot find get-pip.py, please check if the deps folder is correct."
        )
        sys.exit(1)

    # 安装 pip
    subprocess.check_call(
        [
            str(python_executable),
            str(get_pip_script),
            "--no-index",
            f"--find-links={WHEELS_DIR}",
            "--no-warn-script-location",
        ]
    )

    # 安装 setuptools 和 wheel
    subprocess.check_call(
        [
            str(python_executable),
            "-m",
            "pip",
            "install",
            "--no-index",
            f"--find-links={WHEELS_DIR}",
            "--no-warn-script-location",
            "setuptools",
            "wheel",
        ]
    )

    # 安装项目依赖
    subprocess.check_call(
        [
            str(python_executable),
            "-m",
            "pip",
            "install",
            "--no-index",
            f"--find-links={WHEELS_DIR}",
            "--no-build-isolation",
            "--no-warn-script-location",
            f"{PROJECT_ROOT}",
        ]
    )

    # 补充独立 python 环境的 site-packages 扫描路径
    site_packages = (PROJECT_ROOT / "python" / "Lib" / "site-packages").resolve()
    if site_packages.exists() and str(site_packages) not in sys.path:
        sys.path.insert(0, str(site_packages))

    # 强制刷新缓存 | 让当前进程也能扫描到刚安装的依赖
    importlib.invalidate_caches()

    print_info("===== Python 依赖安装/更新 已完成 =====")


def main():
    # 开发时应当注释下面这行, 编译时自动解除注释
    # init_python_env()

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    # 导入MAA工具
    from maa.agent.agent_server import AgentServer
    from maa.toolkit import Toolkit

    # 导入基础包
    from agent.logger import logger
    from agent.module_loader import load_modules

    logger.info("===== 开始初始化MAA程序 =====")

    # 加载 agent 包下所有的模块
    for item in CURRENT_DIR.iterdir():
        # 跳过 __pycache__
        if item.is_dir() and item.name != "__pycache__":
            load_modules(str(item), f"agent.{item.name}")
            logger.info(f"> 子模块 {item.name} 加载完成！")

    logger.info("===== MAA程序初始化完成 =====")

    # 启动MAA主程序
    Toolkit.init_option("./")
    AgentServer.start_up(sys.argv[-1])
    AgentServer.join()
    AgentServer.shut_down()


if __name__ == "__main__":
    main()
