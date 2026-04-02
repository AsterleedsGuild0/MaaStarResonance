# Packet Capture 模块分析文档

## 模块整体逻辑分析

这是一个用于捕获游戏网络流量并提取玩家数据的系统，整体架构如下：

### 模块结构

```
packet_capture/
├── __init__.py          # 公共 API 入口
├── sniffer.py           # 主控制器 PacketCapture
├── process_ports.py     # 游戏进程端口发现
├── tcp_reassembly.py    # TCP 流重组
├── message_parser.py    # 消息帧解析 + zstd 解压
├── player_tracker.py    # 玩家数据提取 + 状态管理
├── diagnose.py          # 诊断工具
├── proto/               # Protobuf 定义
│   ├── world_ntf.proto  # 游戏世界通知消息
│   ├── position.proto   # 位置数据
│   ├── attr.proto       # 属性数据
│   └── entity.proto     # 实体数据
```

### 数据处理流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        PacketCapture                            │
│  (sniffer.py - 主控制器)                                         │
└─────────────────────────────────────────────────────────────────┘
        │
        │ 1. 启动后台嗅探线程 + 端口发现线程
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     process_ports.py                            │
│  发现游戏进程 → 获取 TCP/UDP 端口 → 构建 BPF 过滤器               │
│  (Windows API: CreateToolhelp32Snapshot, GetExtendedTcpTable)   │
└─────────────────────────────────────────────────────────────────┘
        │
        │ 2. Scapy AsyncSniffer 用 BPF filter 捕获数据包
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     tcp_reassembly.py                           │
│  TCP 流重组:                                                     │
│  - 按 4-tuple (src_ip, src_port, dst_ip, dst_port) 分流         │
│  - 序列号追踪 + 乱序包缓存                                        │
│  - 服务器检测 (签名/登录返回/消息帧头)                            │
│  - 处理 Npcap 重复包问题                                          │
└─────────────────────────────────────────────────────────────────┘
        │
        │ 3. 输出重组后的连续字节流
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     message_parser.py                           │
│  消息帧解析:                                                     │
│  - 4-byte 大端长度前缀帧格式                                      │
│  - 解析消息类型 (Notify/FrameDown)                               │
│  - Zstd 解压 (处理 skippable frames)                            │
│  - FrameDown 递归拆包                                            │
│  - 按 service_uuid 路由到处理器                                   │
└─────────────────────────────────────────────────────────────────┘
        │
        │ 4. Notify 消息路由到 WorldNtf 处理器
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     player_tracker.py                           │
│  玩家数据提取:                                                    │
│  - 解析 WorldNtf protobuf (SyncContainerData, SyncNearEntities  │
│    SyncNearDeltaInfo, SyncToMeDeltaInfo)                        │
│  - 提取位置 (x, y, z, dir)                                       │
│  - 提取属性 (name, profession, level, HP, fight_point 等)        │
│  - UUID 匹配识别当前玩家                                          │
│  - 线程安全状态管理 + 回调通知                                     │
└─────────────────────────────────────────────────────────────────┘
        │
        │ 5. 输出 PlayerPosition / PlayerInfo
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      用户代码                                     │
│  capture.get_position()      → PlayerPosition (x,y,z,dir)       │
│  capture.get_player_info()   → PlayerInfo (name,profession,HP)  │
│  capture.on_position_update(callback)                           │
│  capture.on_player_info_update(callback)                        │
└─────────────────────────────────────────────────────────────────┘
```

### 核心组件详解

**1. `process_ports.py` - 端口发现**
- 用 Windows API 查找游戏进程 (`star.exe`, `BPSR_STEAM.exe` 等)
- 获取进程占用的 TCP/UDP 端口
- 构建 BPF filter: `(ip or ip6) and ((tcp and (port X or port Y)) or ...)`
- 每 5 秒刷新端口并更新过滤器

**2. `tcp_reassembly.py` - TCP 重组**
- 处理乱序包：缓存未来序列号的包，等待缺口填补
- 处理重叠重传：Npcap 常见问题，同一数据被捕获两次
- Gap timeout：缺口超时 2 秒后强制跳转同步
- 服务器检测三种方式：
  - 登录返回签名 (`LOGIN_RETURN_PREFIX`)
  - 服务器特征字节 (`SERVER_SIGNATURE`)
  - 有效消息帧头检测 (Notify/FrameDown 类型)

**3. `message_parser.py` - 消息解析**
- 帧格式: `[4B size][2B type][payload]`
- 消息类型: CALL(1), NOTIFY(2), RETURN(3), FRAME_DOWN(6)
- Zstd 解压标志: type 高位 0x8000
- Notify 格式: `[8B service_uuid][4B stub_id][4B method_id][protobuf]`
- 只处理 NOTIFY 和 FRAME_DOWN (服务器→客户端)

**4. `player_tracker.py` - 玩家追踪**
- 处理 4 种 WorldNtf 方法:
  - `SyncContainerData (0x15)` - 登录时完整同步
  - `SyncNearEntities (0x06)` - 附近实体出现
  - `SyncNearDeltaInfo (0x2D)` - 批量增量更新
  - `SyncToMeDeltaInfo (0x2E)` - 针对当前玩家的增量
- 通过 `char_id` 匹配识别当前玩家
- 职业 ID 映射: 1=雷影剑士, 2=冰魔导师, 3=赤炎狂战士 等

### 使用示例

```python
from agent.utils.packet_capture import PacketCapture

capture = PacketCapture()
capture.start()

# 轮询方式
pos = capture.get_position()      # → PlayerPosition(x,y,z,dir)
info = capture.get_player_info()  # → PlayerInfo(name,profession,level,HP)

# 回调方式
capture.on_position_update(lambda p: print(f"位置: {p.x}, {p.y}"))
capture.on_player_info_update(lambda i: print(f"玩家: {i.name}"))

capture.stop()
```

### 参考来源

代码注释表明这是参考 C# 项目 `StarResonanceDps` 的 Python 重实现，包括:
- `TcpStreamProcessor.cs` → `tcp_reassembly.py`
- `MessageAnalyzerV2.cs` → `message_parser.py`
- `DeltaInfoProcessors.cs` 等 → `player_tracker.py`

---

## 详细代码解释

### 1. 入口与公共 API (`__init__.py`)

```python
# agent/utils/packet_capture/__init__.py

from agent.utils.packet_capture.player_tracker import PlayerInfo, PlayerPosition
from agent.utils.packet_capture.sniffer import PacketCapture

__all__ = ["PacketCapture", "PlayerInfo", "PlayerPosition"]
```

**作用**: 只导出三个类给外部使用：
- `PacketCapture` - 主控制器，负责启动/停止捕获
- `PlayerPosition` - 位置数据快照 (x, y, z, dir, timestamp)
- `PlayerInfo` - 玩家信息快照 (name, profession, level, HP 等)

---

### 2. 主控制器 (`sniffer.py`)

#### 2.1 初始化：构建处理管道

```python
# sniffer.py 第 79-88 行
def __init__(self) -> None:
    # 创建三个核心组件
    self._player_tracker = PlayerTracker()
    self._message_parser = MessageParser()
    self._tcp_reassembler = TcpReassembler(on_data=self._message_parser.feed)

    # 注册 WorldNtf 处理器
    self._message_parser.register_handler(
        WORLD_NTF_SERVICE_UUID, self._player_tracker.handle_world_ntf
    )
```

**管道连接**:
```
TCP重组 → MessageParser.feed() → WorldNtf处理器 → PlayerTracker.handle_world_ntf()
```

#### 2.2 启动捕获

```python
# sniffer.py 第 100-122 行
def start(self) -> None:
    if self._running.is_set():
        return  # 防止重复启动

    self._running.set()
    self._stop_event.clear()

    # 启动端口发现线程（后台循环）
    self._port_thread = threading.Thread(
        target=self._port_discovery_loop, name="port-discovery", daemon=True
    )
    self._port_thread.start()

    # 立即执行一次端口发现并启动嗅探器
    self._refresh_ports_and_restart_sniffer()
```

#### 2.3 端口发现循环

```python
# sniffer.py 第 263-277 行
def _port_discovery_loop(self) -> None:
    while self._running.is_set():
        try:
            self._refresh_ports_and_restart_sniffer()
        except Exception:
            logger.exception("Error in port discovery")

        # 每 5 秒刷新一次，或收到停止信号时退出
        if self._stop_event.wait(timeout=PORT_REFRESH_INTERVAL):  # 5.0秒
            break
```

#### 2.4 刷新端口并重启嗅探器

```python
# sniffer.py 第 279-300 行
def _refresh_ports_and_restart_sniffer(self) -> None:
    # 发现游戏进程的端口
    new_ports = discover_game_ports()
    # 构建 BPF 过滤器字符串
    new_filter = build_bpf_filter(new_ports)
    # 根据本地 IP 找到对应的网卡接口
    new_ifaces = self._resolve_interfaces(new_ports.local_ips)

    with self._lock:
        # 如果过滤器没变，不用重启
        if new_filter == self._current_filter:
            return
        self._current_filter = new_filter
        self._current_ports = new_ports

    # 更新 TCP 重组器的本地 IP（用于判断数据包方向）
    self._tcp_reassembler.set_local_ips(new_ports.local_ips)

    # 重启嗅探器
    self._stop_sniffer()
    self._start_sniffer(new_filter, new_ifaces)
```

#### 2.5 启动 Scapy AsyncSniffer

```python
# sniffer.py 第 322-346 行
def _start_sniffer(self, bpf_filter: str, ifaces: list[str] | None = None) -> None:
    try:
        conf.verb = 0  # 禁止 Scapy 输出日志

        kwargs: dict = {
            "filter": bpf_filter,        # BPF 过滤器
            "prn": self._packet_handler, # 每个包的处理回调
            "store": False,              # 不存储原始包
        }
        if ifaces:
            kwargs["iface"] = ifaces if len(ifaces) > 1 else ifaces[0]

        self._sniffer = AsyncSniffer(**kwargs)
        self._sniffer.start()
```

#### 2.6 数据包处理回调

```python
# sniffer.py 第 214-256 行
def _packet_handler(self, packet: Packet) -> None:
    try:
        # 只处理 IP + TCP 包
        if not packet.haslayer(IP) or not packet.haslayer(TCP):
            return

        ip_layer = packet[IP]
        tcp_layer = packet[TCP]

        payload = bytes(tcp_layer.payload)
        if len(payload) == 0:
            return

        # 跳过 Npcap 的伪包：16字节以下的全零包
        # 这是 Windows/Npcap 的已知问题，会重复捕获数据
        if len(payload) <= 16 and not any(payload):
            return

        # 送入 TCP 重组器
        self._tcp_reassembler.process_packet(
            src_ip=ip_layer.src,
            src_port=tcp_layer.sport,
            dst_ip=ip_layer.dst,
            dst_port=tcp_layer.dport,
            seq=tcp_layer.seq,
            payload=payload,
        )

        # 每 30 秒清理空闲的 TCP 流
        now = time.monotonic()
        if now - self._last_cleanup > CLEANUP_INTERVAL:
            self._last_cleanup = now
            self._tcp_reassembler.cleanup_idle_streams()
```

---

### 3. 端口发现 (`process_ports.py`)

#### 3.1 游戏进程名列表

```python
# process_ports.py 第 17-19 行
GAME_PROCESS_NAMES: list[str] = ["star", "BPSR_STEAM", "BPSR_EPIC", "BPSR"]
_GAME_PROCESS_NAMES_UPPER: set[str] = {n.upper() for n in GAME_PROCESS_NAMES}
```

#### 3.2 查找游戏进程 PID

```python
# process_ports.py 第 67-116 行
def _find_game_pids() -> set[int]:
    # Windows API 结构体定义
    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", ctypes.wintypes.DWORD),
            ("th32ProcessID", ctypes.wintypes.DWORD),
            ("szExeFile", ctypes.c_wchar * 260),  # 进程名
            # ... 其他字段
        ]

    kernel32 = ctypes.windll.kernel32
    # 创建进程快照
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)

    pids: set[int] = set()
    pe = PROCESSENTRY32W()
    pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)

    try:
        if kernel32.Process32FirstW(snapshot, ctypes.byref(pe)):
            while True:
                exe_name = pe.szExeFile
                # 去掉 .exe 后缀比较
                name_no_ext = exe_name.rsplit(".", 1)[0] if "." in exe_name else exe_name
                if name_no_ext.upper() in _GAME_PROCESS_NAMES_UPPER:
                    pids.add(pe.th32ProcessID)  # 记录 PID
                if not kernel32.Process32NextW(snapshot, ctypes.byref(pe)):
                    break
    finally:
        kernel32.CloseHandle(snapshot)

    return pids
```

#### 3.3 获取 TCP 端口

```python
# process_ports.py 第 119-176 行
def _get_tcp_ports_for_pids(pids: set[int]) -> tuple[set[int], set[str]]:
    iphlpapi = ctypes.windll.iphlpapi

    # 第一次调用获取需要的缓冲区大小
    buf_size = ctypes.wintypes.DWORD(0)
    iphlpapi.GetExtendedTcpTable(
        None, ctypes.byref(buf_size), False, AF_INET, TCP_TABLE_OWNER_PID_ALL, 0
    )

    # 分配缓冲区，再次调用获取实际数据
    buf = (ctypes.c_byte * buf_size.value)()
    ret = iphlpapi.GetExtendedTcpTable(
        buf, ctypes.byref(buf_size), False, AF_INET, TCP_TABLE_OWNER_PID_ALL, 0
    )

    # 解析表格：第一个 DWORD 是行数
    num_entries = struct.unpack_from("<I", buf, 0)[0]
    offset = 4

    for _ in range(num_entries):
        row = MIB_TCPROW_OWNER_PID.from_buffer_copy(buf, offset)
        if row.dwOwningPid in pids:
            # 端口是网络字节序（大端），需要转换
            port = ((row.dwLocalPort & 0xFF) << 8) | ((row.dwLocalPort >> 8) & 0xFF)
            ports.add(port)

            # 收集本地 IP（排除 127.x 和 0.0.0.0）
            local_ip = socket.inet_ntoa(struct.pack("<I", row.dwLocalAddr))
            if local_ip != "0.0.0.0" and not local_ip.startswith("127."):
                local_ips.add(local_ip)
        offset += row_size

    return ports, local_ips
```

#### 3.4 构建 BPF 过滤器

```python
# process_ports.py 第 257-284 行
def build_bpf_filter(game_ports: GamePorts) -> str:
    if not game_ports.has_ports:
        # 没有端口时，匹配空端口（实际不捕获任何包）
        return "(ip or ip6) and (port 0)"

    parts: list[str] = []

    if game_ports.tcp_ports:
        # tcp and (port 12345 or port 12346)
        tcp_port_expr = " or ".join(f"port {p}" for p in sorted(game_ports.tcp_ports))
        parts.append(f"(tcp and ({tcp_port_expr}))")

    if game_ports.udp_ports:
        udp_port_expr = " or ".join(f"port {p}" for p in sorted(game_ports.udp_ports))
        parts.append(f"(udp and ({udp_port_expr}))")

    filter_body = " or ".join(parts)
    # 最终: "(ip or ip6) and ((tcp and (port X or port Y)) or (udp and (port A)))"
    return f"(ip or ip6) and ({filter_body})"
```

---

### 4. TCP 流重组 (`tcp_reassembly.py`)

#### 4.1 流标识 (4-tuple)

```python
# tcp_reassembly.py 第 43-50 行
@dataclass(frozen=True)
class StreamKey:
    """4-tuple 标识一个 TCP 流方向"""
    src_ip: str
    src_port: int
    dst_ip: str
    dst_port: int
```

每个 TCP 连接有两个方向：
- 服务器→客户端: `(server_ip, server_port, client_ip, client_port)`
- 客户端→服务器: `(client_ip, client_port, server_ip, server_port)`

我们只关心服务器→客户端方向。

#### 4.2 单个 TCP 流的状态

```python
# tcp_reassembly.py 第 61-73 行
class TcpStream:
    def __init__(self) -> None:
        self.next_seq: int | None = None       # 下一个期望的序列号
        self.cache: OrderedDict[int, CacheEntry] = OrderedDict()  # 乱序包缓存
        self.last_activity: float = time.monotonic()  # 最后活动时间
        self.gap_start_time: float | None = None      # 缺口开始时间
```

#### 4.3 序列号比较（处理 32 位回绕）

```python
# tcp_reassembly.py 第 74-89 行
def _seq_compare(self, a: int, b: int) -> int:
    """比较两个序列号，考虑 32 位回绕"""
    diff = (a - b) & 0xFFFFFFFF
    if diff >= 0x80000000:
        return diff - 0x100000000  # 负数
    return diff
```

TCP 序列号是 32 位无符号，会回绕。例如：
- `seq=0xFFFFFFFF` 和 `seq=0x00000001` 实际相差 2，不是巨大差距。

#### 4.4 处理 TCP 段的核心逻辑

```python
# tcp_reassembly.py 第 105-190 行
def process_segment(self, seq: int, payload: bytes) -> bytes:
    now = time.monotonic()
    self.last_activity = now
    payload_len = len(payload)

    if payload_len == 0:
        return b""

    # 第一个包初始化流
    if self.next_seq is None:
        self.next_seq = (seq + payload_len) & 0xFFFFFFFF
        return payload  # 直接返回

    cmp = self._seq_compare(seq, self.next_seq)

    if cmp == 0:
        # ===== 情况 1: 按序到达 =====
        self.gap_start_time = None
        result = bytearray(payload)
        self.next_seq = (self.next_seq + payload_len) & 0xFFFFFFFF

        # 尝试消费缓存的后续包
        while self.cache:
            if self.next_seq in self.cache:
                entry = self.cache.pop(self.next_seq)
                result.extend(entry.data)  # 拼接
                self.next_seq = (self.next_seq + len(entry.data)) & 0xFFFFFFFF
            else:
                break

        return bytes(result)

    elif cmp > 0:
        # ===== 情况 2: 未来包（乱序） =====
        if seq not in self.cache:
            self.cache[seq] = CacheEntry(data=payload, timestamp=now)

        # 记录缺口开始时间
        if self.gap_start_time is None:
            self.gap_start_time = now
        elif now - self.gap_start_time > GAP_TIMEOUT_SECONDS:  # 2秒
            # 缺口超时，强制跳转到这个包
            return self._force_resync_to(seq)

        return b""  # 暂时不返回数据

    else:
        # ===== 情况 3: 过去包（可能是重叠重传） =====
        seg_end = (seq + payload_len) & 0xFFFFFFFF
        overlap = self._seq_compare(seg_end, self.next_seq)

        if overlap > 0:
            # 这个包有新数据超过 next_seq
            # 截掉重复部分，处理新部分
            trim = self._seq_compare(self.next_seq, seq)
            new_data = payload[trim:]

            self.gap_start_time = None
            result = bytearray(new_data)
            self.next_seq = (self.next_seq + len(new_data)) & 0xFFFFFFFF

            # 消费缓存
            while self.cache:
                if self.next_seq in self.cache:
                    entry = self.cache.pop(self.next_seq)
                    result.extend(entry.data)
                    self.next_seq = (self.next_seq + len(entry.data)) & 0xFFFFFFFF
                else:
                    break

            return bytes(result)

        return b""  # 纯重复，忽略
```

#### 4.5 服务器检测

```python
# tcp_reassembly.py 第 333-382 行
def _detect_server(self, src_ip: str, src_port: int, payload: bytes, ...) -> bool:
    # 方法 B: 登录返回签名（最可靠）
    if len(payload) >= 24 and payload[3] == 0x62:
        if payload[:10] == LOGIN_RETURN_PREFIX and payload[14:20] == LOGIN_RETURN_MID:
            self._set_server(src_ip, src_port, seq, payload_len)
            return True

    # 方法 A: 在嵌套帧中扫描服务器签名
    if len(payload) > 10 and payload[4] == 0x00:
        inner = payload[10:]
        if self._scan_for_server_signature(inner):
            self._set_server(src_ip, src_port, seq, payload_len)
            return True

    # 方法 C: 消息帧头检测
    if self._detect_by_message_envelope(payload):
        self._set_server(src_ip, src_port, seq, payload_len)
        return True

    return False
```

#### 4.6 消息帧头检测

```python
# tcp_reassembly.py 第 384-417 行
@staticmethod
def _detect_by_message_envelope(payload: bytes) -> bool:
    """检测是否是有效的服务器消息"""
    if len(payload) < 6:
        return False

    # 前 4 字节是帧长度（大端）
    frame_size = int.from_bytes(payload[:4], "big")
    if frame_size < 6 or frame_size > 0x0FFFFF:
        return False

    # 第 5-6 字节是消息类型
    type_raw = int.from_bytes(payload[4:6], "big")
    msg_type = type_raw & 0x7FFF  # 低 15 位

    # 只接受服务器→客户端的消息类型
    return msg_type in (
        2,  # Notify
        3,  # Return
        6,  # FrameDown
    )
```

#### 4.7 处理单个包

```python
# tcp_reassembly.py 第 273-331 行
def process_packet(self, src_ip, src_port, dst_ip, dst_port, seq, payload) -> None:
    if len(payload) == 0:
        return

    # 判断是否是服务器→客户端包
    is_from_server = False

    if self._local_ips:
        # 如果知道本地 IP，用它判断方向
        # 服务器→客户端: dst_ip 是本地 IP，src_ip 不是
        if dst_ip in self._local_ips and src_ip not in self._local_ips:
            is_from_server = True
    else:
        # 否则用签名检测
        ep = ServerEndpoint(ip=src_ip, port=src_port)
        if ep in self._server_endpoints:
            is_from_server = True
        else:
            if self._detect_server(src_ip, src_port, payload, seq, len(payload)):
                is_from_server = True

    if not is_from_server:
        return

    # 获取或创建流
    key = StreamKey(src_ip, src_port, dst_ip, dst_port)
    stream = self._streams.get(key)
    if stream is None:
        stream = TcpStream()
        self._streams[key] = stream

    # 处理段
    reassembled = stream.process_segment(seq, payload)
    if reassembled:
        self._on_data(reassembled)  # 调用 MessageParser.feed()
```

---

### 5. 消息解析 (`message_parser.py`)

#### 5.1 帧格式

```
[4B 大端长度][2B 类型][payload]
                    ↑
                    类型字段：高 16 位是压缩标志 (0x8000)
                             低 15 位是实际类型
```

#### 5.2 消息类型

```python
# message_parser.py 第 34-46 行
class MessageType(enum.IntEnum):
    NONE = 0
    CALL = 1      # 客户端→服务器（调用）
    NOTIFY = 2    # 服务器→客户端（通知）
    RETURN = 3    # 服务器→客户端（返回）
    ECHO = 4
    FRAME_UP = 5    # 客户端→服务器（帧上传）
    FRAME_DOWN = 6  # 服务器→客户端（帧下发）
```

我们只处理 `NOTIFY` 和 `FRAME_DOWN`（都是服务器→客户端）。

#### 5.3 填充数据并解析帧

```python
# message_parser.py 第 79-88 行
def feed(self, data: bytes) -> None:
    self._buffer.extend(data)  # 添加到缓冲区
    self._parse_frames()       # 尝试提取完整帧
```

#### 5.4 帧提取循环

```python
# message_parser.py 第 90-128 行
def _parse_frames(self) -> None:
    max_skip = 0
    while len(self._buffer) >= 4:
        # 读取帧长度
        packet_size = struct.unpack_from(">I", self._buffer, 0)[0]

        # 合理性检查
        if packet_size <= 4 or packet_size > 0x0FFFFF:
            # 无效帧，跳过一个字节尝试重新同步
            self._buffer = self._buffer[1:]
            max_skip += 1
            if max_skip >= 4096:
                self._buffer.clear()  # 防止无限扫描
                return
            continue

        if len(self._buffer) < packet_size:
            break  # 不完整，等待更多数据

        # 提取完整帧
        frame = bytes(self._buffer[:packet_size])
        self._buffer = self._buffer[packet_size:]
        self._process_message(frame)
```

#### 5.5 处理单条消息

```python
# message_parser.py 第 130-152 行
def _process_message(self, frame: bytes) -> None:
    if len(frame) < 6:
        return

    # 解析类型字段
    packet_type_raw = struct.unpack_from(">H", frame, 4)[0]
    is_compressed = bool(packet_type_raw & 0x8000)  # 高位是压缩标志
    msg_type_value = packet_type_raw & 0x7FFF       # 低 15 位是类型

    payload = frame[6:]

    # 只处理 Notify 和 FrameDown
    if msg_type_value == MessageType.NOTIFY:
        self._handle_notify(payload, is_compressed)
    elif msg_type_value == MessageType.FRAME_DOWN:
        self._handle_frame_down(payload, is_compressed)
```

#### 5.6 处理 Notify 消息

```python
# message_parser.py 第 154-191 行
def _handle_notify(self, payload: bytes, is_compressed: bool) -> None:
    """
    Notify 格式:
    [8B service_uuid][4B stub_id][4B method_id][protobuf payload]
    """
    if len(payload) < 16:
        return

    service_uuid = struct.unpack_from(">Q", payload, 0)[0]  # 8 字节
    # stub_id 在 offset 8，忽略
    method_id = struct.unpack_from(">I", payload, 12)[0]    # 4 字节
    proto_payload = payload[16:]

    if is_compressed:
        proto_payload = self._decompress_zstd(proto_payload)
        if proto_payload is None:
            return

    # 路由到注册的处理器
    handler = self._handlers.get(service_uuid)
    if handler is not None:
        handler(service_uuid, method_id, proto_payload)
```

#### 5.7 处理 FrameDown（帧下发）

```python
# message_parser.py 第 193-224 行
def _handle_frame_down(self, payload: bytes, is_compressed: bool) -> None:
    """
    FrameDown 格式:
    [4B server_sequence_id][嵌套消息帧...]
    """
    if len(payload) < 4:
        return

    data = payload[4:]  # 跳过序列 ID

    if is_compressed:
        data = self._decompress_zstd(data)
        if data is None:
            return

    # 递归解析嵌套帧
    offset = 0
    while offset + 4 <= len(data):
        nested_size = struct.unpack_from(">I", data, offset)[0]
        if nested_size <= 4 or nested_size > 0x0FFFFF:
            break
        if offset + nested_size > len(data):
            break
        nested_frame = data[offset : offset + nested_size]
        self._process_message(nested_frame)  # 递归处理
        offset += nested_size
```

#### 5.8 Zstd 解压

```python
# message_parser.py 第 226-267 行
def _decompress_zstd(self, data: bytes) -> bytes | None:
    # 先跳过可跳过帧 (0x184D2A50 - 0x184D2A5F)
    offset = 0
    while offset + 8 <= len(data):
        magic = struct.unpack_from("<I", data, offset)[0]
        if ZSTD_SKIPPABLE_MIN <= magic <= ZSTD_SKIPPABLE_MAX:
            skip_size = struct.unpack_from("<I", data, offset + 4)[0]
            offset += 8 + skip_size
        else:
            break

    # 验证 Zstd magic (0xFD2FB528)
    magic = struct.unpack_from("<I", data, offset)[0]
    if magic != ZSTD_MAGIC:
        return data[offset:]  # 不是压缩数据，原样返回

    try:
        return self._decompressor.decompress(
            data[offset:], max_output_size=ZSTD_MAX_OUTPUT_SIZE  # 32MB
        )
    except zstandard.ZstdError:
        return None
```

---

### 6. 玩家追踪 (`player_tracker.py`)

#### 6.1 WorldNtf 方法 ID

```python
# player_tracker.py 第 29-34 行
METHOD_SYNC_NEAR_ENTITIES = 0x06      # 附近实体出现
METHOD_SYNC_CONTAINER_DATA = 0x15     # 容器数据同步（登录时完整数据）
METHOD_SYNC_CONTAINER_DIRTY_DATA = 0x16
METHOD_SYNC_NEAR_DELTA_INFO = 0x2D    # 批量增量更新
METHOD_SYNC_TO_ME_DELTA_INFO = 0x2E   # 针对当前玩家的增量
```

#### 6.2 属性类型 ID

```python
# player_tracker.py 第 36-51 行
ATTR_NAME = 1              # 名字（字符串）
ATTR_ID = 10               # 实体 ID
ATTR_DIR = 50              # 方向
ATTR_POS = 52              # 位置（Position protobuf）
ATTR_DST_POS = 53          # 目标位置
ATTR_PROFESSION_ID = 220   # 职业 ID
ATTR_LEVEL = 10000         # 等级
ATTR_FIGHT_POINT = 10030   # 战斗力
ATTR_HP = 11310            # 当前 HP
ATTR_MAX_HP = 11320        # 最大 HP
```

#### 6.3 职业映射

```python
# player_tracker.py 第 61-71 行
PROFESSION_NAMES: dict[int, str] = {
    1: "雷影剑士",
    2: "冰魔导师",
    3: "赤炎狂战士",
    4: "青岚骑士",
    5: "森语者",
    9: "巨刃守护者",
    11: "神射手",
    12: "神盾骑士",
    13: "灵魂乐手",
}
```

#### 6.4 消息处理入口

```python
# player_tracker.py 第 319-352 行
def handle_world_ntf(self, service_uuid: int, method_id: int, payload: bytes) -> None:
    try:
        if method_id == METHOD_SYNC_CONTAINER_DATA:
            self._handle_sync_container_data(payload)
        elif method_id == METHOD_SYNC_NEAR_ENTITIES:
            self._handle_sync_near_entities(payload)
        elif method_id == METHOD_SYNC_NEAR_DELTA_INFO:
            self._handle_sync_near_delta_info(payload)
        elif method_id == METHOD_SYNC_TO_ME_DELTA_INFO:
            self._handle_sync_to_me_delta_info(payload)
```

#### 6.5 处理 SyncContainerData（登录完整同步）

```python
# player_tracker.py 第 356-442 行
def _handle_sync_container_data(self, payload: bytes) -> None:
    # 解析 protobuf
    msg = world_ntf_pb2.WorldNtf.SyncContainerData()
    msg.ParseFromString(payload)

    if not msg.HasField("v_data"):
        return

    char_data = msg.v_data

    # 记录玩家 char_id（用于后续匹配）
    if char_data.char_id != 0:
        with self._lock:
            self._my_uuid = char_data.char_id
            self._player_info.char_id = char_data.char_id

    # 从 CharBaseInfo 提取
    if char_data.HasField("char_base"):
        base = char_data.char_base
        # 更新位置
        self._update_position(base.x, base.y, base.z, base.dir, "SyncContainerData")
        # 更新名字和战斗力
        with self._lock:
            if base.name:
                self._player_info.name = base.name
            if base.fight_point:
                self._player_info.fight_point = base.fight_point

    # 从 ProfessionList 提取职业
    if char_data.HasField("profession_list"):
        prof_id = char_data.profession_list.cur_profession_id
        if prof_id:
            with self._lock:
                self._player_info.profession_id = prof_id
                self._player_info.profession_name = PROFESSION_NAMES.get(prof_id, f"Unknown({prof_id})")

    # 从 RoleLevel 提取等级
    if char_data.HasField("role_level"):
        level = char_data.role_level.level
        if level:
            self._player_info.level = level

    # 从 UserFightAttr 提取 HP
    if char_data.HasField("attr"):
        with self._lock:
            self._player_info.hp = char_data.attr.cur_hp
            self._player_info.max_hp = char_data.attr.max_hp
```

#### 6.6 处理 SyncNearEntities（附近实体）

```python
# player_tracker.py 第 444-471 行
def _handle_sync_near_entities(self, payload: bytes) -> None:
    msg = world_ntf_pb2.WorldNtf.SyncNearEntities()
    msg.ParseFromString(payload)

    for entity in msg.appear:
        # 只处理玩家角色 (ent_type == 10)
        if entity.ent_type != ENT_CHAR:
            continue

        entity_uuid = entity.uuid
        with self._lock:
            # 检查是否是当前玩家
            is_me = self._my_uuid is not None and self._uuid_matches(entity_uuid, self._my_uuid)

        if not is_me:
            continue

        if entity.HasField("attrs"):
            self._process_entity_attrs(entity.attrs, "SyncNearEntities")
```

#### 6.7 UUID 匹配逻辑

```python
# player_tracker.py 第 667-686 行
@staticmethod
def _uuid_matches(entity_uuid: int, my_uuid: int) -> bool:
    """检查实体 UUID 是否匹配玩家的 char_id"""
    # 可能直接匹配
    if entity_uuid == my_uuid:
        return True
    # 可能需要右移 16 位
    if (entity_uuid >> 16) == my_uuid:
        return True
    return False
```

#### 6.8 处理属性集合

```python
# player_tracker.py 第 546-664 行
def _process_entity_attrs(self, attrs: attr_pb2.AttrCollection, source: str) -> None:
    pos_data: bytes | None = None
    dst_pos_data: bytes | None = None
    info_changed = False

    for attr in attrs.Attrs:
        attr_id = attr.Id
        raw = attr.RawData

        # 位置属性
        if attr_id == ATTR_POS and raw:
            pos_data = raw
        elif attr_id == ATTR_DST_POS and raw:
            dst_pos_data = raw

        # 名字属性
        elif attr_id == ATTR_NAME and raw:
            name = _read_protobuf_string(raw)
            if name:
                with self._lock:
                    if self._player_info.name != name:
                        self._player_info.name = name
                        info_changed = True

        # 职业 ID
        elif attr_id == ATTR_PROFESSION_ID and raw:
            prof_id = _read_protobuf_int32(raw)
            if prof_id:
                with self._lock:
                    self._player_info.profession_id = prof_id
                    self._player_info.profession_name = PROFESSION_NAMES.get(prof_id, ...)
                    info_changed = True

        # 等级、HP、战斗力等... 类似处理

    # 解析位置（优先用 ATTR_POS）
    raw_pos = pos_data or dst_pos_data
    if raw_pos is not None:
        pos = position_pb2.Position()
        pos.ParseFromString(raw_pos)
        self._update_position(pos.x, pos.y, pos.z, pos.dir, source)
```

#### 6.9 Protobuf 字符串读取

```python
# player_tracker.py 第 135-165 行
def _read_protobuf_string(raw_data: bytes) -> str:
    """从 Attr.RawData 读取 protobuf 编码的字符串"""
    if not raw_data:
        return ""
    try:
        # CodedInputStream.ReadString() = varint长度 + utf8字节
        length, offset = _decode_varint(raw_data, 0)
        if offset < 0 or offset + length > len(raw_data):
            # 回退：直接 UTF-8 解码
            return raw_data.decode("utf-8", errors="replace")
        return raw_data[offset : offset + length].decode("utf-8", errors="replace")
    except Exception:
        return raw_data.decode("utf-8", errors="replace")
```

#### 6.10 更新位置并通知

```python
# player_tracker.py 第 690-719 行
def _update_position(self, x: float, y: float, z: float, direction: float, source: str) -> None:
    pos = PlayerPosition(
        x=x, y=y, z=z, dir=direction, timestamp=time.time(), source=source
    )

    logger.debug(f"Position update [{source}]: ({pos.x:.2f}, {pos.y:.2f}, {pos.z:.2f})")

    with self._lock:
        self._position = pos
        callbacks = list(self._position_callbacks)  # 复制回调列表

    # 在锁外调用回调，避免死锁
    for cb in callbacks:
        try:
            cb(pos)
        except Exception:
            logger.exception("Error in position update callback")
```

---

### 7. 数据流总结

```
┌──────────────────────────────────────────────────────────────────┐
│ 游戏进程启动                                                        │
│ process_ports.py 发现端口，构建 BPF filter                          │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ Scapy AsyncSniffer 捕获 TCP 包                                      │
│ sniffer.py _packet_handler()                                       │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ tcp_reassembly.py                                                  │
│ - 判断服务器→客户端方向                                              │
│ - 按 StreamKey 分流                                                 │
│ - 序列号追踪、乱序缓存、重叠处理                                      │
│ - 输出重组后的连续字节流                                              │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ message_parser.py                                                  │
│ - 缓冲字节流                                                         │
│ - 提取 4B长度前缀的帧                                                │
│ - 解析类型字段 (Notify/FrameDown)                                   │
│ - Zstd 解压                                                         │
│ - FrameDown 递归拆包                                                │
│ - 按 service_uuid 路由                                              │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ player_tracker.py                                                  │
│ handle_world_ntf()                                                 │
│ - SyncContainerData → char_id, name, profession, level, HP         │
│ - SyncNearEntities → 位置、属性                                     │
│ - SyncNearDeltaInfo → 批量增量                                      │
│ - SyncToMeDeltaInfo → 针对当前玩家                                   │
│ - UUID 匹配识别当前玩家                                              │
│ - 更新 PlayerPosition / PlayerInfo                                 │
│ - 触发回调                                                          │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ 用户代码                                                            │
│ capture.get_position() → PlayerPosition                            │
│ capture.get_player_info() → PlayerInfo                             │
└──────────────────────────────────────────────────────────────────┘
```