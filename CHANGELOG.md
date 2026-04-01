# 更新日志

## 0.8.1 (2026-04-01)

### 🐛 Bug修复

- 修复优化CHANGLOG #48 #73 (#90) @azmiao (Co-authored: sourcery-ai[bot])
- 尝试修复CHANGELOG作者异常问题 @azmiao
- 修复躲猫猫队员端未处理省电模式的问题 (#89) @azmiao (Co-authored: 233Official)
- 处理因为仓库迁移到组织导致的更新异常问题 @233Official

### 🚀 性能优化

- 作者名缓存异常时自动重建 @azmiao
- 麻将新增对局前等待超时时长设置 (#85) @azmiao

### 🧹 日常维护

- 更新脚手架脚本和文档 @azmiao
- 删除队长端的追逃游戏速刷入口（游戏BUG已修复） @azmiao
- 修改麻将日志打印内容 @azmiao

### 🧩 修改依赖

- 更新MFAA至v2.11.8 @azmiao

### 📌 发布

- v0.8.1 @azmiao

### ⚙️ 持续集成

- 新增版本更新时自动更新CHANGELOG.md @azmiao
- 修复仅在Tag时触发更新CHANGELOG @azmiao

## 0.8.0 (2026-03-29)

### ✨ 新功能

- 合并提交 - 新增躲猫猫速刷功能 & 麻将挂机功能（支持单人/组队队长/组队队员） (#84) @azmiao (Co-authored: 233Official)
- 搭建躲猫猫小游戏匹配模式基本架构逻辑 @azmiao
- 新增躲猫猫不同队伍模式的基本架构逻辑 @azmiao
- 添加躲猫猫小游戏的任务接口 @azmiao
- 不思议的追讨游戏_速刷_队员端 @233Official
- 不思议的追逃游戏_速刷_队长端 @233Official
- 新增麻将挂机的基本逻辑框架，整理代码结构 @azmiao
- 新增单人匹配模式的麻将挂机功能 @azmiao

### 🐛 Bug修复

- 补充完整躲猫猫正常挂机逻辑 @azmiao
- 兼容四人组队麻将队长和队员模式 @azmiao
- 修复计数问题 @azmiao

### 📚 文档

- 更新文档 @azmiao

### 🧹 日常维护

- 迁移躲猫猫和麻将合并至一个文件夹 @azmiao

### 🧩 修改依赖

- 更新MFAA至v2.11.6 @azmiao

### 📌 发布

- v0.8.0 @azmiao

## 0.7.1 (2026-03-24)

### 🐛 Bug修复

- 去除冗余的传送导航地图检测 @azmiao

### 🚀 性能优化

- 优化暴打陈敏逻辑，修复切线BUG @azmiao

### 🧩 修改依赖

- MFAA更新至v2.11.4 @azmiao

### 📌 发布

- v0.7.1 @azmiao

## 0.7.0 (2026-03-21)

### ✨ 新功能

- 合并提交 - 新增不稳定空间挑战和暴打陈敏小活动 (#83) @azmiao
- 新增开发版本的上下载具和开关自动战斗的函数 @azmiao
- 新增战斗时视角旋转的函数 @azmiao
- 新增开发版本检测复活函数 @azmiao
- 新增开发版本不稳定空间自动战斗功能 @azmiao

### 🐛 Bug修复

- 修复不稳定空间功能流程 @azmiao
- 修复转动视角持续时间参数错误 @azmiao
- 同步退出副本按钮的绿幕识别参数 @azmiao
- 修复游星岛传送问题 @azmiao
- 修复暴打陈敏计数问题 @azmiao
- 修复小游戏切分线逻辑判断 @azmiao

### 🚀 性能优化

- 更换部分识别为绿幕的模板识别 @azmiao
- 自动钓鱼新增导航至钓鱼点的选项 @azmiao
- 新增游星岛暴打陈敏活动方法 @azmiao
- 优化修复暴打陈敏接口 @azmiao

### 📚 文档

- 更新文档，优化接口描述 @azmiao
- 更新README.md @azmiao
- 更新说明文档 @azmiao

### 🧹 日常维护

- 补充不稳定空间参数 @azmiao
- 调整主接口，新增不稳定空间入口 @azmiao
- 补充导航点数据 @azmiao

### 🧩 修改依赖

- MaaFw更新至v5.9.1，MFAA更新至v2.10.9 @azmiao
- 更新上下载具、开关自动战斗的参数 @azmiao
- MaaFw更新至v5.9.2 @azmiao
- 更新MFAA至2.11.3 @azmiao

### 📌 发布

- v0.7.0 @azmiao

## 0.6.3 (2026-03-09)

### 🐛 Bug修复

- 优化修复部分场景下钓鱼上钩判断异常 @azmiao

### 🚀 性能优化

- 自动钓鱼相关功能大幅优化 (#82) @azmiao (Co-authored: dependabot[bot])
- 优化钓鱼逻辑，将张力满检测改为根据张力值检测 @azmiao
- 自动钓鱼新增检测周期补偿逻辑，重构收线检测逻辑，降低资源消耗，提高钓鱼成功率 @azmiao
- 修改循环检测间隔减少箭头识别丢失概率 @azmiao

### 📚 文档

- 更新本项目官网链接 @azmiao
- 更新新手上路的前置文档 @azmiao
- 更新README @azmiao

### 🧩 修改依赖

- *(deps)* bump actions/download-artifact from 7 to 8 (#77) @dependabot[bot] (Co-authored: dependabot[bot])
- *(deps)* bump actions/upload-artifact from 6 to 7 (#76) @dependabot[bot] (Co-authored: dependabot[bot])
- 更新MFAA版本至v2.10.5 @azmiao
- 更新MFAA至v2.10.7 @azmiao

### 📌 发布

- v0.6.3 @azmiao

### ⚙️ 持续集成

- 适配MFAA仓库变化版本改图标的Ci @dependabot[bot]

## 0.6.2 (2026-03-05)

### ✨ 新功能

- 新增切换分线功能和接口 @azmiao
- 新增通用版本刷茧的开发版本 @azmiao

### 🐛 Bug修复

- 修复钓鱼超时会强制重启游戏的BUG @azmiao
- 补充类型声明 @azmiao

### 🚀 性能优化

- 为自动钓鱼补充切换分线功能 @azmiao
- 优化聊天框频道ID识别效果 @azmiao
- 地图传送导航支持自动根据传送点判断地图 @azmiao

### 📚 文档

- 更新整理软件客户端的公告页面 @azmiao
- 更新README.md @azmiao
- 更新部分文档和README @azmiao
- 优化和修复文档站点部署 (#75) @azmiao
- 更新和优化文档站点URL问题 @azmiao
- 规范部分文档内容格式，防止出现broken url 和 broken author @azmiao
- 更新客户端公告中的文档链接，顺便加个协会宣传（ @azmiao

### 🧹 日常维护

- 补充uv.lock @azmiao
- 版本统一调整为v0.6.2 @azmiao

### 🧩 修改依赖

- MaaFw更新至v5.3.0，MFAA更新至v2.3.0 @azmiao
- MaaFw更新v5.3.2，MFAA更新v2.5.0 @azmiao
- MFAA更新至v2.5.1 @azmiao
- MaaFw更新至v5.3.3 @azmiao
- 更新MaaFw至5.5.0，更新MFAA至2.5.7 @azmiao
- 更新MaaFw至5.8.1，更新MFAA至2.9.1 @233Official

### 📌 发布

- v0.6.2 (#78) @233Official (Co-authored: azmiao)

### ⚙️ 持续集成

- 尝试适配新版MFAA的编译流 @azmiao
- 不再手动编译 MFAA @233Official
- 补充打包时遗漏的图标文件 @233Official

## 0.6.1 (2025-12-28)

### ✨ 新功能

- 新增自动化部署文档站点 (#74) @azmiao (Co-authored: sourcery-ai[bot])

### 📚 文档

- 新增初版文档页面和依赖 @azmiao
- 更新更加简洁干净的文档主页面 @azmiao
- 对多次使用的图片去重 @azmiao

### 🧹 日常维护

- 去除Vercel的评论功能 @azmiao
- 补充去除不需要的配置 @azmiao
- 补充去除不需要的静态文件 @azmiao

### 🧩 修改依赖

- MFAA更新至v2.2.7 @azmiao

### 🔁 还原提交

- 去除CI文档的手动构建，还是自动方便 @azmiao

### ⚙️ 持续集成

- 新增手动或TAG触发文档部署工作流 @azmiao

## 0.6.0 (2025-12-25)

### ✨ 新功能

- 挂机自动批复入队申请 @233Official
- 尝试新增游戏聊天消息发送功能，部分静态资源来自Particle_G @azmiao
- 尝试新增地图导航功能 @azmiao
- 发送消息功能新增可选检测队伍人数功能 @azmiao
- 消息发送功能新增选项，控制队伍已满时是否还需发送 @azmiao
- 离线打包支持指定mfaa,maafw版本(#66) @233Official

### 🐛 Bug修复

- 补充导航功能所需资源和数据 @azmiao
- 修复默认值错误 @azmiao
- 尝试修复弹窗广告检测beta @azmiao
- 修复消息发送逻辑错误和补充坐标 @azmiao
- 尝试修复潜在的异步队列下字符串格式化异常导致的日志不打印问题 @azmiao
- 去除会报错的类型声明 @azmiao
- 尝试修复未解锁的钓鱼配件位置不同的问题，#71 @azmiao
- 修复Rect引用缺失 @azmiao

### 🚀 性能优化

- 优化 Release Info 生成机制, 不再使用 git cliff, 通过自定义 py 脚本实现 @233Official
- 优化 CHANGELOG 生成逻辑, 添加本地昵称用户名映射 @233Official
- 尝试提高聊天检测识别率 @azmiao
- 聊天框频道发言新增频道切换成功检测 @azmiao
- 补充坐标和匹配图标 @azmiao
- 优化弹窗广告处理逻辑，同步钓鱼时的广告处理 @azmiao
- 优化通用方法中的任务中断检测，修复部分变量赋值问题 @azmiao
- 优化消息发送部分场景处理，补充队伍名变量读取，优化接口描述 @azmiao
- 优化消息发送逻辑，提高稳定性 @azmiao
- 优化传送导航部分场景检测和操作，新增75级茧的导航选项 @azmiao

### 🎨 代码重构

- 优化 changelog 生成脚本 @233Official
- 优化聊天消息发送功能 @azmiao
- 重构部分聊天消息发送逻辑，新增对应选项参数 @azmiao
- [核心] 更换logger中format格式化为sink，防止变量参数被意外格式化 @azmiao

### 🥚 格式化

- 顺便统一格式化一下attach中的打印 @azmiao
- 优化购买道具的异常退出逻辑，优化接口描述 @azmiao

### 📚 文档

- 删除旧版本手写changelog @233Official
- 更新README，更新用户手册 @azmiao
- 更新README @azmiao

### 🧹 日常维护

- 更新commit模板、cliff模板、pr模板，更新vscode配置文件 @azmiao
- 更新BUG反馈的模板 @azmiao
- changelog强制UTF-8解码 @azmiao

### 🧩 修改依赖

- *(deps)* bump actions/upload-artifact from 5 to 6 @dependabot[bot]
- *(deps)* bump actions/download-artifact from 6 to 7 @dependabot[bot]
- *(deps)* bump actions/cache from 4 to 5 @dependabot[bot]
- *(deps)* bump actions/github-script from 7 to 8 @dependabot[bot]
- *(deps)* bump actions/setup-python from 5 to 6 @dependabot[bot]
- *(deps)* bump actions/upload-artifact from 4 to 5 @dependabot[bot]
- *(deps)* bump actions/download-artifact from 4 to 6 @dependabot[bot]
- *(deps)* bump actions/checkout from 4 to 6 @dependabot[bot]
- MaaFw更新至5.2.5，MFAA更新至2.2.0 @azmiao
- MaaFw更新至5.2.6，MFAA更新至2.2.1 @azmiao
- MFAA更新至v2.2.2 @azmiao
- MFAA更新至2.2.4 @azmiao
- MaaFw更新至v5.3.0-beta.5，MFAA更新至v2.2.5 @azmiao
- MFAA更新至v2.2.6 @azmiao

### 🧪 测试

- 每130s释放一次一号位幻想 @233Official

### 📌 发布

- v0.6.0 (#72) @azmiao (Co-authored: Copilot)
- v0.6.0 @azmiao

### 🔧 配置文件

- 更新 Github Copilot 全局提示词 @233Official

### ⚙️ 持续集成

- 去除已经不需要的获取最新TAG任务 @azmiao

## 0.5.8 (2025-12-08)

### ✨ 新功能

- 合并补充广告关闭 @azmiao
- 新增两个 custom reco, 当所有/任一 reco节点识别成功时认为识别成功 @233Official
- 打开与识别补偿商店页面 @233Official
- 钓鱼优化环境检测性能，补充关闭弹窗广告逻辑 @azmiao
- 新增关闭所有弹窗广告功能·其一 @azmiao
- 尝试新增选择地图传送的外部接口 @azmiao
- 增加动态包引入特性，重构部分引用代码结构，并将不同功能的代码分开整理 @azmiao

### 🐛 Bug修复

- 修复 Release Note 中作者链接错误的问题(#46) @233Official
- 修复 Release Note 无法处理多行标准 commit message 的问题(#48) @233Official
- 修复 utils 导入失败的问题 @233Official
- 修复钓鱼时间统计显示BUG @azmiao
- 修复默认包导入问题 @azmiao
- 修复开发环境注释问题 @azmiao
- 修复和优化包安装与引用，更新MaaFW至5.1.3 @azmiao
- 编译依赖前的logger还原为print，调整agent子模块为自动导入 @azmiao

### 🚀 性能优化

- 优化初始化逻辑, 当 pyproject 没有变动时不再尝试安装依赖(#54) @233Official
- 优化 Release Info 解析(#48) @233Official
- 优化初始化时的日志打印, 添加 mfaa 规定前缀以支持在 mfaa 中显示 @233Official
- 优化自动钓鱼识别参数性能 @azmiao
- 将传送模块独立，优化传送检测，提取便于直接调用的方法 @azmiao

### 🎨 代码重构

- 延长默认超时时间，拆分等待登录检测和切换场景检测 @azmiao
- 优化钓鱼环境检测逻辑，调整钓鱼参数 @azmiao
- 根据 PR Review 规范化代码与配置 @233Official

### 🥚 格式化

- 规范化页面识别相关常量与工具类代码 @233Official
- 尝试修改日志格式 @azmiao

### 🧩 修改依赖

- *(deps)* bump maafw from 5.1.3 to 5.1.4 @dependabot[bot]
- *(deps)* bump maafw from 5.1.0 to 5.1.3 @dependabot[bot]

### 📌 发布

- v0.5.8 (#57) @233Official (Co-authored: azmiao)
- v0.5.8 @233Official

### 🔧 配置文件

- Maafw更新至5.2.0 @azmiao
- 固定 maafw 的版本为 5.2.0 @233Official
- 在 CI 中固定 MFAA 版本为 2.1.7 @233Official
- dependabot 不再跟踪 uv lock 更新, 转而跟踪 github actions 更新 @233Official
- 在CI 中固定 maafw 版本为 5.2.0 @233Official
- 升级MFAA到 v2.1.8 @233Official

### 🚧 进行中

- 页面识别 @233Official

## 0.5.7 (2025-11-30)

### ✨ 新功能

- 自动钓鱼新增最大重启游戏次数限制 @azmiao
- 新增更加稳定可控的重启并登录星痕共鸣的功能 @azmiao
- 新增钓鱼时间统计和平均钓鱼时长统计 @azmiao
- 添加启动/关闭/重启游戏接口 @azmiao

### 🐛 Bug修复

- 更新适配MAA5.1.0，尝试更新V2接口参数兼容MFAA2.0 @azmiao
- 尝试修复CI中NuGet使用证书错误的国内镜像问题 @azmiao
- 修复钓鱼任务多次触发后统计数量不清空的问题 @azmiao

### 🚀 性能优化

- 自动钓鱼去除同方向识别冷却，微调部分参数以保障游戏稳定性 @azmiao

### 📚 文档

- 调整接口参数，新增联系方式文档 @azmiao
- 更新README @azmiao

### 🧩 修改依赖

- *(deps)* bump pre-commit from 4.4.0 to 4.5.0 (#51) @dependabot[bot] (Co-authored: dependabot[bot])

### 🔁 还原提交

- Revert "fix🐛: 尝试修复CI中NuGet使用证书错误的国内镜像问题" @azmiao

### 📌 发布

- v0.5.7 @azmiao

## 0.5.6 (2025-11-24)

### 📚 文档

- 添加公告文档 (#50) @233Official

### 📌 发布

- v0.5.6 @233Official

## 0.5.5 (2025-11-23)

### ✨ 新功能

- 新增获取不可恢复异常是否重启游戏的选项 @azmiao
- 新增钓鱼如遇到不可恢复异常是否重启游戏的节点选项 @azmiao

### 🐛 Bug修复

- CI编译过滤beta版本的tag @azmiao
- 尝试修复获取MFAA最新TAG的问题 @azmiao

### 🚀 性能优化

- 初始模式暂时替换为节奏模式，防止可能出现按钮按不住的情况，整理代码结构，微调部分参数 @azmiao
- 新增更强的钓鱼方向判断处理逻辑，优化张力检测，优化初始模式稳定性 @azmiao
- 优化张力检测，提高钓鱼稳定性 @azmiao
- 修改箭头检测冷却时间，更新"上钩"为"咬钩"避免歧义 @azmiao
- 新增等待鱼鱼上钩超时处理 @azmiao

### 🥚 格式化

- 去除无用的节点，整理通用节点至general.json @azmiao

### 📚 文档

- 更新钓鱼文档 @azmiao
- 更新自动钓鱼点选择的文档 @azmiao

### 📌 发布

- v0.5.5 @azmiao

### 🔧 配置文件

- 修改只拉取MFAA最新TAG对应的单次提交的代码 @azmiao
- 新增DependaBot自动更新依赖 @azmiao
- 修改PR提交模板说明 @azmiao

## 0.5.4 (2025-11-20)

### ✨ 新功能

- 新增更加稳健的钓鱼循环检测，新增钓鱼结果和统计信息显示，新增两个可通用的工具方法 @azmiao

### 🐛 Bug修复

- 尝试修复支持.NET 10 @azmiao

### 🚀 性能优化

- 增加箭头方向冷却时间，提高稳定性 @azmiao
- 优化性能，优化打印日志显示 @azmiao

### 📚 文档

- 更新用户文档 @azmiao
- 更新文档，支持MFAA最新所需的.NET 10 @azmiao

### 📌 发布

- v0.5.4 @azmiao

### 🔧 配置文件

- MAAFW更新至5.0.5 @azmiao

## 0.5.3 (2025-11-19)

### 🐛 Bug修复

- 不在向Mirror酱推送不再支持的 Linux/macOS Releases @233Official

### 📚 文档

- 添加公告文档 @233Official
- 暂时移除公告中的图片以免程序报错 @233Official

### 🧹 日常维护

- ✨ feat:  claim-activity-rewards (#47) @233Official

### 📌 发布

- v0.5.3 @233Official

### 🔧 配置文件

- 新增领取今日活跃度奖励 task 接口 @233Official

## 0.5.2 (2025-11-18)

### ✨ 新功能

- 新增指定应用的 启动、关闭、重启 的管道节点支持 @azmiao
- 自动钓鱼尝试新增掉线检测和切线检测 @azmiao
- 新增钓鱼总接口的最大成功钓鱼数量填空 @azmiao
- 自动钓鱼支持设置最大成功数量 @azmiao
- 新增领取每日活跃度奖励功能 (#29) @233Official (Co-authored: Copilot)
- 新增回到主页面的节点以及函数装饰器 @233Official
- 新增退出省电模式的函数装饰器 @233Official
- 领取每日活跃度奖励 @233Official

### 🐛 Bug修复

- 修复BUG，提高钓鱼入口判断稳定性 @azmiao

### 🚀 性能优化

- 优化修复启动、关闭、重启指定APP功能 @azmiao

### 🥚 格式化

- Code Format @233Official

### 📚 文档

- 更新自动钓鱼文档，修复一处赋值校验问题 @azmiao

### 📌 发布

- v0.5.2 @azmiao

### 🔧 配置文件

- 禁用其他系统架构CI发布，移动PR模板路径 @azmiao
- Android adb key event 新增 ESC 按键的值 @233Official

## 0.5.1 (2025-11-16)

### 🐛 Bug修复

- 补充回格式化丢失的项目包 @azmiao
- 修改CI中Tera不支持的空格错误 @azmiao
- 尝试修复release的changelog打印pr的commits不全 @azmiao
- 修复自定义传送的一处错误 @azmiao

### 🚀 性能优化

- 延长购买钓鱼配件的等待时间以保障低配置模拟器的稳定 @azmiao
- 优化内存泄漏，优化通用方法 @azmiao

### 🥚 格式化

- 添加标准的isort配置 @azmiao
- 格式化PEP8标准的import顺序，修复部分pylance声明检查错误 @azmiao

### 📚 文档

- 新增自动钓鱼文档 @azmiao

### 📌 发布

- v0.5.1 @azmiao

### 🔧 配置文件

- 添加PR模板说明 @azmiao

## 0.5.0 (2025-11-16)

### ✨ 新功能

- 测试版自动钓鱼，图片和逻辑参考自 Particle_G ，感谢❤️ @azmiao
- 重构自动钓鱼逻辑和代码结构，支持部分参数配置 @azmiao

### 🐛 Bug修复

- 自动钓鱼异步改为同步，修复传参错误 @azmiao
- 修复设备输出控制器问题，调整游戏区服选项 @azmiao
- 修复钓鱼箭头判断出错 @azmiao
- 同步接入点新的节点 @azmiao
- 修复购买鱼饵失败问题 @azmiao
- 优化run_recognition回参适配MaaFW5.0+ @azmiao

### 🚀 性能优化

- 优化钓鱼逻辑 @azmiao
- 优化钓鱼性能，优化钓鱼逻辑，优化退出逻辑 @azmiao
- 优化收线结束检测逻辑 @azmiao
- 降低轮询间隔提高稳定性，尝试优化内存泄漏（无济于事 @azmiao
- 优化方向键转向冷却，修复鱼竿鱼饵选择接口 @azmiao
- 更新VSCODE推荐拓展 @azmiao
- 调整interface @azmiao

### 🥚 格式化

- 格式化代码 @azmiao
- 增加注释 @azmiao

### 🧹 日常维护

- 新增自动钓鱼功能 (#22)(#4) @azmiao (Co-authored: 233Official)

### 📌 发布

- v0.5.0 @233Official

### 🔧 配置文件

- 添加建议扩展并配置basic pylance @azmiao
- 更新MaaFW至5.0.3 @azmiao

## 0.4.0 (2025-11-12)

### 🧹 日常维护

- 新增自适应绿毛图标 & 新增自定义图标CI编译支持 & 更换更可靠的矩阵式多平台编译 & 其他CI优化 (#18)(#14) @azmiao (Co-authored: Copilot)
- 🔧build: 新增Win平台自适应分辨率的图标 @azmiao

### 📌 发布

- v0.4.0 @233Official

### ⚙️ 持续集成

- 新增Win平台绿毛图标可执行文件打包的支持，修改更可靠的矩阵式多平台编译方式，增强编译过程中的稳定性 @azmiao
- Remove unnecessary "）" @azmiao

## 0.3.1 (2025-11-12)

### ✨ 新功能

- add mirrorchyan uploading @MistEO

### 🐛 Bug修复

- 忘记把测试时候的 false 重新打开了 @233Official
- 移除 1500ms 的识别速率限制, 退回默认的 1000ms, 修改错误的注释 @233Official
- 修复一处正则匹配过于宽泛的错误(#9) @233Official

### 🚀 性能优化

- 适应性调整本地编译逻辑 @233Official
- 优化简易采集逻辑, 新增简易采集流程文档(#6) (#16) @233Official
- 优化简易采集逻辑, 新增简易采集流程文档(#6) @233Official

### 📚 文档

- 更新 S2自动刷茧以及简易采集相关文档 @233Official
- 文档目录结构调整 @233Official

### 📌 发布

- v0.3.1 @233Official

### 🔧 配置文件

- 更新开发文档uv环境检查命令，同步uv.lock版本号 @azmiao

### ⚙️ 持续集成

- filename typos @MistEO

## 0.3.0 (2025-11-10)

### ✨ 新功能

- 简易采集 @233Official

### 🐛 Bug修复

- update cache id (#9) @233Official
- 修复因为 cache 导致的报错问题(#9) @233Official
- 为 install 添加等待 prepare wheels 的限制(#9) @233Official
- 尝试修复 wheels 找不到的问题 @233Official
- 修复 wheels 拷贝异常的问题 @233Official
- 修复wheels目录错误的问题(#9) @233Official
- 尝试修复 Actions 找不到脚本的问题(#9) @233Official
- 尝试修复依赖安装报错问题(#9) @233Official
- 尝试修复解除 agent main 安装依赖注释后缩进错误的问题(#9) @233Official
- 尝试修复  Release 包无法正常安装依赖的问题 @233Official
- 尝试修复Windows下python找不到的问题(#9) @233Official
- 修复Windows下python找不到的问题(#9) @233Official
- 尝试修复 Actions 中 python zip 找不到的问题(#9) @233Official
- 修复 Actions 中 python zip 找不到的问题(#9) @233Official
- 修复 interface..json 不支持注释的问题(#9) @233Official
- 尝试修复 actions 运行时的 loguru 报错(#9) @233Official
- 尝试修复 Actions 中 install py 调用 agent 包异常的问题(#9) @233Official
- 尝试修复 Actions 中 install py 调用 agent 包异常的问题 @233Official
- 补充 get-pip 漏掉的 url(#9) @233Official
- 尝试修复 Actions 打包报错(#9) @233Official
- 修复 Actions - Check Resource 脚本找不到的问题 @233Official
- 尝试修复灰色闪屏影响环境退出按钮判断的问题(#8) @233Official
- 添加游戏灰屏识别(#8) @233Official
- 修复一系列挂机Lv10浮梦之茧的识别问题(#8) @233Official
- OCR 退出 字样以修复识别退出按钮因为背景变动导致识别失败从而导致程序异常退出的问题(#8) @233Official
- 尝试修复进入溺梦之地失败没有重回主逻辑的问题 @233Official
- 修复任务异常超时的问题(#8) @233Official

### 🚀 性能优化

- 优化 wait seconds log @233Official

### 📚 文档

- 开发者文档与环境初始化脚本编写 @233Official
- 更新 S2 自动刷茧说明文档 @233Official
- 目前只开放了 G1 因子掉落, 其他等级的茧的自动挂机暂时没必要写了(#5) @233Official

### 🧹 日常维护

- 🎨 文档目录结构调整 @233Official
- Fix link formatting for S2 automatic brushing guide @233Official
- Revise README for clarity on features and stability @233Official

### 📌 发布

- v0.3.0 @233Official

### 🔧 配置文件

- update key @233Official
- 补充rapidfuzz依赖 @azmiao
- 通用TP传送点节点 @azmiao
- 修改agent vsc lauch 任务名称 @233Official
- 给冲刺回能留点时间 @233Official

## 0.2.0 (2025-11-04)

### ✨ 新功能

- Lv10浮游之茧潦草实现 @233Official
- 自定义 Action 新增条件选择动作与sleep动作 @233Official
- 自定义action传入参数解析模块 @233Official
- add loguru @233Official

### 🐛 Bug修复

- 解决初次运行项目时由于动态安装依赖导致的模块引入失败的问题 @233Official
- 尝试修复 VSCode 异常卡顿的问题, 目前我认为是 releases 目录中的成千上万个文件导致的 @233Official
- 协会狩猎复活逻辑捉虫 @233Official
- 修复自动战斗异常与协会狩猎复活异常的问题 @233Official
- 修复协会狩猎复活异常的问题(#3) @233Official

### 🎨 代码重构

- json format @233Official

### 📚 文档

- 更细自动刷茧文档(#5) @233Official
- S2 自动刷茧主体流程设计(#5) @233Official
- 更新新手上路文档与README @233Official
- update readme @233Official
- 更新文档与LICENSE @233Official
- UPDATE CHANGELOG @233Official
- 自动协会狩猎流程梳理 @233Official
- add docs @233Official

### 🧹 日常维护

- 🚧 新建文件夹: 自动钓鱼, 版本号来到 0.2.0 @233Official
- 🚧 自动开拓局任务 @233Official
- 📝 添加测试输出 @233Official
- ignore MaaDebuger Directory @233Official
- 🎨 抽离自动战斗模块 @233Official
- 🎨 code format @233Official

### 🔧 配置文件

- actions添加对prerelease的识别 @233Official
- 添加一些 VSCode 工作区扩展建议 @233Official
- 调整格式化配置 @233Official
- 启用 Github Actions @233Official
- 修改 markdown lint 配置 @233Official
- 归位 Github Actions @233Official
- 注释暂时未完成的全局 task @233Official
- 更新全局提示词 @233Official

## 0.1.0 (2025-10-17)

### ✨ 新功能

- 自动协会狩猎 @233Official
- 为离线打包添加embeddable python 支持 @233Official
- 进入游戏, 从省电模式唤醒, 打开与关闭一键连招 @233Official
- 新增 Python 脚本支持多平台本地编译产物 @233Official

### 🐛 Bug修复

- 修复活动自动弹出通知勾选会被识别为组队邀请, 自动点击 √ 并创建队伍的问题(#2) @233Official
- 修复省电模式全屏随机点击导致的异常 @233Official

### 🚀 性能优化

- 优化本地编译代码， 使其更合理 @Ayusummer

### 📚 文档

- add TODOs @233Official
- aDD TODO @233Official
- 截图工具手动使用命令 @233Official
- 优化描述, 补充说明 @233Official

### 🧹 日常维护

- ⚡️ improve AI Coding Rule @233Official
- 🎨 Code Format @233Official
- 🔥Delete Solved bug @233Official
- 🚧 每周商店清理 @233Official
- ignore MaaFWDocs @233Official
- 🔥 移除旧版本地打包脚本 @233Official
- ✨ 打包 embed python @233Official
- 🎨 目录结构调整 @Ayusummer
- ignore embeddable python dir @Ayusummer
- 🎨 auto format @Ayusummer
- ignore poetry config files @233Official
- 📝初版DPS分析 @233Official
- 🚧 更新部分肉鸽配置 @233Official
- 🔧 补充配置项 @233Official
- 🔥 移除对 Android 的支持, 添加本地构建命令示例 @233Official
- ignore config & ds store @233Official
- 🎨 转换为本地发版 @233Official

### 🧪 测试

- 添加基础测试用例-目前存在问题 macos 上无法正常调试 @233Official

### 🔧 配置文件

- 修改 json prettier 配置并重新格式化代码 @233Official
- interface.json 添加 macOS 配置 @233Official
- Python 虚拟环境配置 @233Official
- add Android KeyEvent Json @233Official
- add VSCode Github Copilot Coding Rules @233Official
- 补充快捷调试配置 @233Official
- 修改下项目名称 @Ayusummer
- 新增全局 interface 默认字段 @Ayusummer
- 添加VSC工作区扩展建议 - Prettier 用于格式化代码 @Ayusummer
- 调整 OCR 模型配置脚本以适应项目新结构 @Ayusummer
- vscode setting - 添加推荐扩展与 spell words @Ayusummer
- 不再使用github action， 暂且归档 @Ayusummer
- poetry 改 uv 管理项目依赖 @233Official

### 其他变更

- 离线安装依赖 @Ayusummer
- 下载 @Ayusummer

## 0.0.3 (2025-09-25)

### 📚 文档

- 添加 CHANGELOG @233Official

### 🧹 日常维护

- 🐛 尝试 Actions 编译报错问题 @233Official
- 🐛 尝试修复编译报错问题 @233Official
- 🎨 目录结构调整 @233Official

## 0.0.2 (2025-09-13)

### 🔧 配置文件

- 修改包体名称 @233

## 0.0.1 (2025-09-08)

### 🧹 日常维护

- 📝 更新开发随笔 @233
- Initial commit @233Official
