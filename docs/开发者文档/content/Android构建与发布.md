---
title: Android 构建与发布
sidebar_label: Android 构建与发布
sidebar_position: 7
description: Android 签名 APK、GitHub Release、Mirror酱分发及不发版验证流程
keywords:
  - Android
  - GitHub Actions
  - Release
  - Mirror酱
hide_title: false
hide_table_of_contents: false
---

## 支持范围与真机记录

Android 使用 MaaFwApp，在 `1280x720 / 240 dpi` 虚拟屏运行，要求 Android 10 或以上，通过 root 或 Shizuku 连接特权服务。

**AZMIAO 已在自用红米 K80 Pro（root 环境）上测试通过。** 此记录来自维护者反馈，不等于本次 CI 进行了真机测试，也不代表 Shizuku、x64 设备、其他厂商系统或所有任务已逐项验收。新增设备仍应检查截图、输入、多指钓鱼、后台运行和覆盖安装。

先授予通知、电池白名单及 root/Shizuku 权限，运行「启动星痕共鸣」或「重启并登录星痕共鸣」，让游戏进入虚拟屏，再运行其他任务。桌面 Npcap 插件不进入 Android 包。

## 构建入口与发布边界

入口是 `.github/workflows/install.yml`，Android 实现位于可复用的 `android.yml`，不再单独运行原来的 **Android development APK**。

| 触发方式 | Android 构建 | Release 与 Mirror酱 |
| --- | --- | --- |
| 命中构建路径的普通分支推送 | 构建 arm64/x64 签名 APK | 不执行 |
| 在分支上手动运行 `install` | 构建 arm64/x64 签名 APK | 不执行 |
| Pull Request | 不使用签名 secrets，跳过 APK 构建 | 不执行 |
| 推送 `v*` tag | 构建 arm64/x64 签名 APK | 全部平台成功后发布，再同步 Mirror酱 |

构建路径包括工作流、`android/`、`assets/`、Python 文件、Android 依赖、项目 Python 配置、图标和许可文件。只修改文档不会触发 `install`，可手动运行验证。手动运行即使选中 tag 也不会创建 Release；正式发布必须通过 tag 的 push 事件。

Windows x64/ARM64、Android arm64/x64 与更新说明生成必须全部成功，`release` 才会执行。APK 构建失败不会发布只有桌面包的残缺版本。普通分支运行中，`release`、`mirrorchyan` 和 `mirrorchyan-release-note` 应显示 skipped。

## 版本、签名与固定依赖

- 正式 APK 的 `versionName`、载荷资源版本与文件名使用同一个完整 tag，例如 `v1.2.3` 或 `v1.2.3-beta.1`，不会沿用 `pyproject.toml` 的旧项目版本。
- 非发版构建使用 `v<最近基础版本>-ci.<run_number>.<run_attempt>.g<短SHA>`，避免开发包被误认成正式包。
- `versionCode = 100000000 + install.run_number × 100 + run_attempt`，两个 ABI 相同；预留旧 Android 开发包的低位计数区间，后续统一使用 `install` 的运行序号。覆盖安装需保持同一包名、签名，并避免安装更旧构建；不要重置该工作流的运行序号。
- 包名固定为 `io.github.asterleedsguild0.maastarresonance`，配置在 `android/build-config.json`；切换包名或证书不能按原包覆盖更新。
- 外壳 revision、Agent Core 校验和、MaaFramework 和 SDK/NDK/CMake 版本均固定于 `android/build-config.json`。客户端与 Python Agent 当前均为 MaaFramework `v6.0.0-beta.3`。

在仓库 Settings → Secrets and variables → Actions 配置：

| Secret | 用途 |
| --- | --- |
| `ANDROID_KEYSTORE_BASE64` | 长期签名 keystore 的 Base64 内容 |
| `ANDROID_KEYSTORE_PASSWORD` | keystore 密码 |
| `ANDROID_KEY_ALIAS` | 签名 key 的别名 |
| `ANDROID_KEY_PASSWORD` | key 密码 |
| `MirrorChyanUploadToken` | 已授权 `MaaStarResonance` 资源的 Mirror酱上传令牌 |

缺少签名配置时构建失败，不生成随机 debug 证书。开发工件与正式包共用永久签名，务必备份 keystore 和密码，禁止提交到仓库或打印到日志。

工作流验证签名证书指纹、包名、版本、ABI、Agent 运行时与原生库，并运行外壳的多指触控单测和资源检查。校验失败不上传 APK 工件。

## 产物与下载

Actions 工件名为 `MaaStarResonance-android-arm64`、`MaaStarResonance-android-x64`，保存 7 天；工件下载时 GitHub 自带 ZIP 容器，解开后安装其中的 APK。

正式 Release 附件直接提供：

```text
MaaStarResonance-android-arm64-<tag>.apk
MaaStarResonance-android-arm64-<tag>.apk.sha256
MaaStarResonance-android-x64-<tag>.apk
MaaStarResonance-android-x64-<tag>.apk.sha256
MaaStarResonance-win-x86_64-<tag>.zip
MaaStarResonance-win-aarch64-<tag>.zip
```

Release 不会再把 APK 套入 ZIP，也不会发布中间产物 `wheels-win-x64`。发布前再次校验 APK 的 SHA-256。红米 K80 Pro 等 ARM64 手机下载 arm64；x64 用于相应 Android x86_64 环境，不表示已经完成运行验收。

下载 APK 和同名 `.sha256` 到同一目录后，Linux 可用 `sha256sum --check <文件名>.apk.sha256`；PowerShell 可用 `Get-FileHash <文件名>.apk -Algorithm SHA256` 对照摘要。授权安装来源后覆盖安装，不需要卸载旧版；卸载可能丢失配置。

## Mirror酱分发

Release 附件上传完毕后，`install` 直接调用可复用的 `mirrorchyan.yml`，不再用异步 `gh workflow run` 查找 latest。上传和更新说明均绑定本次精确 tag，预发布与正式发布不会串包。

| os | arch | 上传文件 |
| --- | --- | --- |
| `win` | `aarch64` | 对应 Windows ARM64 ZIP |
| `win` | `x86_64` | 对应 Windows x64 ZIP |
| `android` | `arm64` | 对应 arm64 APK |
| `android` | `x64` | 对应 x64 APK |

资源 ID 沿用 `MaaStarResonance`。维护者需在 Mirror酱确认资源及令牌允许这四组平台/架构；GitHub secrets 的存在本身不证明服务端已开通 Android 分发。APK 原样上传，不解包、不重新压缩，`.sha256` 不作为安装包上传。

上传动作根据 tag 自动区分渠道：包含 `alpha` 为 alpha，包含 `beta` 或 `rc` 为 beta，其余为 stable。所有安装包同步成功后才同步该 tag 的更新说明；编辑非草稿 Release 时，更新说明工作流也使用被编辑 Release 的 tag。

:::warning
当前固定版本 MaaFwApp 的[官方接入文档](https://github.com/Aliothmoon/MaaFwApp/blob/1736e50deef562dc7bc0addf7c232a64897b55ac/INTEGRATION.md)明确写明暂不支持 Mirror酱。这里接入的是服务端 APK 分发，不是应用内自更新，也不是桌面资源包热更新。Android 资源随 APK 绑定，更新需要下载完整 APK 并覆盖安装。
:::

同步失败时已有 GitHub Release 不会回滚。可在 Actions 页面单独重跑失败任务，或手动运行 `mirrorchyan` 并填写已有 Release 的精确 `tag`；随后手动运行 `mirrorchyan_release_note`，填写同一个 tag。不要为重试创建新 tag，也不要用缺少 APK 的旧 Release 验证上传。

## 不发布新版本的验证

本地运行：

```bash
python -m unittest discover -s tests -p test_android_packaging.py -v
npm run docs:check
```

工作流修改还应使用 `actionlint` 检查 YAML、表达式、可复用工作流输入及权限。

推送普通分支，或在该分支手动触发：

```bash
gh workflow run install.yml --ref <分支名>
```

记录本次提交对应的 run URL，确认两个 Android ABI 与 Windows 构建通过，并下载工件核对文件名、摘要和签名检查步骤结果。确认发布及 Mirror酱任务 skipped，不能以实际上传作为“不发版验证”。CI 构建通过不等于真机运行通过。

验证阶段不要推送 `v*` tag，不要运行 Mirror酱上传工作流，不要创建 Release。本流程不会证明实际 Release 上传或 Mirror酱服务端接收成功；这两项在下一次获授权的正式发版时验收。

## 正式发布与故障定位

只有维护者明确决定发布新版本时，才按[发布说明](./开发随笔.md#发布)推送新 `v*` tag。本次补齐自动化不要求执行该步骤。

| 失败阶段 | 优先检查 |
| --- | --- |
| 固定签名准备 | 四个签名 secrets、keystore 密码和 alias，禁止换随机证书绕过 |
| 运行时或 APK 校验 | `build-config.json` 固定版本/摘要、ABI、Agent Core 和 MaaFramework 是否一致 |
| Android 成功但未出现 Release | 是否为 tag push；Windows 或更新说明是否失败 |
| Mirror酱找不到附件 | 精确 tag、APK 是否已上传、文件扩展名及架构命名 |
| Mirror酱拒绝上传 | 令牌权限、RID 及 Android 平台/架构是否开通；不影响已有 GitHub 附件 |
| 安装报签名冲突或版本降级 | 包名、永久证书与 `versionCode`；不要默认卸载以免丢失配置 |
| 安装成功但开始失败 | root/Shizuku 服务、启动游戏任务、应用内日志导出及 `adb logcat -s MaaFw` |
