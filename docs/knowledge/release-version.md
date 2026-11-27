---
sidebar_label: 版本更新与发布
---

# 版本更新与发布

只有用户明确要求更新版本并发布时，才执行以下流程；修改发版说明、排错或普通提交不构成发版授权。`v0.12.0` 仅为格式示例，实际使用用户指定且尚未发布的新版本，禁止复用、移动或强推已有 tag。文中命令和仓库文件路径均以项目根目录为基准。

## 1. 同步项目版本

历史 `tag📌` 提交（如 `fbb7573`、`b7a9696`）统一涉及以下 5 个文件。以目标版本 `X.Y.Z` 为例：

| 文件 | 版本字段 | 更新方式 |
| --- | --- | --- |
| `assets/interface.json` | 顶层 `version` 为 `vX.Y.Z` | 修改源文件，保留 JSONC 注释及其余资源配置。 |
| `pyproject.toml` | `[project].version` 为 `X.Y.Z` | 修改项目版本，不顺带升级 Python 或 MaaFW。 |
| `package.json` | 顶层 `version` 为 `X.Y.Z` | 修改文档站项目版本；它不是 Docusaurus 的依赖版本。 |
| `uv.lock` | `name = "maastarresonance"` 的包版本为 `X.Y.Z` | 修改 `pyproject.toml` 后运行 `uv sync`，同步锁文件及 `.venv`，不要手改锁文件。 |
| `package-lock.json` | 顶层 `version` 和 `packages[""].version` 均为 `X.Y.Z` | 修改 `package.json` 后由 npm 安装/更新命令同步，不手改传递依赖记录。 |

不要全库替换旧版本：历史更新日志、文档示例和测试夹具不属于发版版本字段。`android/build-config.json` 固定的是框架、外壳和工具链，不随项目版本例行递增；只有另行升级这些依赖时才修改。Android 正式包的 `versionName` 来自 tag 去掉 `v`，`versionCode` 由 `install` 工作流生成，不手工改计数。Android 的签名、构建与排错详见 [Android 构建与发布](../开发者文档/content/Android构建与发布.md)。

## 2. 同步 Python 并更新文档站依赖

1. 完成版本声明修改后运行 `uv sync`；它负责依赖同步，不等于无条件升级全部 Python 依赖。
2. 文档站使用 **npm**，先用 `npm install` 同步安装及项目版本，再用 `npm outdated` 检查更新；后者发现过期包时可能退出 1，不应直接当作安装失败。
3. 检查并更新现有全部 Docusaurus 包：`@docusaurus/core`、`@docusaurus/faster`、`@docusaurus/preset-classic`、`@docusaurus/module-type-aliases`、`@docusaurus/types`。选择相互兼容的同一稳定版本，保留原有 dependencies/devDependencies 分类；同时检查 `@mdx-js/react`、`react`、`react-dom`、`clsx`、`prism-react-renderer` 及其他现有文档站依赖。
4. `npm update` 只更新声明范围内的版本；需要更新版本范围时，使用 `npm install <包名>@<目标版本>`，开发依赖使用 `--save-dev`。先检查目标 Docusaurus 的 Node.js engines、peerDependencies 和迁移要求，必要时同步 `package.json` 与 CI 的 Node.js 版本；不使用 `--force`、`--legacy-peer-deps` 或 `npm audit fix --force` 掩盖不兼容。
5. 保留并一并提交 `package.json`、`package-lock.json` 的实际依赖更新；已经最新则记录检查结果，不制造无意义锁文件改动。不要使用默认会自动提交和打 tag 的 `npm version`，避免拆出额外发版提交。

所有版本、依赖及必要迁移改动完成后，再统一验证：`uv lock --check`、`npm run docs:check`；涉及 Android 版本/打包逻辑时运行 `uv run python -m unittest discover -s tests -p test_android_packaging.py -v`。按实际改动补充针对性检查，失败先修复，不带失败结果打正式 tag。运行结果与无法本地验证的范围必须如实记录。

## 3. 单次提交、打 tag 并推送

- 将本次授权范围内的版本字段、锁文件、依赖更新及必要迁移改动合为 **一个发版 commit**，不夹带无关工作。使用 eval 的 `commit` 命名空间选择并提交改动，不用 `git add` / `git commit` 全量收集工作区。
- 提交标题固定为 `tag📌: vX.Y.Z`，例如 `tag📌: v0.12.0`；不要追加描述或更换前缀。tag 名固定为同版本的 `vX.Y.Z`，并明确指向刚创建的发版提交。
- 确认远端及发布分支后推送 commit 和 tag，优先原子推送，避免只推成功一半：

```bash
git tag vX.Y.Z <发版提交SHA>
git push --atomic origin HEAD:<发布分支> refs/tags/vX.Y.Z
```

禁止借此重写已有 tag 或强推分支。不要再手动创建 Release、重复运行上传或另起发版提交来代替工作流。

## 4. 跟踪工作流与 Release

1. 推送 `v*` tag 会自动触发 `.github/workflows/install.yml` 的正式构建、Release 和 Mirror酱流程；普通分支推送或 `workflow_dispatch` 只构建，不发版。分支与 tag 同推可能产生多个 run，必须按**完整提交 SHA、tag 和事件**区分，跟踪 tag push 的发版 run，不能把分支 run 中发布任务 skipped 当成发版成功。
2. 记录对应 run URL，使用 `gh run watch <run-id> --exit-status` 等待完成；同时确认该提交触发的 `check`。检查 Windows x64/ARM64、Android arm64/x64、更新说明、`release`、Mirror酱四平台上传和更新说明同步全部完成且状态正常。失败时查看具体 job 日志，报告失败阶段，不反复推 tag 试错。
3. 工作流可能自动回写 `CHANGELOG.md` 并在默认分支生成机器人提交；发版 tag 仍应指向原发版提交，不因此挪动 tag 或把机器人提交误认作本次构建的 SHA。
4. 全部工作流完成后，用 `gh release view <tag>` 或 Release 页面确认目标版本已发布、不是草稿、预发布标记符合预期、更新说明存在，并核对附件齐全：Windows `x86_64` / `aarch64` 各一份 ZIP，Android `arm64` / `x64` 各一份 APK 及对应 `.apk.sha256`。按目标 tag 核对，不只看 latest。
5. 发布验证通过后，同步本地代码以拉取机器人回写的 Changelog 提交：确认本地当前位于机器人回写的默认分支（通常为 `main`），且工作区干净，再执行 `git pull --ff-only <远端> <默认分支>`。不在 tag 的 detached HEAD 上拉取，也不将默认分支合并进其他分支；若当前分支不符、存在未提交改动或无法快进，保留现场并报告未同步原因，禁止自动 stash、reset、强推或覆盖用户改动。同步本地分支不改变发版 tag 的指向。
6. 报告发版 commit、tag、工作流链接及结论、Release 链接，以及本地分支同步结果（包括是否拉取到机器人提交）。助手到此完成发布流程；Release 文件的下载、安装和实际游戏功能验证交给用户，不把 CI/附件存在等同于实机验收通过。
