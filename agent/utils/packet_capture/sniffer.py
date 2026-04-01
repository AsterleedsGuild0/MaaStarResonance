"""Scapy AsyncSniffer backend with dynamic BPF filter and public API.

Provides the main PacketCapture class that orchestrates all components:
- Background packet sniffing via Scapy AsyncSniffer
- Periodic game process port discovery and BPF filter updates
- TCP reassembly, message parsing, and player tracking

Usage::

    from agent.utils.packet_capture import PacketCapture

    capture = PacketCapture()
    capture.start()

    # Polling API
    pos = capture.get_position()
    if pos:
        print(f"Player at ({pos.x}, {pos.y}, {pos.z}), facing {pos.dir}")

    info = capture.get_player_info()
    print(f"Name: {info.name}, Profession: {info.profession_name}")

    # Callback API
    capture.on_position_update(lambda p: print(f"Moved to {p}"))
    capture.on_player_info_update(lambda i: print(f"Info: {i}"))

    capture.stop()
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

from scapy.all import AsyncSniffer, IFACES, IP, TCP, conf

from agent.logger import logger
from agent.utils.packet_capture.message_parser import (
    WORLD_NTF_SERVICE_UUID,
    MessageParser,
)
from agent.utils.packet_capture.player_tracker import (
    PlayerInfo,
    PlayerPosition,
    PlayerTracker,
)
from agent.utils.packet_capture.process_ports import (
    GamePorts,
    build_bpf_filter,
    discover_game_ports,
)
from agent.utils.packet_capture.tcp_reassembly import TcpReassembler

if TYPE_CHECKING:
    from collections.abc import Callable

    from scapy.packet import Packet

# Port refresh interval in seconds
PORT_REFRESH_INTERVAL = 5.0

# Cleanup interval for idle TCP streams
CLEANUP_INTERVAL = 30.0


class PacketCapture:
    """Main packet capture orchestrator.

    Manages the lifecycle of:
    - Scapy AsyncSniffer (background thread)
    - Periodic port discovery (background thread)
    - TCP reassembly pipeline
    - Message parsing and player tracking

    Thread-safe: all public methods can be called from any thread.
    """

    def __init__(self) -> None:
        # Pipeline components
        self._player_tracker = PlayerTracker()
        self._message_parser = MessageParser()
        self._tcp_reassembler = TcpReassembler(on_data=self._message_parser.feed)

        # Register WorldNtf handler
        self._message_parser.register_handler(
            WORLD_NTF_SERVICE_UUID, self._player_tracker.handle_world_ntf
        )

        # Sniffer state
        self._sniffer: AsyncSniffer | None = None
        self._port_thread: threading.Thread | None = None
        self._running = threading.Event()
        self._stop_event = threading.Event()  # Signaled when stopping
        self._current_filter: str = ""
        self._current_ports: GamePorts = GamePorts()
        self._lock = threading.Lock()
        self._last_cleanup: float = 0.0

    def start(self) -> None:
        """Start packet capture.

        Begins background sniffing and periodic port discovery.
        Safe to call multiple times (subsequent calls are no-ops).
        """
        if self._running.is_set():
            logger.warning("PacketCapture is already running")
            return

        self._running.set()
        self._stop_event.clear()

        # Start port discovery thread
        self._port_thread = threading.Thread(
            target=self._port_discovery_loop, name="port-discovery", daemon=True
        )
        self._port_thread.start()

        # Initial port discovery and sniffer start
        self._refresh_ports_and_restart_sniffer()

        logger.info("PacketCapture started")

    def stop(self) -> None:
        """Stop packet capture.

        Stops the sniffer and port discovery thread. Safe to call multiple times.
        """
        if not self._running.is_set():
            return

        self._running.clear()
        self._stop_event.set()

        self._stop_sniffer()

        if self._port_thread is not None:
            self._port_thread.join(timeout=10.0)
            self._port_thread = None

        logger.info("PacketCapture stopped")

    @property
    def is_running(self) -> bool:
        """Whether the capture is currently active."""
        return self._running.is_set()

    def get_position(self) -> PlayerPosition | None:
        """Get the most recent known player position.

        Thread-safe polling API.

        Returns:
            The latest PlayerPosition, or None if no position data has been received.
        """
        return self._player_tracker.get_position()

    def get_player_info(self) -> PlayerInfo:
        """Get the current player info snapshot (name, profession, level, etc.).

        Thread-safe polling API.

        Returns:
            A copy of the current PlayerInfo.
        """
        return self._player_tracker.get_player_info()

    def on_position_update(self, callback: Callable[[PlayerPosition], None]) -> None:
        """Register a callback for position updates.

        Args:
            callback: Function receiving a PlayerPosition on each update.
        """
        self._player_tracker.on_position_update(callback)

    def on_player_info_update(self, callback: Callable[[PlayerInfo], None]) -> None:
        """Register a callback for player info updates (name, profession, etc.).

        Args:
            callback: Function receiving a PlayerInfo on each update.
        """
        self._player_tracker.on_player_info_update(callback)

    def remove_position_callback(
        self, callback: Callable[[PlayerPosition], None]
    ) -> None:
        """Remove a previously registered position callback.

        Args:
            callback: The callback to remove.
        """
        self._player_tracker.remove_position_callback(callback)

    def remove_player_info_callback(
        self, callback: Callable[[PlayerInfo], None]
    ) -> None:
        """Remove a previously registered player info callback.

        Args:
            callback: The callback to remove.
        """
        self._player_tracker.remove_player_info_callback(callback)

    def reset(self) -> None:
        """Reset all internal state without stopping capture.

        Useful when the game reconnects or switches servers.
        """
        self._tcp_reassembler.reset()
        self._message_parser.reset()
        self._player_tracker.reset()
        logger.info("PacketCapture state reset")

    def _packet_handler(self, packet: Packet) -> None:
        """Process a single captured packet.

        Called by Scapy's AsyncSniffer on the sniffer thread.

        Args:
            packet: The captured Scapy packet.
        """
        try:
            if not packet.haslayer(IP) or not packet.haslayer(TCP):
                return

            ip_layer = packet[IP]
            tcp_layer = packet[TCP]

            # Extract TCP payload
            payload = bytes(tcp_layer.payload)
            if len(payload) == 0:
                return

            # Skip Npcap artifact packets: short all-zero payloads that appear as
            # duplicates at the same TCP sequence number as the real data packet.
            # These are a known Windows/Npcap capture quirk and would corrupt
            # TCP stream reassembly if processed (they claim sequence positions
            # that belong to the real data).
            if len(payload) <= 16 and not any(payload):
                return

            self._tcp_reassembler.process_packet(
                src_ip=ip_layer.src,
                src_port=tcp_layer.sport,
                dst_ip=ip_layer.dst,
                dst_port=tcp_layer.dport,
                seq=tcp_layer.seq,
                payload=payload,
            )

            # Periodic cleanup
            now = time.monotonic()
            if now - self._last_cleanup > CLEANUP_INTERVAL:
                self._last_cleanup = now
                self._tcp_reassembler.cleanup_idle_streams()

        except Exception as exc:
            import traceback

            tb = traceback.format_exc()
            logger.error(f"Error processing captured packet: {exc!r}\n{tb}")

    def _port_discovery_loop(self) -> None:
        """Background thread that periodically refreshes game ports.

        Runs until ``_running`` is cleared. When ports change, restarts
        the sniffer with an updated BPF filter.
        """
        while self._running.is_set():
            try:
                self._refresh_ports_and_restart_sniffer()
            except Exception:
                logger.exception("Error in port discovery")

            # Wait for the refresh interval (or until stopped)
            if self._stop_event.wait(timeout=PORT_REFRESH_INTERVAL):
                break  # Stop event was set

    def _refresh_ports_and_restart_sniffer(self) -> None:
        """Discover game ports and restart sniffer if the filter changed."""
        new_ports = discover_game_ports()
        new_filter = build_bpf_filter(new_ports)
        new_ifaces = self._resolve_interfaces(new_ports.local_ips)

        with self._lock:
            if new_filter == self._current_filter:
                return
            self._current_filter = new_filter
            self._current_ports = new_ports

        logger.info(f"BPF filter updated: {new_filter}")
        if new_ifaces:
            logger.info(f"Sniffing on interfaces: {new_ifaces}")

        # Update reassembler with current local IPs for direction detection
        self._tcp_reassembler.set_local_ips(new_ports.local_ips)

        # Reset TCP reassembly and message parser state.  The old sniffer's
        # TCP streams have stale sequence numbers that will never match the
        # new connections, and the message parser buffer may contain
        # incomplete frames from the old stream.  PlayerTracker state
        # (position, player info) is deliberately preserved.
        self._tcp_reassembler.reset()
        self._message_parser.reset()

        # Restart sniffer with new filter
        self._stop_sniffer()
        self._start_sniffer(new_filter, new_ifaces)

    @staticmethod
    def _resolve_interfaces(local_ips: set[str]) -> list[str]:
        """Find Scapy interface names matching the given local IP addresses.

        Args:
            local_ips: Set of local IP addresses from game connections.

        Returns:
            List of Scapy interface names, or empty list (use default).
        """
        if not local_ips:
            return []

        matched: list[str] = []
        for iface in IFACES.data.values():
            if getattr(iface, "ip", None) in local_ips:
                matched.append(iface.name)

        return matched

    def _start_sniffer(self, bpf_filter: str, ifaces: list[str] | None = None) -> None:
        """Start the Scapy AsyncSniffer with the given BPF filter.

        Args:
            bpf_filter: BPF filter string.
            ifaces: List of interface names to sniff on. If empty/None, uses default.
        """
        try:
            # Suppress Scapy's verbose output
            conf.verb = 0

            kwargs: dict = {
                "filter": bpf_filter,
                "prn": self._packet_handler,
                "store": False,
            }
            if ifaces:
                kwargs["iface"] = ifaces if len(ifaces) > 1 else ifaces[0]

            self._sniffer = AsyncSniffer(**kwargs)
            self._sniffer.start()
            logger.debug("Scapy AsyncSniffer started")
        except Exception:
            logger.exception("Failed to start Scapy AsyncSniffer")
            self._sniffer = None

    def _stop_sniffer(self) -> None:
        """Stop the current Scapy AsyncSniffer if running."""
        if self._sniffer is not None:
            try:
                self._sniffer.stop()
            except Exception:
                pass  # Sniffer may already be stopped
            self._sniffer = None
