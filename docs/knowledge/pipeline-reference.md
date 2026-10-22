---
sidebar_label: Pipeline 参考
---

# Pipeline 参考手册

本文面向本项目开发者，列出常用 Pipeline 配置和项目内可复用节点，不替代完整协议。项目依赖 MaaFramework 5.12.3；字段与执行语义以[对应版本的任务流水线协议](https://github.com/MaaXYZ/MaaFramework/blob/v5.12.3/docs/zh_cn/3.1-任务流水线协议.md)及实际安装的 API 为准。仓库 `MaaFWDocs/` 保留了较早版本的文档，其中旧字段不能直接作为当前版本的配置依据。

---

## Pipeline 节点完整字段

以下列出本页涉及的常用字段；示例值不等于框架默认值，完整字段和默认值请查阅对应版本协议。

```json
{
    "节点名称": {
        "recognition": {
            "type": "DirectHit",
            "param": {}
        },
        "action": {
            "type": "DoNothing",
            "param": {}
        },
        "next": ["后继节点"],
        "on_error": ["错误处理节点"],
        "attach": { "key": "value" },
        "pre_delay": 0,
        "post_delay": 0,
        "rate_limit": 1000,
        "timeout": 20000,
        "enabled": true,
        "inverse": false,
        "focus": {}
    }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `recognition` | string\|object | 否 | 识别配置，不填默认 DirectHit |
| `action` | string\|object | 否 | 动作配置，不填默认 DoNothing |
| `next` | string\|array | 否 | 按顺序识别候选节点，只执行首个命中节点；支持 `[JumpBack]` 前缀 |
| `on_error` | string\|array | 否 | 当前节点动作失败，或其后继识别超时时，转入的候选节点列表 |
| `attach` | object | 否 | 附加数据，供 CustomAction 通过 `context.get_node_data()` 读取 |
| `pre_delay` | int | 否 | 识别命中后、动作执行前的延迟（毫秒），默认 200 |
| `post_delay` | int | 否 | 动作执行后、开始识别后继节点前的延迟（毫秒），默认 200 |
| `rate_limit` | int | 否 | 识别频率限制（毫秒），防止过快轮询 |
| `timeout` | int | 否 | 等待后继候选节点命中的识别超时时间（毫秒），默认 20000；不是整个任务的总时限 |
| `enabled` | bool | 否 | 是否启用，默认 true，可通过 pipeline_override 控制 |
| `inverse` | bool | 否 | 识别结果取反（识别不到才算命中），默认 false |
| `focus` | object | 否 | 关注节点的通知配置，供节点回调使用；消息值可以是 string 或 object，不是识别失败时自动显示的提示文本 |

---

## 识别类型详解

### DirectHit — 直接命中

不做任何识别，直接命中。用于纯动作节点。

```json
"ESC": {
    "recognition": "DirectHit",
    "action": {
        "type": "ClickKey",
        "param": { "key": 111 }
    }
}
```

### TemplateMatch — 模板匹配

在屏幕上查找模板图片。

```json
"检测主页面": {
    "recognition": {
        "type": "TemplateMatch",
        "param": {
            "template": ["general/主页面任务图标.png"],
            "roi": [22, 218, 26, 23],
            "threshold": 0.7,
            "green_mask": true,
            "method": 5
        }
    }
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `template` | string\|array | 模板图片路径（相对于 image/ 目录），多个模板任一匹配 |
| `roi` | [x,y,w,h] | 识别区域，[0,0,0,0] 表示全屏 |
| `threshold` | float | 匹配阈值 0-1，默认 0.7，越高越严格 |
| `green_mask` | bool | 绿色掩码，过滤模板中的绿色背景 |
| `method` | int | 匹配算法，1=`TM_SQDIFF_NORMED`、3=`TM_CCORR_NORMED`、5=`TM_CCOEFF_NORMED`，默认 5；枚举见 [OpenCV 文档](https://docs.opencv.org/4.x/df/dfb/group__imgproc__object.html) |

### OCR — 文字识别

识别屏幕上的文字。

```json
"检测确认按钮": {
    "recognition": {
        "type": "OCR",
        "param": {
            "expected": ["确认"],
            "roi": [767, 517, 59, 27],
            "only_rec": false,
            "replace": ["己", "已"]
        }
    }
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `expected` | string\|array | 期望的文字，支持正则表达式 |
| `roi` | [x,y,w,h] | 识别区域 |
| `only_rec` | bool | 跳过文字检测，直接识别指定 ROI 中的文字；需精确设置 ROI，不会取消 `expected` 筛选 |
| `replace` | array | 文字替换对，用于纠正常见 OCR 错误 |

### ColorMatch — 颜色匹配

匹配指定区域的颜色。

```json
"检测鱼鱼咬钩": {
    "recognition": {
        "type": "ColorMatch",
        "param": {
            "lower": [12, 250, 207],
            "upper": [24, 255, 255],
            "roi": [620, 357, 34, 32],
            "count": 8,
            "method": 40,
            "connected": false
        }
    }
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `lower` | [H,S,V] | HSV 下限 |
| `upper` | [H,S,V] | HSV 上限 |
| `roi` | [x,y,w,h] | 识别区域 |
| `count` | int | 最少匹配像素数 |
| `method` | int | 匹配方法（4=RGB, 40=HSV, 6=GRAY 等） |
| `connected` | bool | 是否要求连通区域 |

### Custom — 自定义识别

使用 Python 实现的自定义识别。

```json
"复合识别": {
    "recognition": {
        "type": "Custom",
        "param": {
            "custom_recognition": "AllMatch",
            "custom_recognition_param": {
                "nodes": ["节点A", "节点B"]
            }
        }
    }
}
```

---

## 动作类型详解

### DoNothing — 不做操作

```json
"参数节点": {
    "action": "DoNothing",
    "attach": { "key": "value" }
}
```

### Click — 点击

```json
// 固定坐标点击 [x, y, w, h]（在区域内随机点击）
"点击按钮": {
    "action": {
        "type": "Click",
        "param": {
            "target": [640, 360, 10, 10]
        }
    }
}

// 点击识别到的位置
"点击识别目标": {
    "recognition": { ... },
    "action": {
        "type": "Click",
        "param": {
            "target": true
        }
    }
}

// 点击偏移位置（识别位置 + 偏移量）
"点击偏移位置": {
    "recognition": { ... },
    "action": {
        "type": "Click",
        "param": {
            "target": true,
            "target_offset": [10, 20, 0, 0]
        }
    }
}
```

### ClickKey — 按键

```json
"按ESC": {
    "action": {
        "type": "ClickKey",
        "param": {
            "key": 111
        }
    }
}
```

### LongPressKey — 长按按键

```json
"按住W键1秒": {
    "action": {
        "type": "LongPressKey",
        "param": {
            "key": 51,
            "duration": 1000
        }
    }
}
```

### InputText — 输入文本

```json
"输入文本": {
    "action": {
        "type": "InputText",
        "param": {
            "input_text": "要输入的内容"
        }
    }
}
```

### Custom — 自定义动作

```json
"执行我的功能": {
    "action": {
        "type": "Custom",
        "param": {
            "custom_action": "MyFeature",
            "custom_action_param": {
                "key1": "value1",
                "key2": 123
            }
        }
    }
}
```

### Swipe — 滑动

```json
"滑动屏幕": {
    "action": {
        "type": "Swipe",
        "param": {
            "begin": [640, 500],
            "end": [640, 200],
            "duration": 500
        }
    }
}
```

---

## next 跳转规则

`next` 列出的是待识别的候选节点，不是“当前节点成功走第一个、失败走第二个”。当前节点动作完成后，框架按列表顺序检查候选节点各自的 `recognition`，只执行首个命中节点的动作，再处理该节点的 `next`。

- 某个候选节点本轮未命中，只会继续检查下一个候选；这不是动作失败，也不会立即触发 `on_error`。
- 所有候选都未命中时，按 `rate_limit` 继续轮询，直到命中或达到当前节点的 `timeout`。
- `DirectHit` 总会命中。把它放在候选列表前面会挡住后续候选；作为兜底时应放在最后。

**顺序执行：A → B → C。** 以下节点省略识别配置，默认 `DirectHit`。

```json
{
    "A": { "next": "B" },
    "B": { "next": "C" },
    "C": {}
}
```

**按候选识别结果分支。** 先识别 B 的“确认”；未命中才识别 C 的“取消”。两者都未命中则继续等待，不取决于 A 的识别结果。

```json
{
    "A": { "next": ["B", "C"] },
    "B": {
        "recognition": {
            "type": "OCR",
            "param": { "expected": ["确认"] }
        }
    },
    "C": {
        "recognition": {
            "type": "OCR",
            "param": { "expected": ["取消"] }
        }
    }
}
```

**错误分支：`on_error`。** 当前节点动作执行失败，或等待其 `next` 候选命中超时，才进入该节点的 `on_error` 列表。错误分支也按候选识别结果选择节点，不会依次执行列表中的所有节点。

```json
{
    "等待按钮": {
        "next": ["确认按钮"],
        "timeout": 20000,
        "on_error": ["识别超时处理"]
    },
    "确认按钮": {
        "recognition": {
            "type": "OCR",
            "param": { "expected": ["确认"] }
        },
        "action": "Click",
        "on_error": ["动作失败处理"]
    },
    "识别超时处理": {},
    "动作失败处理": {}
}
```

示例中的两个处理节点仅用于展示路由，默认 `DirectHit` / `DoNothing`，没有恢复操作。实际流程应接入所需的恢复动作或结束分支。“确认按钮”未命中时，等待的是“等待按钮”的 `next`，超时进入“等待按钮”的 `on_error`；命中后若点击动作失败，则使用“确认按钮”自己的 `on_error`，不会回退去尝试原列表的第二个候选。没有可用的错误处理分支时，任务失败结束。

**JumpBack：处理分支后重新识别原候选列表。**

```json
{
    "A": { "next": ["C", "[JumpBack]B"] },
    "B": {
        "recognition": {
            "type": "OCR",
            "param": { "expected": ["关闭"] }
        },
        "action": "Click"
    },
    "C": {
        "recognition": {
            "type": "OCR",
            "param": { "expected": ["确认"] }
        }
    }
}
```

当 C 未命中而 B 命中时，执行 B 及其后继节点链；节点链全部结束且当前不在错误处理路径时，从 A 的 `next` 列表起始位置重新识别，先尝试 C，再尝试 B，不重新执行 A 的识别和动作。若当前处于 `on_error` 错误处理路径，则不执行回跳，不能假设分支失败后仍会返回。`[JumpBack]` 不表示“识别失败时执行”，也不是 `on_error` 的替代品；它适合关闭弹窗后继续等待原目标等场景。

**循环：A → B → A。**

```json
{
    "A": { "next": "B", "timeout": 20000 },
    "B": { "next": "A" }
}
```

这个例子没有退出分支，A、B 都默认直接命中，因此会持续循环；`timeout` 不会累计整条流水线的运行时间并自动终止循环。需要结束条件时，应在循环候选列表中加入可识别的结束节点，并让其 `next` 为空；同时避免把始终命中的循环节点放在结束节点之前。也可以由调用方主动停止任务。顶层正常流程走到空 `next` 时结束；JumpBack 节点链走完后，仅在不处于错误处理路径时返回原候选列表。识别超时会转入 `on_error`，错误处理本身若又返回循环，也不能保证任务终止。

---

## interface.json 结构

`task[].entry` 指向该任务开始执行的 Pipeline 节点名，不是文件名；该节点需要包含在任务所加载的资源中。

```json
{
    "interface_version": 2,
    "name": "项目名",
    "version": "v0.12.0",
    "title": "显示标题",
    "controller": [
        { "name": "模拟器", "type": "Adb" }
    ],
    "resource": [
        { "name": "国服", "path": ["./resource/base"] }
    ],
    "agent": {
        "child_exec": "{PROJECT_DIR}/../.venv/Scripts/python.exe",
        "child_args": ["{PROJECT_DIR}/../agent/main.py"]
    },
    "task": [
        {
            "name": "任务显示名",
            "entry": "pipeline入口节点名",
            "description": "任务描述",
            "option": ["选项名1", "选项名2"]
        }
    ],
    "option": {
        "选项名1": {
            "type": "select",
            "default_case": "默认选中项",
            "description": "选项描述",
            "cases": [
                {
                    "name": "选项A",
                    "option": ["级联选项名"],
                    "pipeline_override": {
                        "节点名": {
                            "attach": { "key": "value" },
                            "enabled": true
                        }
                    }
                }
            ]
        },
        "选项名2": {
            "type": "input",
            "inputs": [
                {
                    "name": "输入框名",
                    "description": "输入说明",
                    "pipeline_type": "int",
                    "default": "0"
                }
            ],
            "pipeline_override": {
                "节点名": {
                    "action": {
                        "param": {
                            "custom_action_param": {
                                "key": "{输入框名}"
                            }
                        }
                    }
                }
            }
        }
    }
}
```

---

## 常用 pipeline_override 模式

### 覆盖 attach 参数

```json
"pipeline_override": {
    "获取参数-XXX": {
        "attach": { "key": "新值" }
    }
}
```

### 覆盖 custom_action_param

```json
"pipeline_override": {
    "入口节点": {
        "action": {
            "param": {
                "custom_action_param": {
                    "key": "{用户输入占位符}"
                }
            }
        }
    }
}
```

### 启用/禁用节点

```json
"pipeline_override": {
    "专注采集": { "enabled": true },
    "普通采集": { "enabled": false }
}
```

### 覆盖识别参数

```json
"pipeline_override": {
    "通用文字识别": {
        "expected": "新文字",
        "roi": [x, y, w, h]
    }
}
```

---

## 项目中的通用节点

以下节点在多个功能中复用，可以直接在 pipeline 或 Python 代码中引用：

| 节点名 | 类型 | 说明 |
|--------|------|------|
| `通用文字识别` | OCR | 通用 OCR，配合 pipeline_override 使用 |
| `图片识别是否在主页面` | TemplateMatch | 检测是否在游戏主页面 |
| `回到主页面` | Custom | 调用 return_main_page 返回主页 |
| `关闭所有弹窗广告` | Custom | 调用 CloseAd 关闭广告 |
| `ESC` | ClickKey | 按 ESC 键（key=111） |
| `按住W键1秒` | LongPressKey | 按住 W 键 1 秒 |
| `E-冲刺` | ClickKey | 按 E 键（key=33） |
| `循环F` | ClickKey | 循环按 F 键 |
| `启动指定APP` | Custom | 启动星痕共鸣 APP |
| `关闭指定APP` | Custom | 关闭星痕共鸣 APP |
| `重启指定APP` | Custom | 重启星痕共鸣 APP |
| `重启并登录星痕共鸣` | Custom | 重启并登录游戏 |
| `切换分线` | Custom | 切换世界分线 |
| `聊天频道发言` | Custom | 发送聊天消息 |
| `周期性聊天频道发言` | Custom | 循环发送聊天消息 |

---

## 常用 CustomAction 列表

| 注册名 | 文件 | 说明 |
|--------|------|------|
| `AutoFishing` | custom/fishing_action.py | 自动钓鱼 |
| `SendMessage` | custom/general/chat_message.py | 发送聊天消息 |
| `SendMessageLoop` | custom/general/chat_message.py | 循环发送聊天消息 |
| `SwitchLine` | custom/general/world_line_switcher.py | 切换分线 |
| `CloseAd` | custom/general/ad_close.py | 关闭广告弹窗 |
| `return_main_page` | custom/general/general.py | 返回主页面 |
| `run_pipeline_node` | custom/common_action.py | 运行指定 pipeline 节点 |
| `decision_router` | custom/common_action.py | 条件分支路由 |
| `wait_x_seconds` | custom/common_action.py | 等待指定秒数 |
| `run_custom_actions_series` | custom/common_action.py | 运行一系列动作 |
| `move_wsad` | custom/common_action.py | WSAD 移动 |
| `RestartAndLoginXHGM` | custom/app_manage_action.py | 重启并登录游戏 |
| `StartTargetApp` | custom/app_manage_action.py | 启动 APP |
| `StopTargetApp` | custom/app_manage_action.py | 关闭 APP |

---

## 常用 CustomRecognition 列表

| 注册名 | 文件 | 说明 |
|--------|------|------|
| `AllMatch` | custom/general/general.py | 所有指定节点都识别成功才算成功 |
| `AnyMatch` | custom/general/general.py | 任一指定节点识别成功即返回 |

---

## 分辨率与坐标系

- **基准分辨率**: 1280 x 720（MuMu 模拟器标准分辨率）
- **坐标原点**: 左上角 (0, 0)
- **ROI 格式**: `[x, y, width, height]`（左上角坐标 + 宽高）
- **全屏 ROI**: `[0, 0, 0, 0]` 或 `[0, 0, 1280, 720]`

---

## Android KeyEvent 常用键码

| 键名 | 键码 | 说明 |
|------|------|------|
| KEYCODE_ESCAPE | 111 | ESC |
| KEYCODE_W | 51 | W |
| KEYCODE_A | 29 | A |
| KEYCODE_S | 47 | S |
| KEYCODE_D | 32 | D |
| KEYCODE_E | 33 | E |
| KEYCODE_F | 34 | F |
| KEYCODE_I | 37 | I |
| KEYCODE_Z | 54 | Z |
| KEYCODE_ENTER | 66 | Enter |
| KEYCODE_BACK | 4 | 返回键 |

完整键码表见 `agent/constant/key_event/AndroidKeyEvent.json`。
