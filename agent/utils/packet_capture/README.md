# packet_capture - 星穹共鸣实时玩家数据抓包模块

`agent.utils.packet_capture` 通过被动网络抓包，从星穹共鸣（`com.tencent.wlfz`）的 TCP 流量中实时提取玩家数据。整个流程包括：嗅探 TCP 数据包、重组流、解析游戏自定义二进制协议、反序列化 protobuf 消息，最终提取玩家位置、身份和属性信息。

## 架构

```
Scapy AsyncSniffer  -->  TcpReassembler  -->  MessageParser  -->  PlayerTracker
   (BPF filter)         (stream reorder)     (frame/proto)      (player state)
```

| 模块 | 文件 | 职责 |
|------|------|------|
| **PacketCapture** | `sniffer.py` | 主调度器。管理 sniffer 生命周期、定期发现游戏端口、对外暴露公共 API |
| **TcpReassembler** | `tcp_reassembly.py` | TCP 流重组：序列号追踪、乱序缓存、游戏服务器自动识别（signature + envelope 启发式检测）、本地 IP 预过滤 |
| **MessageParser** | `message_parser.py` | 协议帧解析：length-prefixed 分帧、zstd 解压、FrameDown envelope 拆包、Notify 消息分发 |
| **PlayerTracker** | `player_tracker.py` | Protobuf 反序列化 WorldNtf 系列消息（SyncContainerData、SyncNearEntities、SyncNearDeltaInfo、SyncToMeDeltaInfo），维护线程安全的玩家状态，支持 callback 通知 |
| **process_ports** | `process_ports.py` | Windows 专用游戏进程发现，通过 `iphlpapi.dll` 枚举 PID、TCP/UDP 端口、本地 IP，构建 BPF filter |
| **proto/** | `proto/*.proto` / `*_pb2.py` | Protobuf 定义及生成代码（Position、Attr、Entity、WorldNtf、CharData） |

## 提取的数据

| 字段 | 来源 | 类型 |
|------|------|------|
| Position (x, y, z) | SyncToMeDeltaInfo, SyncContainerData | float |
| Direction (dir) | ATTR_DIR / 由移动推算 | float (radians) |
| char_id | SyncToMeDeltaInfo, SyncContainerData | int |
| Name | SyncContainerData, SyncNearEntities | str |
| Profession | SyncContainerData, SyncNearEntities | int -> name |
| Level | SyncContainerData, SyncNearEntities | int |
| Fight Point | SyncContainerData, SyncNearEntities | int |
| Rank Level | SyncNearEntities | int |
| HP / Max HP | SyncContainerData, SyncNearEntities | int |
| Season Strength | SyncNearEntities | int |

## 公共 API

```python
from agent.utils.packet_capture import PacketCapture, PlayerPosition, PlayerInfo

capture = PacketCapture()
capture.start()

# 轮询获取
pos: PlayerPosition | None = capture.get_position()
info: PlayerInfo = capture.get_player_info()

# 回调通知
capture.on_position_update(lambda p: print(p.x, p.y, p.z))
capture.on_player_info_update(lambda i: print(i.name, i.profession_name))

# 停止
capture.stop()
```

## 运行要求

- **操作系统**: Windows（依赖 `iphlpapi.dll` 发现游戏端口）
- **权限**: 管理员（原始数据包捕获需要）
- **Npcap**: 必须安装（Scapy 后端依赖）
- **Python**: >=3.11

## 命令行工具

### test_live - 实时监控

```bash
python -m agent.utils.packet_capture.test_live [--interval N] [--debug]
```

- `--interval N`: 状态输出间隔秒数（默认 5）
- `--debug`: 启用 DEBUG 级别日志，用于问题诊断

### diagnose - 诊断工具

```bash
python -m agent.utils.packet_capture.diagnose [--ports-only] [--capture FILE] [--replay FILE]
```

- `--ports-only`: 仅显示发现的游戏端口
- `--capture FILE`: 抓包并保存到 pickle 文件
- `--replay FILE`: 回放之前保存的 pickle 文件

## 文件结构

```
packet_capture/
├── __init__.py          # 公共 API 导出
├── sniffer.py           # PacketCapture 主调度器
├── tcp_reassembly.py    # TCP 流重组 + 服务器识别
├── message_parser.py    # 协议帧解析 + 消息分发
├── player_tracker.py    # Protobuf 反序列化 + 状态追踪
├── process_ports.py     # 游戏进程/端口发现 (Windows)
├── test_live.py         # 实时状态监控 (CLI)
├── diagnose.py          # 诊断/回放工具
├── proto/               # Protobuf 定义
│   ├── position.proto / position_pb2.py
│   ├── attr.proto / attr_pb2.py
│   ├── entity.proto / entity_pb2.py
│   ├── world_ntf.proto / world_ntf_pb2.py
│   └── char_data.proto / char_data_pb2.py
└── README.md
```
