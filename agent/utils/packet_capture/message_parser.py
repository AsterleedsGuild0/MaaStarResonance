"""Game protocol message framing, envelope parsing, and zstd decompression.

Parses the reassembled TCP byte stream into individual messages, extracts
the protocol envelope (type, service UUID, method ID), decompresses zstd payloads,
and routes Notify messages to registered handlers.

Reference: MessageAnalyzerV2.cs from StarResonanceDps.
"""

from __future__ import annotations

import enum
import struct
from collections.abc import Callable

import zstandard

from agent.logger import logger

# --- Constants ---
WORLD_NTF_SERVICE_UUID = 1664308034
WORLD_SERVICE_UUID = 103198054

# Zstd magic bytes (little-endian in buffer)
ZSTD_MAGIC = 0xFD2FB528
ZSTD_SKIPPABLE_MIN = 0x184D2A50
ZSTD_SKIPPABLE_MAX = 0x184D2A5F
ZSTD_MAX_OUTPUT_SIZE = 32 * 1024 * 1024  # 32MB

# Message type flag for zstd compression
ZSTD_COMPRESSION_FLAG = 0x8000


class MessageType(enum.IntEnum):
    """Protocol message type enum.

    Matches MessageType.cs from the C# reference.
    """

    NONE = 0
    CALL = 1
    NOTIFY = 2
    RETURN = 3
    ECHO = 4
    FRAME_UP = 5
    FRAME_DOWN = 6


# Type alias for message handler callbacks
# (service_uuid: int, method_id: int, payload: bytes) -> None
MessageHandler = Callable[[int, int, bytes], None]


class MessageParser:
    """Parses framed messages from a reassembled TCP byte stream.

    Handles:
    - 4-byte big-endian length-prefixed message framing
    - Protocol envelope extraction (message type, compression flag)
    - Zstd decompression for compressed payloads
    - FrameDown recursive unpacking
    - Notify message routing to registered handlers
    """

    def __init__(self) -> None:
        self._buffer = bytearray()
        self._handlers: dict[int, MessageHandler] = {}
        self._decompressor = zstandard.ZstdDecompressor()

    def register_handler(self, service_uuid: int, handler: MessageHandler) -> None:
        """Register a handler for a specific service UUID.

        Args:
            service_uuid: The service UUID to handle (e.g., WORLD_NTF_SERVICE_UUID).
            handler: Callback receiving (service_uuid, method_id, payload).
        """
        self._handlers[service_uuid] = handler

    def feed(self, data: bytes) -> None:
        """Feed reassembled TCP data into the parser.

        Buffers data and extracts complete messages as they become available.

        Args:
            data: Reassembled byte data from the TCP stream.
        """
        self._buffer.extend(data)
        self._parse_frames()

    def _parse_frames(self) -> None:
        """Extract and process complete message frames from the buffer.

        Each frame has a 4-byte big-endian length prefix that includes itself.
        """
        while len(self._buffer) >= 4:
            packet_size = struct.unpack_from(">I", self._buffer, 0)[0]

            # Validity check: size must be > 4 and <= 0x0FFFFF
            if packet_size <= 4 or packet_size > 0x0FFFFF:
                # Invalid frame - try to recover by skipping one byte
                logger.debug(f"Invalid frame size: {packet_size}, skipping byte")
                self._buffer = self._buffer[1:]
                continue

            if len(self._buffer) < packet_size:
                # Incomplete frame, wait for more data
                break

            frame = bytes(self._buffer[:packet_size])
            self._buffer = self._buffer[packet_size:]
            self._process_message(frame)

    def _process_message(self, frame: bytes) -> None:
        """Process a single complete message frame.

        Args:
            frame: Complete frame bytes including the 4-byte length prefix.
        """
        if len(frame) < 6:
            return

        # Parse envelope: [4B size][2B type]
        packet_type_raw = struct.unpack_from(">H", frame, 4)[0]
        is_compressed = bool(packet_type_raw & ZSTD_COMPRESSION_FLAG)
        msg_type = MessageType(packet_type_raw & 0x7FFF)

        payload = frame[6:]

        if msg_type == MessageType.NOTIFY:
            self._handle_notify(payload, is_compressed)
        elif msg_type == MessageType.FRAME_DOWN:
            self._handle_frame_down(payload, is_compressed)
        # All other types (CALL, RETURN, ECHO, FRAME_UP, NONE) are silently dropped

    def _handle_notify(self, payload: bytes, is_compressed: bool) -> None:
        """Handle a Notify message.

        Envelope for Notify:
        - [8B] serviceUuid (big-endian uint64)
        - [4B] stubId (ignored)
        - [4B] methodId (big-endian uint32)
        - [...] protobuf payload

        Args:
            payload: Message payload after the 6-byte envelope header.
            is_compressed: Whether the payload is zstd-compressed.
        """
        if len(payload) < 16:
            return

        service_uuid = struct.unpack_from(">Q", payload, 0)[0]
        # stubId at offset 8, 4 bytes - ignored
        method_id = struct.unpack_from(">I", payload, 12)[0]
        proto_payload = payload[16:]

        if is_compressed:
            proto_payload = self._decompress_zstd(proto_payload)
            if proto_payload is None:
                return

        handler = self._handlers.get(service_uuid)
        if handler is not None:
            try:
                handler(service_uuid, method_id, proto_payload)
            except Exception:
                logger.exception(
                    f"Error in message handler for service {service_uuid}, method {method_id}"
                )

    def _handle_frame_down(self, payload: bytes, is_compressed: bool) -> None:
        """Handle a FrameDown message by recursively parsing nested frames.

        FrameDown envelope:
        - [4B] serverSequenceId (ignored)
        - [...] nested message frames

        Args:
            payload: FrameDown payload.
            is_compressed: Whether the payload is zstd-compressed.
        """
        if len(payload) < 4:
            return

        data = payload[4:]  # Skip serverSequenceId

        if is_compressed:
            data = self._decompress_zstd(data)
            if data is None:
                return

        # Recursively parse nested frames
        offset = 0
        while offset + 4 <= len(data):
            nested_size = struct.unpack_from(">I", data, offset)[0]
            if nested_size <= 4 or nested_size > 0x0FFFFF:
                break
            if offset + nested_size > len(data):
                break
            nested_frame = data[offset : offset + nested_size]
            self._process_message(nested_frame)
            offset += nested_size

    def _decompress_zstd(self, data: bytes) -> bytes | None:
        """Decompress zstd-compressed data.

        Handles skippable frames by scanning for the actual zstd magic.

        Args:
            data: Possibly compressed data.

        Returns:
            Decompressed bytes, or None on failure.
        """
        if len(data) < 4:
            return None

        offset = 0
        # Skip skippable frames (0x184D2A50 - 0x184D2A5F)
        while offset + 8 <= len(data):
            magic = struct.unpack_from("<I", data, offset)[0]
            if ZSTD_SKIPPABLE_MIN <= magic <= ZSTD_SKIPPABLE_MAX:
                skip_size = struct.unpack_from("<I", data, offset + 4)[0]
                offset += 8 + skip_size
            else:
                break

        if offset >= len(data):
            return None

        # Verify zstd magic
        if offset + 4 > len(data):
            return None
        magic = struct.unpack_from("<I", data, offset)[0]
        if magic != ZSTD_MAGIC:
            # Not actually compressed, return as-is
            return data[offset:]

        try:
            return self._decompressor.decompress(
                data[offset:], max_output_size=ZSTD_MAX_OUTPUT_SIZE
            )
        except zstandard.ZstdError:
            logger.debug("Zstd decompression failed")
            return None

    def reset(self) -> None:
        """Reset parser state (buffer only, handlers preserved)."""
        self._buffer.clear()
