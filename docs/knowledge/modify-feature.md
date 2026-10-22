---
sidebar_label: 修改功能
---

# 如何修改现有功能

本页说明如何定位现有功能的影响范围并修改相关资源和代码。新增任务与参数读取方式见[如何添加新功能](./add-feature.md)。

---

## 修改前必读

### 影响范围分析

修改任何代码前，先确定影响范围：

- Python 符号先使用编辑器或语言服务器的“查找引用”；跨 JSON/Python 的名称还要检查文本引用。
- 例如修改 `AutoFishing` 时，核对 `agent/` 中的注册与调用、`assets/` 中的 `custom_action`，以及 `assets/interface.json` 中的任务入口。

### 跨文件引用检查

按实际依赖检查联动文件，不要求每个功能都有 Python 和 Attach 层：

| 修改对象 | 需要核对的引用 |
| --- | --- |
| Pipeline 节点名 | `task.entry`、`next`、`on_error`、`pipeline_override`、Python 中的节点字符串 |
| 自定义动作或识别器注册名 | Pipeline 中的 `custom_action` / `custom_recognition` 与 Python 装饰器 |
| 用户选项 | `task.option`、选项定义、被覆盖节点与读取该参数的代码 |
| `attach` 参数 | 参数节点名、key、`agent/attach/` 读取函数及其调用处 |

纯 Pipeline 任务不需要为了满足目录结构而增加 CustomAction 或 Attach 文件。

---

## 常见修改场景

### 场景 1: 修改识别区域 (ROI)

**需求**：游戏更新后 UI 位置变化，需要调整识别区域。

**步骤**：

1. 用 VSCode Maa 插件截取新画面
2. 框选新的识别区域，获取新 ROI
3. 修改 pipeline JSON 中对应节点的 `roi` 字段

```json
// 修改前
"检测抛竿按钮": {
    "recognition": {
        "type": "TemplateMatch",
        "param": {
            "template": "自动钓鱼/抛竿按钮.png",
            "roi": [1084, 514, 150, 143]
        }
    }
}

// 修改后（只改 roi）
"检测抛竿按钮": {
    "recognition": {
        "type": "TemplateMatch",
        "param": {
            "template": "自动钓鱼/抛竿按钮.png",
            "roi": [1090, 520, 150, 143]
        }
    }
}
```

**注意**：

- ROI 格式为 `[x, y, width, height]`（左上角坐标 + 宽高）
- 修改后用 VSCode 插件验证识别是否命中
- 如果同一个识别节点被多处引用，只需改一处

### 场景 2: 更换模板图片

**需求**：游戏更新后 UI 图标变化，需要重新截取模板。

**步骤**：

1. 截取新的模板图片，替换 `assets/resource/base/image/` 下的对应文件
2. 保持文件名不变（避免修改 pipeline JSON）
3. 如果文件名变了，同步修改 pipeline JSON 中的 `template` 路径
4. 运行 `uv run python scripts/check_resource.py assets/resource/base` 检查资源加载，再用实际截图确认匹配结果。

### 场景 3: 修改点击位置

**需求**：按钮位置变化，需要调整点击坐标。

**步骤**：

1. 找到 pipeline JSON 中对应的 action 节点
2. 修改 `target` 字段的坐标

```json
"点击抛竿按钮": {
    "action": {
        "type": "Click",
        "param": {
            "target": [1160, 585, 1, 1]  // 修改这里的坐标
        }
    }
}
```

**提示**：如果该按钮有对应的识别节点，建议使用 `"target": true` 自动点击识别到的位置，而不是固定坐标。

### 场景 4: 修改 CustomAction 逻辑

**需求**：修改某个功能的业务逻辑（如钓鱼策略、聊天内容处理等）。

**步骤**：

1. 找到 `agent/custom/` 下对应的 Python 文件
2. 修改 `run()` 方法中的逻辑
3. 确保不改变 `@AgentServer.custom_action("名称")` 中的名称
4. 确保 `run()` 方法签名不变

示例：修改钓鱼张力阈值。

```python
# agent/custom/fishing_action.py
# 在 reel_loop 方法中

# 修改前
max_tension = 85  # 最大张力限制

# 修改后
max_tension = 90  # 提高张力阈值
```

**注意事项**：

- 不要修改 custom_action 注册名称，否则 pipeline JSON 也要同步改
- 不要修改 `run()` 方法的参数签名
- 保持返回值语义：`True` 成功，`False` 失败
- 修改后检查是否影响了其他调用该方法的地方

### 场景 5: 添加新的用户选项

**需求**：为现有功能添加新的可配置选项。

**步骤**：

以下示例采用共享 `attach` 参数；仅供单个动作使用的参数可直接通过 `custom_action_param` 传入，选择依据见[参数传递](./add-feature.md#参数传递)。

- **pipeline JSON**：添加参数节点（如果还没有）

```json
"获取参数-我的新参数": {
    "action": "DoNothing",
    "attach": {
        "my_new_param": "默认值"
    }
}
```

- **attach 辅助函数**：添加读取函数（使用装饰器）

```python
# agent/attach/my_attach.py
from maa.context import Context
from agent.attach import attach_param


@attach_param("获取参数-我的新参数", "my_new_param", "默认值")
def get_my_new_param(context: Context) -> str:
    """获取我的新参数"""
    ...
```

- **CustomAction**：在 `run()` 中读取并使用参数

```python
my_param = get_my_new_param(context)
```

- **interface.json**：在 option 中添加选项定义，在 task 的 option 列表中引用

```json
// option 中添加
"我的新选项": {
    "type": "select",
    "cases": [
        {
            "name": "选项A",
            "pipeline_override": {
                "获取参数-我的新参数": {
                    "attach": { "my_new_param": "A" }
                }
            }
        }
    ]
}

// task 中引用
{
    "name": "我的功能",
    "entry": "我的功能入口",
    "option": ["我的新选项"]
}
```

### 场景 6: 修改任务流程（节点链）

**需求**：调整任务执行步骤，如添加/删除/重排节点。

**步骤**：

1. 修改 pipeline JSON 中节点的 `next` 字段
2. 确保所有 `next` 引用的节点都存在
3. 为有意设计的循环设置实际退出条件，并验证用户停止响应；`timeout` 不是整个任务的总时长上限。
4. 运行 `uv run python scripts/check_resource.py assets/resource/base` 检查资源加载，再实际运行受影响的节点链。

示例：在流程中插入一个等待节点。

```json
// 修改前
"节点A": { "next": "节点B" }

// 修改后（插入等待）
"节点A": { "next": "等待2秒" },
"等待2秒": {
    "action": {
        "type": "Custom",
        "param": {
            "custom_action": "wait_x_seconds",
            "custom_action_param": { "wait_seconds": 2 }
        }
    },
    "next": "节点B"
}
```

### 场景 7: 修改 interface.json 中的任务定义

**需求**：修改任务名称、描述、选项等。

**注意**：

- `entry` 字段值必须与 pipeline JSON 中的节点 key 一致，修改 entry 时必须同步修改 pipeline
- `name` 字段是用户看到的显示名，可以自由修改
- `option` 引用的选项名必须在 `option` 对象中存在

---

## 修改后的验证流程

按[测试与验收](./test-feature.md)选择适用检查，区分三个层次：

1. 资源加载与格式检查：确认框架能加载资源；不能据此证明 Python 注册名称匹配。
2. 节点调试：用实际截图验证识别、ROI 和动作。
3. 任务验收：从入口运行受影响功能，验证选项、完成条件、停止和异常分支；共享节点的调用方也要覆盖。

没有模拟器或对应游戏场景时，明确记录尚未验证的范围。

---

## 安全修改原则

### DO（推荐做法）

- **最小修改**：只改需要改的部分，不做无关重构
- **保持命名**：不做无关重命名；确需改名时同步更新全部跨文件引用。
- **保持参数契约**：更改默认值或删除参数前，核对选项覆盖、读取函数和调用方。
- **按依赖修改**：只更新实际受影响的 Pipeline、Python 和界面声明，不强制凑齐固定层数。
- **分层验证**：资源加载检查之外，还要验证受影响的节点和任务。

### DON'T（避免做法）

- **不要**随意重命名 pipeline 节点名（会导致 interface.json 和其他引用断裂）
- **不要**随意重命名 custom_action 注册名（会导致 pipeline 引用断裂）
- **不要**修改 `run()` 方法签名
- **不要**删除仍在被引用的 pipeline 节点
- **不要**修改 attach 节点的 key 名而不同步修改对应的读取函数
- **不要**在未验证的情况下批量修改 ROI 坐标

---

## 版本更新检查清单

游戏版本更新后，按以下清单逐项检查：

- [ ] 所有模板图片是否仍然匹配（游戏 UI 可能变化）
- [ ] 所有 ROI 是否仍然正确
- [ ] OCR 识别的文字是否有变化
- [ ] 颜色匹配的 HSV 范围是否仍然有效
- [ ] 点击坐标是否仍然正确
- [ ] 新功能是否需要添加到 interface.json
- [ ] 地图数据（MapPoint.json / NavigatePoint.json）是否需要更新
- [ ] 鱼类数据（FishData.json）是否需要更新
- [ ] 频道数据（ChannelData.json）是否需要更新

---

## 插件开发

### 插件结构

```text
agent/plugins/
└── my_plugin/
    ├── plugin.json          # 插件元数据
    ├── lib/
    │   └── my_plugin.pyz    # 插件代码（zip 打包）
    └── deps/                # 可选：依赖的 wheel 文件
        └── some_package.whl
```

### plugin.json 格式

```json
{
    "name": "my_plugin",
    "display_name": "我的插件",
    "version": "1.0.0",
    "description": "插件描述",
    "author": "作者",
    "license": "AGPL-3.0",
    "pyz_file": "lib/my_plugin.pyz",
    "entry_point": "my_plugin_module",
    "dependencies": ["deps/some_package.whl"],
    "system_requirements": {
        "platform": "windows",
        "min_python_version": "3.11"
    },
    "exports": {
        "MyApi": "my_module.MyApi"
    }
}
```

### 在代码中使用插件

```python
from agent.plugin_registry import PluginRegistry

registry = PluginRegistry.get_instance()

# 检查插件是否可用
if registry.is_available("my_plugin"):
    # 获取插件模块
    module = registry.get_plugin("my_plugin")
    
    # 获取插件导出的 API
    api = registry.get_api("my_plugin", "MyApi")
    if api:
        api.do_something()
else:
    logger.info("插件 my_plugin 未安装，相关功能已禁用")
```

---

## 文件修改速查表

| 修改内容 | 需要改的文件 |
|---------|-------------|
| 识别区域 ROI | `assets/resource/base/pipeline/*.json` |
| 模板图片 | `assets/resource/base/image/` |
| 点击坐标 | `assets/resource/base/pipeline/*.json` |
| 业务逻辑 | `agent/custom/*.py` |
| 参数读取 | `agent/attach/*.py` |
| 新增用户选项 | `assets/interface.json` + 被覆盖的 Pipeline 节点；按读取方式更新 Python |
| 任务入口 | `assets/interface.json` + `assets/resource/base/pipeline/*.json` |
| 常量数据 | `agent/constant/` |
| 工具函数 | `agent/utils/*.py` |
| 新增功能 | 按需修改 interface.json、Pipeline、Python 扩展和参数读取；见[添加功能](./add-feature.md) |
