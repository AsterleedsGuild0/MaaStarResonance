<!-- markdownlint-disable MD041 MD034 -->
<div align="center">
<img alt="LOGO" src="static/img/logo_transparent.png" width="256" height="256" />

# 星痕共鸣 MAA 小助手

基于图像识别的星痕共鸣自动化工具

由 [MaaFramework](https://github.com/MaaXYZ/MaaFramework) 强力驱动！  

<a href="https://github.com/AsterleedsGuild0/MaaStarResonance" style="font-weight: bold;">🔗 本项目 GitHub 仓库</a><br>

</div>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white">
  <img alt="platform" src="https://img.shields.io/badge/platform-Windows-blueviolet">
  <img alt="license" src="https://img.shields.io/github/license/MAA1999/M9A">
  <br>
  <img alt="commit" src="https://img.shields.io/github/commit-activity/m/AsterleedsGuild0/MaaStarResonance">
  <img alt="stars" src="https://img.shields.io/github/stars/AsterleedsGuild0/MaaStarResonance?style=social">
  <img alt="downloads" src="https://img.shields.io/github/downloads/AsterleedsGuild0/MaaStarResonance/total?style=social">
</p>

---

## 界面预览

- 如果觉得还算好用请给我们的项目点个收藏支持一下⭐

![image-20260109134752](docs/关于/关于我们.assets/image-20260109134752.png)

---

## 声明与许可

- 本项目采用 [`AGPL-3.0`](LICENSE) 许可证进行开源
- 本资源按"现状"提供，不附带任何形式的明示或暗示担保。使用者需自行承担所有风险
- 作者不对因使用本资源而导致的任何直接、间接或结果性损失承担责任
- 基于本资源进行的任何商业行为均与原作者无关，使用者不得暗示任何官方关联或认可
- 项目图标来源: [艾露娜Q版表情包全套高清修复分享｜星痕共鸣｜腾讯频道](https://pd.qq.com/g/pd34199182/post/B_e60f346878db0d001441152189808449200X60)

---

## 功能列表

> 桌面版使用 Windows + MuMu 模拟器；Android 开发版使用 MaaFwApp + Shizuku/root，在 `1280x720 / 240 dpi` 虚拟屏运行，要求 Android 10 或以上。Android 尚待真机验收，不代表所有任务均已验证。
>
> 您可以采用多个配置页、复制、排列、组合任务列表的方式来完成日常

- 日常功能
  - 自动钓鱼
  - 简易采集
  - 挑战不稳定空间
  - 领取今日活跃度奖励
- 挂机功能
  - 挂机自动批复入队申请
  - 聊天频道发言
  - 周期性聊天频道发言
  - S2浮游之茧
  - 自动接受协会狩猎邀请和战斗
- 游星岛功能
  - 游星岛暴打陈敏小游戏
  - 游星岛躲猫猫小游戏
  - 游星岛镭射回旋小游戏
  - 游星岛极限落潮小游戏
  - 游星岛浪花躲避球小游戏
  - 游星岛游鱼暴走小游戏
  - 游星岛麻将挂机小游戏
  - 游星岛环城载具赛小游戏
- 其他功能
  - 启动并登录游戏
  - 关闭所有广告弹窗
  - 地图传送
  - 地图导航
  - 切换分线

---

## 文档

- 在线文档入口: [星痕共鸣 Maa 小助手](https://maa-star-resonance.ayusummer233.top)

### Android 开发包

- Actions 的 **Android development APK** 构建 arm64/x64 APK，仅保存开发工件，不发布 Release 或接入自更新。
- 外壳、Agent Core 与工具版本固定于 `android/build-config.json`；客户端与 Python Agent 均使用 MaaFramework `v6.0.0-beta.3`，不自动降级。
- 包名使用本仓库身份 `io.github.asterleedsguild0.maastarresonance`，在 `android/build-config.json` 的 `app.applicationId` 配置，由 Gradle 初始化脚本覆盖外壳默认前缀。旧包只有证书一致才可覆盖安装；切换外壳不保证继承旧配置。
- 仓库需要 `ANDROID_KEYSTORE_BASE64`、`ANDROID_KEYSTORE_PASSWORD`、`ANDROID_KEY_ALIAS`、`ANDROID_KEY_PASSWORD` 四个 secrets。构建后核对真实证书指纹；缺配置会失败，不回退到随机 debug 证书。
- 安装后授予 Shizuku/root、通知和电池白名单权限，先运行「启动星痕共鸣」或「重启并登录星痕共鸣」，再运行其他任务。桌面 Npcap 插件不打入 Android。
- MaaFwApp 已贯通多指触控并使用 `specialUse` 保活；仍需在设备上验收双指钓鱼、截图、键盘输入、后台长跑和覆盖安装，不能保证厂商系统不会杀后台。

本地预处理与检查（Python 3.13）：

```bash
python -m unittest discover -s tests -p test_android_packaging.py -v
python android/prepare.py --abi arm64-v8a --version-code 10101
git clone https://github.com/Aliothmoon/MaaFwApp.git android/MaaFwApp
git -C android/MaaFwApp checkout 1736e50deef562dc7bc0addf7c232a64897b55ac
python android/build_runtime.py --abi arm64-v8a
```

配方位于 `android/.build/profile.json`，载荷和解释器分别位于同目录的 `payload/`、`agent-dist/`。完整出包使用工作流中固定的 JDK 25、SDK 37、NDK 29 与外壳 Gradle Wrapper；`PI_PROFILE` 指向配方，设置与 `app.applicationId` 一致的 `BUILD_APPLICATION_ID`、`BUILD_VERSION_NAME`、递增的 `BUILD_VERSION_CODE` 和四个 Gradle 签名环境变量，通过 `android/maafwapp.init.gradle` 构建。RapidFuzz 在构建期生成官方纯 Python wheel；Android 不安装桌面 MaaFw wheel 或在设备上运行 pip。

接入依据：[MaaFwApp 官方文档](https://github.com/Aliothmoon/MaaFwApp/blob/1736e50deef562dc7bc0addf7c232a64897b55ac/INTEGRATION.md)、[M9A Android 配方](https://github.com/MAA1999/M9A/tree/main/Android)、[MaaYuan 签名与版本实践](https://github.com/syoius/MaaYuan/blob/v5/android/README.md)。


---

## 插件

> 自 `v0.11.0` 之后版本已支持插件侧载，可以实现一些拓展能力，插件安装请参考文档：[插件安装与使用](https://maa-star-resonance.ayusummer233.top/docs/功能文档/插件使用/)

---

## 鸣谢

- 本项目由 **[MaaFramework](https://github.com/MaaXYZ/MaaFramework)** 强力驱动！  
- 桌面 UI 由 [MFAAvalonia](https://github.com/MaaXYZ/MFAAvalonia) 提供，Android 开发版使用 [MaaFwApp](https://github.com/Aliothmoon/MaaFwApp)。
- 感谢以下开发者对本项目作出的贡献:

[![Contributors](https://contrib.rocks/image?repo=AsterleedsGuild0/MaaStarResonance&max=1000)](https://github.com/AsterleedsGuild0/MaaStarResonance/graphs/contributors)

---

## 协会招募

阿斯特里斯零协会（ID：14130）招人啦~

保持活跃即可，有协会Q群，有OOPZ语音频道，每周有团本车~

协会群里有玩 084、二重、PCR、MC、战地 等各种游戏的群友，欢迎加入我们协会，~~一起带薪群聊~~

协会直接搜ID进即可，也欢迎其他协会前来合会~

![image-20251125113159](docs/关于/关于我们.assets/image-20251125113159.png)

## 友情链接

- [另一款 MAA Star Resonance](https://github.com/26F-Studio/maa-star-resonance)
  这是一个由 [Particle_G](https://github.com/ParticleG) 开发的星痕共鸣MAA小助手，使用 Electron + 文本图像识别 + ADB模拟控制 技术实现
