from pathlib import Path
import sys
import re

REPO_ROOT = (Path(__file__).parent / "..").resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import json
import shutil
from init_develop_environment import check_ocr_model_directory
from scripts.json_utils import strip_interface_json_comments




working_dir = (Path(__file__).parent / "..").resolve()
install_path = working_dir / Path("install")
if len(sys.argv) > 1:
    version = sys.argv[1]
    print(f"[install] 使用传入的版本号: {version}")
else:
    version = "v0.0.1"
    print(f"[install] 未传入版本号，使用默认值: {version}")

if len(sys.argv) > 2:
    platform = sys.argv[2]
    print(f"[install] 使用传入的平台标识: {platform}")
else:
    platform = "windows"
    print(f"[install] 未传入平台标识，使用默认值: {platform}")

if len(sys.argv) > 3:
    arch = sys.argv[3]
    print(f"[install] 使用传入的体系结构: {arch}")
else:
    arch = "x86_64"
    print(f"[install] 未传入体系结构，使用默认值: {arch}")


def install_deps():
    if not (working_dir / "deps" / "bin").exists():
        print('Please download the MaaFramework to "deps" first.')
        print('请先下载 MaaFramework 到 "deps"。')
        sys.exit(1)

    shutil.copytree(
        working_dir / "deps" / "bin",
        install_path,
        ignore=shutil.ignore_patterns(
            "*MaaDbgControlUnit*",
            "*MaaThriftControlUnit*",
            "*MaaRpc*",
            "*MaaHttp*",
        ),
        dirs_exist_ok=True,
    )
    shutil.copytree(
        working_dir / "deps" / "share" / "MaaAgentBinary",
        install_path / "MaaAgentBinary",
        dirs_exist_ok=True,
    )


def install_resource():

    check_ocr_model_directory()

    shutil.copytree(
        working_dir / "assets" / "resource",
        install_path / "resource",
        dirs_exist_ok=True,
    )
    shutil.copy2(
        working_dir / "assets" / "interface.json",
        install_path,
    )
    shutil.copy2(
        working_dir / "assets" / "logo.ico",
        install_path,
    )

    ## 先将 assets/interface.json  中的 // 注释全部去掉
    strip_interface_json_comments(install_path / "interface.json")

    with open(install_path / "interface.json", "r", encoding="utf-8") as f:
        interface = json.load(f)

    interface["version"] = version
    interface["agent"]["child_exec"] = "{PROJECT_DIR}/python/python.exe"
    interface["agent"]["child_args"] = ["{PROJECT_DIR}/agent/main.py"]

    with open(install_path / "interface.json", "w", encoding="utf-8") as f:
        json.dump(interface, f, ensure_ascii=False, indent=4)


def install_chores():
    shutil.copy2(
        working_dir / "README.md",
        install_path,
    )
    shutil.copy2(
        working_dir / "LICENSE",
        install_path,
    )


def install_agent():
    shutil.copytree(
        working_dir / "agent",
        install_path / "agent",
        dirs_exist_ok=True,
    )
    # 取消 agent/main.py 中的 init_python_env 调用
    agent_main = install_path / "agent" / "main.py"
    if agent_main.exists():
        try:
            text = agent_main.read_text(encoding="utf-8")
            pattern = r"^([ \t]*)#\s*init_python_env\(\)"
            replacement = r"\1init_python_env()"
            new_text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
            if new_text != text:
                agent_main.write_text(new_text, encoding="utf-8")
                print("已取消 agent/main.py 中的 init_python_env() 注释")
            else:
                print("agent/main.py 中未找到被注释的 init_python_env()")
        except Exception as e:
            print(f"修改 agent/main.py 失败: {e}")
    else:
        print("未找到 agent/main.py，无法取消注释 init_python_env()")


# 安装 embeddable python(仅适用于 Windows)
def install_embed_python():
    if platform == "win":
        embed_python_install_path = install_path / "python"
        print(f"当前平台为 {platform} {arch}, 运行 embeddable python 安装")
        # 打印 working_dir/resource/embeddable_python_zip 下的所有文件
        print("以下是可用的 embeddable python zip 文件:")
        for file in (working_dir / "resource/embeddable_python_zip").iterdir():
            print(f" - {file.name}")
        embed_python_zip_path = (
            working_dir
            / f"resource/embeddable_python_zip"
            / f"python-3.13.7-embed-{arch}.zip"
        )
        # 解压 zip 文件到目标路径
        shutil.unpack_archive(embed_python_zip_path, embed_python_install_path, "zip")
        # 修改 install_path / "python/python313._pth" 文件, 添加一行 "import site" 以及"..\agent"
        pth_file_path = embed_python_install_path / "python313._pth"
        with open(pth_file_path, "a", encoding="utf-8") as f:
            f.write("\nimport site\n")
            f.write(r"..\agent")
    else:
        print(f"当前平台为 {platform} {arch}, 暂不支持 embeddable python 安装")


# 拷贝 python wheels 以及 get-pip.py 和 pyproject.toml
def copy_python_wheels():
    # 目前只对 Windows x64 下载了 wheels
    if platform != "win" or arch != "x86_64":
        print(f"当前平台为 {platform} {arch}, 跳过 wheels 拷贝步骤")
        return
    wheels_source_path = working_dir / "resource" / "wheels" / "win-x64"
    wheels_target_path = install_path / "deps" / "wheels"
    shutil.copytree(wheels_source_path, wheels_target_path, dirs_exist_ok=True)

    get_pip_source_path = working_dir / "resource" / "get-pip.py"
    get_pip_target_path = install_path / "deps" / "get-pip.py"
    shutil.copy2(get_pip_source_path, get_pip_target_path)

    pyproject_source_path = working_dir / "pyproject.toml"
    pyproject_target_path = install_path / "pyproject.toml"
    shutil.copy2(pyproject_source_path, pyproject_target_path)


if __name__ == "__main__":
    install_deps()
    install_resource()
    install_chores()
    install_agent()
    install_embed_python()
    copy_python_wheels()

    print(f"Install to {install_path} successfully.")
