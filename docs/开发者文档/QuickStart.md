# QuickStart

> 只有当您想要开发 MAAStarResonance 时才需要看当前页面!
>
> 用户请转到 [MAAStarResonance使用手册](/docs/用户文档/新手上路/新手上路.md)
>
> 开发 MaaFramework 或开发自己的项目请到 [MaaXYZ/MaaFramework](https://github.com/MaaXYZ/MaaFramework)
>
> [M9A的开发者文档](https://1999.fan/zh_cn/develop) 很全面, 非常值得参考!

## Github Pull Request 流程简述

### 我不懂编程，只是想改一点点 JSON 文件/文档等，要怎么操作？

欢迎收看 [牛牛也能看懂的 GitHub Pull Request 使用指南](https://maa.plus/docs/zh-cn/develop/pr-tutorial.html)

### 我有编程经验，但是没参与过相关项目，要怎么做？

1. 如果很久以前 fork 过，先在自己仓库的 `Settings` 里，翻到最下面，删除

2. 打开 [MaaStarResonance主仓库](https://github.com/AsterleedsGuild0/MaaStarResonance)，点击 `Fork`，继续点击 `Create fork`

3. 克隆你自己的仓库到本地，并使用 `--recursive` 拉取子模块

    ```bash
    # https clone
    git clone --recursive https://github.com/<你的用户名>/MaaStarResonance.git
    # ssh clone
    git clone --recursive git@github.com:<你的用户名>/MaaStarResonance.git
    ```

    > 如果 https clone 比较慢要使用代理 clone 的话可以如下设置:
    >
    > ```bash
    > # 设置 HTTP(s) 代理, 例如:
    > ## 全局
    > git config --global https.proxy http://127.0.0.1:7890
    > git config --global http.proxy http://127.0.0.1:7890
    > ## 当前目录所在仓库
    > git config https.proxy http://127.0.0.1:7890
    > git config http.proxy http://127.0.0.1:7890
    > 
    > # 取消代理配置
    > ## 取消全局代理配置
    > git config --global --unset https.proxy
    > git config --global --unset http.proxy
    > ## 取消当前目录所在仓库代理配置
    > git config --unset https.proxy
    > git config --unset http.proxy
    > ```
    >
    > ---
    >
    > 如果 ssh clone 比较慢需要使用代理 clone 的话可以如下设置 ``~/.ssh/config`. 对于 windows 而言可以是:
    >
    > ![image-20230921013914928](QuickStart.assets/202309210139983.png)

    如果先 clone 了仓库, 后续需要再初始化 Submodule:

    ```bash
    git submodule update --init --recursive
    ```

    ![image-20251108161838553](QuickStart.assets/image-20251108161838553.png)

4. 下载 MaaFramework 的 [Release 包](https://github.com/MaaXYZ/MaaFramework/releases)，解压到 `deps` 文件夹中。

    ![image-20251108162148858](QuickStart.assets/image-20251108162148858.png)

5. 配置编程环境

    - 安装 python(>=3.11, 最好是 3.13)

    - 安装 uv 并初始化虚拟环境:

        ```bash
        # windows
        powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
        ## macOS/Linux
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # 验证安装
        uv --version
        ```

        ![image-20251003192732297](QuickStart.assets/202510031927611.png)

        使用 uv 初始化虚拟环境:

        ```bash
        uv sync
        ```

        ![image-20251108162126637](QuickStart.assets/image-20251108162126637.png)

        使用 scripts 目录下的开发环境初始化脚本检查与初始化环境:

        ```bash
        uv run scripts/init_develop_environment.py
        ```

        ![image-20251108170954377](QuickStart.assets/image-20251108170954377.png)

    - 下载并安装vscode

        使用 VSCode 打开仓库目录, 然后安装推荐扩展:

        ![image-20251108162450766](QuickStart.assets/image-20251108162450766.png)

    - 选择性安装调试/开发工具

        | 工具 | 简介 |
        | --- | --- |
        | [MaaDebugger](https://github.com/MaaXYZ/MaaDebugger)(推荐) | 独立调试工具 |
        | [Maa Pipeline Support](https://marketplace.visualstudio.com/items?itemName=nekosu.maa-support)(推荐) | VSCode 插件，提供调试、截图、获取 ROI 、取色等功能 |
        | [MFA Tools(仅win)](https://github.com/SweetSmellFox/MFATools) | 独立截图、获取 ROI 及取色工具 |
        | [ImageCropper(不推荐)](https://github.com/MaaXYZ/MaaFramework/tree/main/tools/ImageCropper) | 独立截图及获取 ROI 工具 |

6. 开始开发

    开始愉快的改代码吧，开始前查看如下相关阅读文档:

    - [如何实现一个自己的MAA？MaaFramework集成教程来啦！_哔哩哔哩_bilibili](https://www.bilibili.com/video/BV1yr421E7MW/?spm_id_from=333.337.search-card.all.click&vd_source=bb4d7b2841dd4d0035c93d44ba5cf11a)： Maa 作者 MrEO 开发 MaaFramework 时制作的基础开发视频， 通过此视频可以帮助你从零开始学习使用 MaaFramework pipeline json 开发一些基本的功能

    - [MaaFW 的文档](https://maafw.xyz/docs): 我们的项目基于 MaaFramework 开发, 了解其工作原理与配置是必要的
    - [M9A 的开发者文档](https://1999.fan/zh_cn/develop/development.html): M9A 是 MaaFramework 的优秀实践, 其文档也比较优秀, 可以参考其文档
    - [M9A 的 Github 仓库](https://github.com/MAA1999/M9A)： M9A 是 MaaFramework 的优秀实践，如果有什么功能一时间没有想法的话可以看看 M9A 中是否有类似场景实现

7. git 操作

    使用 VSCode 开发的话， 侧边栏的 `源代码管理` 视图可以直接 UI 完成一些基本的 Git 操作, 例如 commit, push, pull

    ![image-20251108172318003](QuickStart.assets/image-20251108172318003.png)

    命令行的话通常用的最多的基本命令有：
    - `git add <file>`：添加文件到暂存区，`*` 代表全部文件
    - `git commit -m "message"`：提交暂存区到本地仓库。`message` 请遵循 [约定式提交规范](https://www.conventionalcommits.org/zh-hans/v1.0.0/)，让你的 commit 信息更加清晰
    - `git pull origin <branch>`：拉取远程仓库到本地仓库
    - `git push origin <branch>`：推送本地仓库到远程仓库

    > ⚠
    >
    > 开发过程中，每一定数量，记得提交一个 commit, 别忘了写上 message
    > 假如你不熟悉 git 的使用，你可能需要创建并切换到一个新的分支，而不是直接提交在 main 上
    > 这样你的提交就能在新的分支上生长，不会受到 main 更新的打扰

    ```bash
    git checkout -b <branch-name> # 创建并切换到新的分支
    ```

    完成开发后，推送你修改的本地分支到远程仓库（fork 的仓库）

    ```bash
    git push origin <branch-name>
    ```

    当 MAAStarResonance 仓库出现更改（如其他人的commit），你可能需要把这些更改同步到你的分支

    1. 关联 MaaStarResonance 原仓库：

        ```bash
        git remote add upstream https://github.com/AsterleedsGuild0/MaaStarResonance.git
        ```

    2. 拉取远程仓库更新：

        ```bash
        git fetch upstream
        ```

    3. 变基（推荐）或者合并修改：

        ```bash
        git rebase upstream/main # 变基，使commit历史更清晰，完成你的个人pr时建议使用rebase而不是merge来合并修改
        ```

        或者

        ```bash
        git merge upstream/main
        ```

    git 参考资料：
    - [pcottle/learnGitBranching: An interactive git visualization and tutorial. Aspiring students of git can use this app to educate and challenge themselves towards mastery of git!](https://github.com/pcottle/learnGitBranching): 可视化的 Git 操作学习
    - [git 官方文档](https://git-scm.com/docs)
    - [git 简明指南](https://www.runoob.com/manual/git-guide/)
    - [git 教程|菜鸟教程](https://www.runoob.com/git/git-tutorial.html)

8. 提交 Pull Request

    你修改的代码已经提交到你的仓库，现在你需要提交一个 Pull Request 到 M9A 的仓库，等待维护者审核

    [GitHub Pull Request 参考](https://maa.plus/docs/zh-cn/develop/pr-tutorial.html)

---

## MAAStarResonance 格式化要求

M9A 使用一系列的格式化工具来保证仓库中的代码和资源文件美观统一，以便于维护和阅读

请确保在提交之前已经格式化，或是[启用 Pre-commit Hooks 进行自动格式化](#利用 Pre-commit Hooks 自动进行代码格式化)

目前启用的格式化工具如下：

| 文件类型 | 格式化工具 |
| --- | --- |
| JSON/Yaml | [prettier](https://prettier.io/) |
| Markdown | [MarkdownLint](https://github.com/DavidAnson/markdownlint-cli2) |

![image-20251108175317310](QuickStart.assets/image-20251108175317310.png)

---

### 利用 Pre-commit Hooks 自动进行代码格式化

> [!NOTE]
>
> 实际协作中，在 vscode 中开发，安装推荐的插件后，基本就可以完成自动格式化了，故该部分可跳过。

1. 确保你的电脑上有 Python 与 Node 环境

2. 在项目根目录下执行以下命令

    ```bash
    pip install pre-commit
    pre-commit install
    ```

如果pip安装后依然无法运行pre-commit，请确认pip安装地址已被添加到PATH

接下来，每次提交时都将会自动运行格式化工具，来确保你的代码格式符合规范

手动触发：

```bash
pre-commit run --all-files
```

---
