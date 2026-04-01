"""Packet capture module for Star Resonance game player tracking.

Provides real-time player data extraction from game network traffic
via Scapy packet sniffing, TCP stream reassembly, protocol parsing,
and protobuf deserialization.

Public API
----------
- :class:`PacketCapture` — Main orchestrator (start/stop/get_position/get_player_info)
- :class:`PlayerPosition` — Position data snapshot (x, y, z, dir, timestamp)
- :class:`PlayerInfo` — Player identity/stats snapshot (name, profession, level, HP, etc.)

Quick start::

    from agent.utils.packet_capture import PacketCapture

    capture = PacketCapture()
    capture.start()

    # Polling
    pos = capture.get_position()
    info = capture.get_player_info()

    # Callbacks
    capture.on_position_update(lambda p: print(p))
    capture.on_player_info_update(lambda i: print(i))

    capture.stop()
"""

from agent.utils.packet_capture.player_tracker import PlayerInfo, PlayerPosition
from agent.utils.packet_capture.sniffer import PacketCapture

__all__ = ["PacketCapture", "PlayerInfo", "PlayerPosition"]
