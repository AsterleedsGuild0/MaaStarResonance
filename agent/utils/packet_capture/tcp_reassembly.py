"""TCP stream reassembly for game packet capture.

Tracks TCP sequence numbers per connection 4-tuple, handles out-of-order packets
with a bounded cache, and reassembles ordered byte streams for message parsing.

Reference: TcpStreamProcessor.cs from StarResonanceDps.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from agent.logger import logger

if TYPE_CHECKING:
    from collections.abc import Callable

# --- Constants matching C# reference ---
MAX_CACHE_ENTRIES = 1000
CACHE_TTL_SECONDS = 30.0
GAP_TIMEOUT_SECONDS = 2.0
IDLE_TIMEOUT_SECONDS = 10.0

# Server detection signatures
SERVER_SIGNATURE = bytes([0x00, 0x63, 0x33, 0x53, 0x42, 0x00])
LOGIN_RETURN_PREFIX = bytes(
    [0x00, 0x00, 0x00, 0x62, 0x00, 0x03, 0x00, 0x00, 0x00, 0x01]
)
LOGIN_RETURN_MID = bytes([0x00, 0x11, 0x45, 0x14, 0x00, 0x00])


@dataclass
class CacheEntry:
    """An out-of-order packet waiting for reassembly."""

    data: bytes
    timestamp: float


@dataclass(frozen=True)
class StreamKey:
    """4-tuple identifying a TCP stream direction."""

    src_ip: str
    src_port: int
    dst_ip: str
    dst_port: int


@dataclass(frozen=True)
class ServerEndpoint:
    """Identified game server endpoint."""

    ip: str
    port: int


class TcpStream:
    """State for a single TCP stream direction.

    Tracks expected sequence numbers, caches out-of-order segments,
    and reassembles contiguous data for frame parsing.
    """

    def __init__(self) -> None:
        self.next_seq: int | None = None
        self.cache: OrderedDict[int, CacheEntry] = OrderedDict()
        self.last_activity: float = time.monotonic()
        self.gap_start_time: float | None = None

    def _seq_compare(self, a: int, b: int) -> int:
        """Compare two sequence numbers with 32-bit wraparound.

        Matches the C# ``(int)(a - b)`` comparison.

        Args:
            a: First sequence number.
            b: Second sequence number.

        Returns:
            Signed difference (negative if a < b).
        """
        diff = (a - b) & 0xFFFFFFFF
        if diff >= 0x80000000:
            return diff - 0x100000000
        return diff

    def _evict_stale_cache(self) -> None:
        """Remove cache entries that have exceeded TTL."""
        now = time.monotonic()
        stale_keys = [
            k for k, v in self.cache.items() if now - v.timestamp > CACHE_TTL_SECONDS
        ]
        for key in stale_keys:
            del self.cache[key]

    def _enforce_cache_limit(self) -> None:
        """Evict oldest entries if cache exceeds maximum size."""
        while len(self.cache) > MAX_CACHE_ENTRIES:
            self.cache.popitem(last=False)

    def process_segment(self, seq: int, payload: bytes) -> bytes:
        """Process an incoming TCP segment and return reassembled data.

        Args:
            seq: TCP sequence number of this segment.
            payload: TCP payload bytes.

        Returns:
            Contiguous reassembled bytes (may be empty if segment is out of order).
        """
        now = time.monotonic()
        self.last_activity = now
        payload_len = len(payload)

        if payload_len == 0:
            return b""

        # First segment initializes the stream
        if self.next_seq is None:
            self.next_seq = (seq + payload_len) & 0xFFFFFFFF
            return payload

        cmp = self._seq_compare(seq, self.next_seq)

        if cmp == 0:
            # In-order: consume directly and drain cache
            self.gap_start_time = None
            result = bytearray(payload)
            self.next_seq = (self.next_seq + payload_len) & 0xFFFFFFFF

            # Try to consume cached segments
            while self.cache:
                if self.next_seq in self.cache:
                    entry = self.cache.pop(self.next_seq)
                    result.extend(entry.data)
                    self.next_seq = (self.next_seq + len(entry.data)) & 0xFFFFFFFF
                else:
                    break

            return bytes(result)

        elif cmp > 0:
            # Future segment: cache it
            if seq not in self.cache:
                self.cache[seq] = CacheEntry(data=payload, timestamp=now)
                self._enforce_cache_limit()

            # Check gap timeout
            if self.gap_start_time is None:
                self.gap_start_time = now
            elif now - self.gap_start_time > GAP_TIMEOUT_SECONDS:
                # Force resync: skip to this segment
                logger.debug(f"TCP gap timeout, resyncing to seq={seq}")
                self.gap_start_time = None
                return self._force_resync_to(seq)

            return b""

        else:
            # Past segment: check if it extends beyond next_seq (overlapping retransmit).
            # This commonly happens on Windows/Npcap where the same TCP data is captured
            # twice — first as a small segment, then as the full coalesced segment.
            seg_end = (seq + payload_len) & 0xFFFFFFFF
            overlap = self._seq_compare(seg_end, self.next_seq)
            if overlap > 0:
                # This segment has new data beyond next_seq. Trim the old part
                # and process the new portion as an in-order segment.
                trim = self._seq_compare(self.next_seq, seq)  # always > 0
                new_data = payload[trim:]
                self.gap_start_time = None
                result = bytearray(new_data)
                self.next_seq = (self.next_seq + len(new_data)) & 0xFFFFFFFF

                # Try to consume cached segments
                while self.cache:
                    if self.next_seq in self.cache:
                        entry = self.cache.pop(self.next_seq)
                        result.extend(entry.data)
                        self.next_seq = (self.next_seq + len(entry.data)) & 0xFFFFFFFF
                    else:
                        break

                return bytes(result)

            # Pure retransmit (no new data): ignore
            return b""

    def _force_resync_to(self, seq: int) -> bytes:
        """Force resync by skipping to the given sequence number.

        Discards all cached segments before this seq, then tries to
        reassemble from the target seq forward.

        Args:
            seq: Sequence number to resync to.

        Returns:
            Reassembled bytes from the resync point.
        """
        # Remove entries before this seq
        stale = [k for k in self.cache if self._seq_compare(k, seq) < 0]
        for k in stale:
            del self.cache[k]

        self.next_seq = seq

        # Try consuming from this point
        result = bytearray()
        while self.next_seq in self.cache:
            entry = self.cache.pop(self.next_seq)
            result.extend(entry.data)
            self.next_seq = (self.next_seq + len(entry.data)) & 0xFFFFFFFF

        return bytes(result)

    def check_idle(self) -> bool:
        """Check if this stream has been idle beyond the timeout.

        Returns:
            True if the stream should be reset due to inactivity.
        """
        return time.monotonic() - self.last_activity > IDLE_TIMEOUT_SECONDS

    def reset(self) -> None:
        """Reset all stream state (on reconnect or idle timeout)."""
        self.next_seq = None
        self.cache.clear()
        self.last_activity = time.monotonic()
        self.gap_start_time = None


class TcpReassembler:
    """Manages TCP stream reassembly for multiple connections.

    Identifies game server endpoints by signature detection or local IP matching,
    then reassembles TCP streams from servers into ordered byte data.
    """

    def __init__(
        self, on_data: Callable[[bytes], None], local_ips: set[str] | None = None
    ) -> None:
        """Initialize the reassembler.

        Args:
            on_data: Callback invoked with reassembled contiguous byte data
                from the server->client direction.
            local_ips: Set of local IP addresses owned by the game process.
                If provided, packets with dst_ip in this set are treated as
                server->client traffic (no signature detection needed).
        """
        self._streams: dict[StreamKey, TcpStream] = {}
        self._server_endpoints: set[ServerEndpoint] = set()
        self._local_ips: set[str] = local_ips or set()
        self._on_data = on_data

    @property
    def server_endpoints(self) -> set[ServerEndpoint]:
        """The detected game server endpoints."""
        return self._server_endpoints

    def set_local_ips(self, local_ips: set[str]) -> None:
        """Update the local IPs for direction detection.

        Args:
            local_ips: Set of local IP addresses.
        """
        self._local_ips = local_ips

    def process_packet(
        self,
        src_ip: str,
        src_port: int,
        dst_ip: str,
        dst_port: int,
        seq: int,
        payload: bytes,
    ) -> None:
        """Process a single TCP packet.

        Handles server detection, stream tracking, and reassembly.

        Args:
            src_ip: Source IP address.
            src_port: Source port.
            dst_ip: Destination IP address.
            dst_port: Destination port.
            seq: TCP sequence number.
            payload: TCP payload bytes.
        """
        if len(payload) == 0:
            return

        # Determine if this is a server->client packet
        is_from_server = False

        if self._local_ips:
            # If we know local IPs, use them for direction detection
            # Server->client: dst_ip is one of our local IPs AND src_ip is not
            if dst_ip in self._local_ips and src_ip not in self._local_ips:
                is_from_server = True
        else:
            # Fall back to signature-based server detection
            ep = ServerEndpoint(ip=src_ip, port=src_port)
            if ep in self._server_endpoints:
                is_from_server = True
            else:
                # Try detection
                if self._detect_server(src_ip, src_port, payload, seq, len(payload)):
                    is_from_server = True

        if not is_from_server:
            return

        key = StreamKey(src_ip, src_port, dst_ip, dst_port)
        stream = self._streams.get(key)
        if stream is None:
            stream = TcpStream()
            self._streams[key] = stream

        # Check idle timeout
        if stream.check_idle():
            logger.debug(f"TCP stream idle timeout, resetting: {key}")
            stream.reset()

        reassembled = stream.process_segment(seq, payload)
        if reassembled:
            self._on_data(reassembled)

    def _detect_server(
        self, src_ip: str, src_port: int, payload: bytes, seq: int, payload_len: int
    ) -> bool:
        """Attempt to detect the game server from packet content.

        Uses three methods (checked in order):
        1. Login return signature (only seen during initial login)
        2. Server signature bytes in nested frames
        3. Valid message envelope heuristic (Notify/FrameDown with matching length)

        Args:
            src_ip: Source IP address.
            src_port: Source port.
            payload: Packet payload.
            seq: TCP sequence number.
            payload_len: Payload length.

        Returns:
            True if server was detected (packet consumed).
        """
        # Method B: Login return signature (simpler, check first)
        if len(payload) >= 24 and payload[3] == 0x62:
            if (
                payload[:10] == LOGIN_RETURN_PREFIX
                and payload[14:20] == LOGIN_RETURN_MID
            ):
                self._set_server(src_ip, src_port, seq, payload_len)
                logger.info(f"Game server detected (login return): {src_ip}:{src_port}")
                return True

        # Method A: Server signature in nested frame data
        if len(payload) > 10 and payload[4] == 0x00:
            # Skip first 10 bytes, then scan for signature in remaining data
            inner = payload[10:]
            if self._scan_for_server_signature(inner):
                self._set_server(src_ip, src_port, seq, payload_len)
                logger.info(
                    f"Game server detected (server signature): {src_ip}:{src_port}"
                )
                return True

        # Method C: Valid message envelope heuristic
        # If the first 6 bytes look like a valid frame header with a server-side
        # message type (Notify or FrameDown), treat this as the server.
        if self._detect_by_message_envelope(payload):
            self._set_server(src_ip, src_port, seq, payload_len)
            logger.info(f"Game server detected (message envelope): {src_ip}:{src_port}")
            return True

        return False

    @staticmethod
    def _detect_by_message_envelope(payload: bytes) -> bool:
        """Detect server by checking if payload starts with a valid message envelope.

        A valid server message has:
        - 4-byte big-endian length that matches (or is close to) the payload size
        - 2-byte type where bits 0-14 are Notify(2) or FrameDown(6)

        Args:
            payload: Packet payload.

        Returns:
            True if payload looks like a valid server message.
        """
        if len(payload) < 6:
            return False

        frame_size = int.from_bytes(payload[:4], "big")
        if frame_size < 6 or frame_size > 0x0FFFFF:
            return False

        # Frame size should be <= payload length (could be start of larger frame,
        # but should at least not be wildly larger)
        # Allow some tolerance: frame might span multiple TCP segments
        # But if the frame size is reasonable and <= 1MB, accept it
        type_raw = int.from_bytes(payload[4:6], "big")
        msg_type = type_raw & 0x7FFF

        # Only accept server-to-client message types
        return msg_type in (
            2,  # Notify
            3,  # Return
            6,  # FrameDown
        )

    def _scan_for_server_signature(self, data: bytes) -> bool:
        """Scan data for the server signature pattern.

        Parses nested 4-byte length-prefixed frames and checks for the
        signature at offset 5 within inner frame data.

        Args:
            data: Data to scan.

        Returns:
            True if server signature is found.
        """
        offset = 0
        while offset + 4 <= len(data):
            if offset + 4 > len(data):
                break
            frame_size = int.from_bytes(data[offset : offset + 4], "big")
            if frame_size < 4 or frame_size > 0x0FFFFF:
                break
            if offset + frame_size > len(data):
                break
            frame_data = data[offset + 4 : offset + frame_size]
            if (
                len(frame_data) >= 11
                and frame_data[5 : 5 + len(SERVER_SIGNATURE)] == SERVER_SIGNATURE
            ):
                return True
            offset += frame_size
        return False

    def _set_server(self, ip: str, port: int, seq: int, payload_len: int) -> None:
        """Record the server endpoint and reset stream state.

        Args:
            ip: Server IP address.
            port: Server port.
            seq: Current sequence number.
            payload_len: Current payload length.
        """
        self._server_endpoints.add(ServerEndpoint(ip=ip, port=port))
        # Clear all existing streams on new server detection
        self._streams.clear()

    def reset(self) -> None:
        """Reset all state including server detection."""
        self._server_endpoints.clear()
        self._streams.clear()

    def cleanup_idle_streams(self) -> None:
        """Remove streams that have been idle beyond the timeout."""
        idle_keys = [k for k, v in self._streams.items() if v.check_idle()]
        for key in idle_keys:
            del self._streams[key]
            logger.debug(f"Cleaned up idle TCP stream: {key}")

        # Evict stale cache entries in remaining streams
        for stream in self._streams.values():
            stream._evict_stale_cache()
