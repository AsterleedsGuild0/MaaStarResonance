"""Windows game process port discovery via ctypes P/Invoke.

Uses iphlpapi.dll GetExtendedTcpTable/GetExtendedUdpTable to discover TCP/UDP ports
owned by the game process, then builds BPF filter strings for Scapy.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import struct
from dataclasses import dataclass, field

from agent.logger import logger

# Game process names (without .exe extension)
GAME_PROCESS_NAMES: list[str] = ["star", "BPSR_STEAM", "BPSR_EPIC", "BPSR"]

# --- Windows API constants ---
AF_INET = 2
TCP_TABLE_OWNER_PID_ALL = 5
UDP_TABLE_OWNER_PID = 1

# --- ctypes structures for TCP/UDP table entries ---


class MIB_TCPROW_OWNER_PID(ctypes.Structure):
    """Single row in the extended TCP table with owning PID."""

    _fields_ = [
        ("dwState", ctypes.wintypes.DWORD),
        ("dwLocalAddr", ctypes.wintypes.DWORD),
        ("dwLocalPort", ctypes.wintypes.DWORD),
        ("dwRemoteAddr", ctypes.wintypes.DWORD),
        ("dwRemotePort", ctypes.wintypes.DWORD),
        ("dwOwningPid", ctypes.wintypes.DWORD),
    ]


class MIB_UDPROW_OWNER_PID(ctypes.Structure):
    """Single row in the extended UDP table with owning PID."""

    _fields_ = [
        ("dwLocalAddr", ctypes.wintypes.DWORD),
        ("dwLocalPort", ctypes.wintypes.DWORD),
        ("dwOwningPid", ctypes.wintypes.DWORD),
    ]


@dataclass
class GamePorts:
    """Container for discovered game process ports."""

    tcp_ports: set[int] = field(default_factory=set)
    udp_ports: set[int] = field(default_factory=set)
    pids: set[int] = field(default_factory=set)

    @property
    def has_ports(self) -> bool:
        """Check if any ports were discovered."""
        return bool(self.tcp_ports or self.udp_ports)


def _find_game_pids() -> set[int]:
    """Find PIDs of all running game processes using Windows API.

    Uses CreateToolhelp32Snapshot + Process32First/Next to enumerate processes.

    Returns:
        Set of PIDs belonging to game processes.
    """
    TH32CS_SNAPPROCESS = 0x00000002

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", ctypes.wintypes.DWORD),
            ("cntUsage", ctypes.wintypes.DWORD),
            ("th32ProcessID", ctypes.wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", ctypes.wintypes.DWORD),
            ("cntThreads", ctypes.wintypes.DWORD),
            ("th32ParentProcessID", ctypes.wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", ctypes.wintypes.DWORD),
            ("szExeFile", ctypes.c_wchar * 260),
        ]

    kernel32 = ctypes.windll.kernel32
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == ctypes.wintypes.HANDLE(-1).value:
        logger.warning("Failed to create process snapshot")
        return set()

    pids: set[int] = set()
    pe = PROCESSENTRY32W()
    pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)

    try:
        if kernel32.Process32FirstW(snapshot, ctypes.byref(pe)):
            while True:
                exe_name = pe.szExeFile
                # Strip .exe extension for comparison
                name_no_ext = (
                    exe_name.rsplit(".", 1)[0] if "." in exe_name else exe_name
                )
                if name_no_ext in GAME_PROCESS_NAMES:
                    pids.add(pe.th32ProcessID)
                if not kernel32.Process32NextW(snapshot, ctypes.byref(pe)):
                    break
    finally:
        kernel32.CloseHandle(snapshot)

    return pids


def _get_tcp_ports_for_pids(pids: set[int]) -> set[int]:
    """Get all TCP local ports owned by the given PIDs.

    Uses GetExtendedTcpTable from iphlpapi.dll.

    Args:
        pids: Set of process IDs to filter by.

    Returns:
        Set of local TCP port numbers.
    """
    if not pids:
        return set()

    iphlpapi = ctypes.windll.iphlpapi
    ports: set[int] = set()

    # First call to get required buffer size
    buf_size = ctypes.wintypes.DWORD(0)
    iphlpapi.GetExtendedTcpTable(
        None, ctypes.byref(buf_size), False, AF_INET, TCP_TABLE_OWNER_PID_ALL, 0
    )

    if buf_size.value == 0:
        return ports

    buf = (ctypes.c_byte * buf_size.value)()
    ret = iphlpapi.GetExtendedTcpTable(
        buf, ctypes.byref(buf_size), False, AF_INET, TCP_TABLE_OWNER_PID_ALL, 0
    )

    if ret != 0:
        logger.warning(f"GetExtendedTcpTable failed with error code {ret}")
        return ports

    # Parse table: first DWORD is row count, followed by MIB_TCPROW_OWNER_PID entries
    num_entries = struct.unpack_from("<I", buf, 0)[0]
    row_size = ctypes.sizeof(MIB_TCPROW_OWNER_PID)
    offset = 4  # Skip dwNumEntries

    for _ in range(num_entries):
        if offset + row_size > buf_size.value:
            break
        row = MIB_TCPROW_OWNER_PID.from_buffer_copy(buf, offset)
        if row.dwOwningPid in pids:
            # Port is stored in network byte order (big-endian) in low 16 bits
            port = ((row.dwLocalPort & 0xFF) << 8) | ((row.dwLocalPort >> 8) & 0xFF)
            if port > 0:
                ports.add(port)
        offset += row_size

    return ports


def _get_udp_ports_for_pids(pids: set[int]) -> set[int]:
    """Get all UDP local ports owned by the given PIDs.

    Uses GetExtendedUdpTable from iphlpapi.dll.

    Args:
        pids: Set of process IDs to filter by.

    Returns:
        Set of local UDP port numbers.
    """
    if not pids:
        return set()

    iphlpapi = ctypes.windll.iphlpapi
    ports: set[int] = set()

    # First call to get required buffer size
    buf_size = ctypes.wintypes.DWORD(0)
    iphlpapi.GetExtendedUdpTable(
        None, ctypes.byref(buf_size), False, AF_INET, UDP_TABLE_OWNER_PID, 0
    )

    if buf_size.value == 0:
        return ports

    buf = (ctypes.c_byte * buf_size.value)()
    ret = iphlpapi.GetExtendedUdpTable(
        buf, ctypes.byref(buf_size), False, AF_INET, UDP_TABLE_OWNER_PID, 0
    )

    if ret != 0:
        logger.warning(f"GetExtendedUdpTable failed with error code {ret}")
        return ports

    # Parse table: first DWORD is row count, followed by MIB_UDPROW_OWNER_PID entries
    num_entries = struct.unpack_from("<I", buf, 0)[0]
    row_size = ctypes.sizeof(MIB_UDPROW_OWNER_PID)
    offset = 4

    for _ in range(num_entries):
        if offset + row_size > buf_size.value:
            break
        row = MIB_UDPROW_OWNER_PID.from_buffer_copy(buf, offset)
        if row.dwOwningPid in pids:
            port = ((row.dwLocalPort & 0xFF) << 8) | ((row.dwLocalPort >> 8) & 0xFF)
            if port > 0:
                ports.add(port)
        offset += row_size

    return ports


def discover_game_ports() -> GamePorts:
    """Discover all TCP/UDP ports owned by the game process.

    Returns:
        GamePorts instance with discovered ports and PIDs.
    """
    pids = _find_game_pids()
    if not pids:
        logger.debug("No game processes found")
        return GamePorts()

    tcp_ports = _get_tcp_ports_for_pids(pids)
    udp_ports = _get_udp_ports_for_pids(pids)

    result = GamePorts(tcp_ports=tcp_ports, udp_ports=udp_ports, pids=pids)
    if result.has_ports:
        logger.debug(
            f"Discovered game ports - TCP: {sorted(tcp_ports)}, UDP: {sorted(udp_ports)}, PIDs: {sorted(pids)}"
        )
    return result


def build_bpf_filter(game_ports: GamePorts) -> str:
    """Build a BPF filter string from discovered game ports.

    Filter format matches the C# reference implementation:
    - With ports: ``(ip or ip6) and ((tcp and (port X or port Y)) or (udp and (port A or port B)))``
    - No ports: ``(ip or ip6) and (port 0)`` (match nothing)

    Args:
        game_ports: Discovered game ports.

    Returns:
        BPF filter string for Scapy.
    """
    if not game_ports.has_ports:
        return "(ip or ip6) and (port 0)"

    parts: list[str] = []

    if game_ports.tcp_ports:
        tcp_port_expr = " or ".join(f"port {p}" for p in sorted(game_ports.tcp_ports))
        parts.append(f"(tcp and ({tcp_port_expr}))")

    if game_ports.udp_ports:
        udp_port_expr = " or ".join(f"port {p}" for p in sorted(game_ports.udp_ports))
        parts.append(f"(udp and ({udp_port_expr}))")

    filter_body = " or ".join(parts)
    return f"(ip or ip6) and ({filter_body})"
