"""Player position tracking via protobuf decoding.

Extracts position data from WorldNtf messages (SyncContainerData,
SyncNearEntities, SyncNearDeltaInfo, SyncToMeDeltaInfo) and maintains
thread-safe position state with callback support.

Reference: DeltaInfoProcessors.cs, SyncNearEntitiesProcessor.cs,
SyncContainerDataProcessor.cs from StarResonanceDps.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from google.protobuf.message import DecodeError

from agent.logger import logger
from agent.utils.packet_capture.proto import (
    attr_pb2,
    char_data_pb2,
    entity_pb2,
    position_pb2,
    world_ntf_pb2,
)


# --- WorldNtf method IDs relevant to position tracking ---
METHOD_SYNC_NEAR_ENTITIES = 0x06  # 6
METHOD_SYNC_CONTAINER_DATA = 0x15  # 21
METHOD_SYNC_CONTAINER_DIRTY_DATA = 0x16  # 22
METHOD_SYNC_NEAR_DELTA_INFO = 0x2D  # 45
METHOD_SYNC_TO_ME_DELTA_INFO = 0x2E  # 46

# Attribute type IDs for position/direction
ATTR_DIR = 50
ATTR_POS = 52

# Entity type for player characters
ENT_CHAR = 10


@dataclass
class PlayerPosition:
    """Immutable snapshot of a player's position and facing direction."""

    x: float
    y: float
    z: float
    dir: float
    timestamp: float
    source: str  # Which message type provided this data

    def __repr__(self) -> str:
        return f"PlayerPosition(x={self.x:.2f}, y={self.y:.2f}, z={self.z:.2f}, dir={self.dir:.2f}, source={self.source})"


# Callback type: (position: PlayerPosition) -> None
PositionCallback = Callable[[PlayerPosition], None]


class PositionTracker:
    """Tracks the current player's position from game network messages.

    Thread-safe: position state is protected by a lock, callbacks are
    invoked outside the lock to prevent deadlocks.

    Supports both polling (``get_position()``) and push (``on_position_update(cb)``) patterns.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._position: PlayerPosition | None = None
        self._my_uuid: int | None = None
        self._callbacks: list[PositionCallback] = []

    def get_position(self) -> PlayerPosition | None:
        """Get the most recent known player position.

        Thread-safe polling API.

        Returns:
            The latest PlayerPosition, or None if no position data has been received.
        """
        with self._lock:
            return self._position

    def on_position_update(self, callback: PositionCallback) -> None:
        """Register a callback for position updates.

        The callback will be invoked on the sniffer thread whenever a new
        position is received. Keep callbacks lightweight to avoid blocking
        packet processing.

        Args:
            callback: Function receiving a PlayerPosition on each update.
        """
        with self._lock:
            self._callbacks.append(callback)

    def remove_callback(self, callback: PositionCallback) -> None:
        """Remove a previously registered callback.

        Args:
            callback: The callback to remove.
        """
        with self._lock:
            try:
                self._callbacks.remove(callback)
            except ValueError:
                pass

    def handle_world_ntf(
        self, service_uuid: int, method_id: int, payload: bytes
    ) -> None:
        """Handle a WorldNtf message and extract position data.

        This is the message handler registered with MessageParser.

        Args:
            service_uuid: The service UUID (should be WORLD_NTF_SERVICE_UUID).
            method_id: The method ID within the service.
            payload: The protobuf-encoded payload.
        """
        try:
            if method_id == METHOD_SYNC_CONTAINER_DATA:
                self._handle_sync_container_data(payload)
            elif method_id == METHOD_SYNC_NEAR_ENTITIES:
                self._handle_sync_near_entities(payload)
            elif method_id == METHOD_SYNC_NEAR_DELTA_INFO:
                self._handle_sync_near_delta_info(payload)
            elif method_id == METHOD_SYNC_TO_ME_DELTA_INFO:
                self._handle_sync_to_me_delta_info(payload)
            # METHOD_SYNC_CONTAINER_DIRTY_DATA (22) uses custom binary format, not pure protobuf
            # Skipped for now - the other 4 methods provide sufficient position data
        except DecodeError:
            logger.debug(f"Protobuf decode error for WorldNtf method {method_id}")
        except Exception:
            logger.exception(f"Error processing WorldNtf method {method_id}")

    def _handle_sync_container_data(self, payload: bytes) -> None:
        """Handle SyncContainerData (full player data sync at login).

        Extracts position from CharSerialize -> CharBaseInfo (x, y, z, dir).

        Args:
            payload: Protobuf-encoded SyncContainerData.
        """
        msg = world_ntf_pb2.WorldNtf.SyncContainerData()
        msg.ParseFromString(payload)

        if not msg.HasField("v_data"):
            return

        char_data = msg.v_data
        if not char_data.HasField("char_base"):
            return

        base = char_data.char_base
        # Store our UUID for identifying our entity in delta updates
        if char_data.char_id != 0:
            with self._lock:
                self._my_uuid = char_data.char_id
            logger.info(f"Player char_id identified: {char_data.char_id}")

        self._update_position(base.x, base.y, base.z, base.dir, "SyncContainerData")

    def _handle_sync_near_entities(self, payload: bytes) -> None:
        """Handle SyncNearEntities (entities appearing nearby).

        Scans appearing entities for player characters and extracts
        position from AttrPos/AttrDir attributes.

        Args:
            payload: Protobuf-encoded SyncNearEntities.
        """
        msg = world_ntf_pb2.WorldNtf.SyncNearEntities()
        msg.ParseFromString(payload)

        for entity in msg.appear:
            # Only process player characters
            if entity.ent_type != ENT_CHAR:
                continue

            # Check if this is our character
            entity_uuid = entity.uuid
            with self._lock:
                is_me = self._my_uuid is not None and self._uuid_matches(
                    entity_uuid, self._my_uuid
                )
            if not is_me:
                continue

            if entity.HasField("attrs"):
                pos = self._extract_position_from_attrs(entity.attrs)
                if pos is not None:
                    self._update_position(
                        pos.x, pos.y, pos.z, pos.dir, "SyncNearEntities"
                    )

    def _handle_sync_near_delta_info(self, payload: bytes) -> None:
        """Handle SyncNearDeltaInfo (batch delta updates for nearby entities).

        Args:
            payload: Protobuf-encoded SyncNearDeltaInfo.
        """
        msg = world_ntf_pb2.WorldNtf.SyncNearDeltaInfo()
        msg.ParseFromString(payload)

        for delta in msg.DeltaInfos:
            self._process_delta(delta, "SyncNearDeltaInfo")

    def _handle_sync_to_me_delta_info(self, payload: bytes) -> None:
        """Handle SyncToMeDeltaInfo (delta update targeted at current player).

        Args:
            payload: Protobuf-encoded SyncToMeDeltaInfo.
        """
        msg = world_ntf_pb2.WorldNtf.SyncToMeDeltaInfo()
        msg.ParseFromString(payload)

        if not msg.HasField("DeltaInfo"):
            return

        to_me = msg.DeltaInfo
        # SyncToMeDeltaInfo is specifically for the current player
        if to_me.HasField("BaseDelta"):
            self._process_delta(to_me.BaseDelta, "SyncToMeDeltaInfo", force_self=True)

    def _process_delta(
        self,
        delta: world_ntf_pb2.WorldNtf.AoiSyncDelta,
        source: str,
        force_self: bool = False,
    ) -> None:
        """Process a single AoiSyncDelta for position data.

        Args:
            delta: The delta update message.
            source: Description of the source message type.
            force_self: If True, treat this delta as belonging to the current player
                regardless of UUID matching.
        """
        if not force_self:
            # Check if this delta is for our character
            delta_uuid = delta.Uuid if delta.HasField("Uuid") else 0
            with self._lock:
                if self._my_uuid is None:
                    return
                if not self._uuid_matches(delta_uuid, self._my_uuid):
                    return

        if not delta.HasField("Attrs"):
            return

        pos = self._extract_position_from_attrs(delta.Attrs)
        if pos is not None:
            self._update_position(pos.x, pos.y, pos.z, pos.dir, source)

    def _extract_position_from_attrs(
        self, attrs: attr_pb2.AttrCollection
    ) -> position_pb2.Position | None:
        """Extract position from an AttrCollection's Attr list.

        Looks for AttrPos (ID=52) and AttrDir (ID=50) attributes.
        RawData for these attributes contains a serialized Position protobuf.

        Args:
            attrs: The attribute collection to search.

        Returns:
            A Position message if found, or None.
        """
        pos_data: bytes | None = None
        dir_data: bytes | None = None

        for attr in attrs.Attrs:
            attr_id = attr.Id
            if attr_id == ATTR_POS and attr.RawData:
                pos_data = attr.RawData
            elif attr_id == ATTR_DIR and attr.RawData:
                dir_data = attr.RawData

        if pos_data is None and dir_data is None:
            return None

        # Parse position from AttrPos (primary source with x, y, z, dir)
        if pos_data is not None:
            try:
                pos = position_pb2.Position()
                pos.ParseFromString(pos_data)
                return pos
            except DecodeError:
                logger.debug("Failed to decode AttrPos RawData as Position")

        # Fallback: parse direction from AttrDir
        if dir_data is not None:
            try:
                pos = position_pb2.Position()
                pos.ParseFromString(dir_data)
                # AttrDir might only have direction info; if x/y/z are all 0, merge with current
                with self._lock:
                    if (
                        self._position is not None
                        and pos.x == 0.0
                        and pos.y == 0.0
                        and pos.z == 0.0
                    ):
                        # Only direction changed
                        merged = position_pb2.Position()
                        merged.x = self._position.x
                        merged.y = self._position.y
                        merged.z = self._position.z
                        merged.dir = pos.dir if pos.dir != 0.0 else self._position.dir
                        return merged
                return pos
            except DecodeError:
                logger.debug("Failed to decode AttrDir RawData as Position")

        return None

    @staticmethod
    def _uuid_matches(entity_uuid: int, my_uuid: int) -> bool:
        """Check if an entity UUID matches the player's char_id.

        Entity UUIDs may be shifted: ``entity_uuid >> 16 == my_uuid``,
        or they may match directly.

        Args:
            entity_uuid: UUID from the entity/delta message.
            my_uuid: Player's char_id from SyncContainerData.

        Returns:
            True if the UUIDs match.
        """
        if entity_uuid == my_uuid:
            return True
        if (entity_uuid >> 16) == my_uuid:
            return True
        return False

    def _update_position(
        self, x: float, y: float, z: float, direction: float, source: str
    ) -> None:
        """Update the stored position and notify callbacks.

        Args:
            x: X coordinate.
            y: Y coordinate.
            z: Z coordinate.
            direction: Facing direction.
            source: Description of the source message.
        """
        pos = PlayerPosition(
            x=x, y=y, z=z, dir=direction, timestamp=time.time(), source=source
        )

        with self._lock:
            self._position = pos
            callbacks = list(self._callbacks)

        # Invoke callbacks outside the lock
        for cb in callbacks:
            try:
                cb(pos)
            except Exception:
                logger.exception("Error in position update callback")

    def reset(self) -> None:
        """Reset all tracking state."""
        with self._lock:
            self._position = None
            self._my_uuid = None
