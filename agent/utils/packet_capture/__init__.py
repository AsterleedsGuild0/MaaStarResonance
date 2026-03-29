"""Packet capture module for Star Resonance game position tracking.

Provides real-time player position extraction from game network traffic
via Scapy packet sniffing, TCP stream reassembly, protocol parsing,
and protobuf deserialization.

Public API
----------
- :class:`PacketCapture` — Main orchestrator (start/stop/get_position/on_position_update)
- :class:`PlayerPosition` — Position data snapshot (x, y, z, dir, timestamp)

Quick start::

    from agent.utils.packet_capture import PacketCapture

    capture = PacketCapture()
    capture.start()

    # Polling
    pos = capture.get_position()

    # Callback
    capture.on_position_update(lambda p: print(p))

    capture.stop()
"""

from agent.utils.packet_capture.position_tracker import PlayerPosition
from agent.utils.packet_capture.sniffer import PacketCapture

__all__ = ["PacketCapture", "PlayerPosition"]
