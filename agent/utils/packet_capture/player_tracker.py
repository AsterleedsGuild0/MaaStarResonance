"""Player tracking via protobuf decoding — position, name, profession, stats.

Extracts player data from WorldNtf messages (SyncContainerData,
SyncNearEntities, SyncNearDeltaInfo, SyncToMeDeltaInfo) and maintains
thread-safe player state with callback support.

Reference: DeltaInfoProcessors.cs, SyncNearEntitiesProcessor.cs,
SyncContainerDataProcessor.cs, ProfessionExtends.cs from StarResonanceDps.
"""

from __future__ import annotations

import struct
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from google.protobuf.message import DecodeError

from agent.logger import logger
from agent.utils.packet_capture.proto import (
    attr_pb2,
    position_pb2,
    world_ntf_pb2,
)


# --- WorldNtf method IDs ---
METHOD_SYNC_NEAR_ENTITIES = 0x06  # 6
METHOD_SYNC_CONTAINER_DATA = 0x15  # 21
METHOD_SYNC_CONTAINER_DIRTY_DATA = 0x16  # 22
METHOD_SYNC_NEAR_DELTA_INFO = 0x2D  # 45
METHOD_SYNC_TO_ME_DELTA_INFO = 0x2E  # 46

# --- EAttrType IDs (from enum_e_attr_type.proto) ---
ATTR_NAME = 1
ATTR_ID = 10  # Monster/NPC ID
ATTR_DIR = 50
ATTR_POS = 52
ATTR_DST_POS = 53  # Target/destination position (AttrTargetPos)
ATTR_PROFESSION_ID = 220
ATTR_LEVEL = 10000
ATTR_FIGHT_POINT = 10030
ATTR_RANK_LEVEL = 10060
ATTR_SEASON_LEVEL = 10070
ATTR_CRI = 11110
ATTR_LUCK = 11130
ATTR_HP = 11310
ATTR_MAX_HP = 11320
ATTR_SEASON_STRENGTH = 11440

# Entity type for player characters
ENT_CHAR = 10

# Player entity UUID marker: low 16 bits == 640
PLAYER_UUID_MARKER = 640

# --- Profession ID → name mapping ---
# From ProfessionExtends.cs / Classes.cs in StarResonanceDps
PROFESSION_NAMES: dict[int, str] = {
    1: "雷影剑士",  # Stormblade
    2: "冰魔导师",  # FrostMage
    3: "赤炎狂战士",  # FlameBerserker
    4: "青岚骑士",  # WindKnight
    5: "森语者",  # VerdantOracle
    9: "巨刃守护者",  # HeavyGuardian
    11: "神射手",  # Marksman
    12: "神盾骑士",  # ShieldKnight
    13: "灵魂乐手",  # SoulMusician
}


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
        return (
            f"PlayerPosition(x={self.x:.2f}, y={self.y:.2f}, z={self.z:.2f}, "
            f"dir={self.dir:.2f}, source={self.source})"
        )


@dataclass
class PlayerInfo:
    """Snapshot of player identity and stats.

    Fields are optional — they are filled as data arrives from different
    message types. Only non-None fields should be considered valid.
    """

    char_id: int = 0
    name: str = ""
    profession_id: int = 0
    profession_name: str = ""
    level: int = 0
    fight_point: int = 0
    rank_level: int = 0
    hp: int = 0
    max_hp: int = 0
    season_level: int = 0
    season_strength: int = 0
    timestamp: float = 0.0

    def __repr__(self) -> str:
        parts = [f"PlayerInfo(char_id={self.char_id}"]
        if self.name:
            parts.append(f"name={self.name!r}")
        if self.profession_name:
            parts.append(f"profession={self.profession_name}")
        elif self.profession_id:
            parts.append(f"profession_id={self.profession_id}")
        if self.level:
            parts.append(f"lv={self.level}")
        if self.fight_point:
            parts.append(f"fp={self.fight_point}")
        if self.max_hp:
            parts.append(f"hp={self.hp}/{self.max_hp}")
        return ", ".join(parts) + ")"


# Callback types
PositionCallback = Callable[[PlayerPosition], None]
PlayerInfoCallback = Callable[[PlayerInfo], None]


def _read_protobuf_string(raw_data: bytes) -> str:
    """Read a protobuf-encoded string from Attr.RawData.

    The C# code uses ``CodedInputStream.ReadString()`` which reads a
    varint length prefix followed by UTF-8 bytes. In proto3, a bare
    ``string`` field serialized as a complete message would be
    ``[field_tag=0x0A][varint_length][utf8_bytes]``. But Attr.RawData
    stores the value written directly via CodedInputStream, so it's
    ``[varint_length][utf8_bytes]``.

    Args:
        raw_data: The raw bytes from Attr.RawData.

    Returns:
        The decoded string, or empty string on failure.
    """
    if not raw_data:
        return ""
    try:
        # CodedInputStream.ReadString() = varint_length + utf8_bytes
        length, offset = _decode_varint(raw_data, 0)
        if offset < 0 or offset + length > len(raw_data):
            # Fallback: try direct UTF-8 decode
            return raw_data.decode("utf-8", errors="replace")
        return raw_data[offset : offset + length].decode("utf-8", errors="replace")
    except Exception:
        # Last resort: try direct decode
        try:
            return raw_data.decode("utf-8", errors="replace")
        except Exception:
            return ""


def _read_protobuf_int32(raw_data: bytes) -> int:
    """Read a protobuf-encoded int32 from Attr.RawData.

    The C# code uses ``CodedInputStream.ReadInt32()`` which reads a
    varint-encoded signed 32-bit integer.

    Args:
        raw_data: The raw bytes from Attr.RawData.

    Returns:
        The decoded integer, or 0 on failure.
    """
    if not raw_data:
        return 0
    try:
        value, _ = _decode_varint(raw_data, 0)
        # Protobuf int32 uses zigzag or plain varint; ReadInt32 reads plain varint
        # and casts to int32 (signed 32-bit)
        if value > 0x7FFFFFFF:
            value -= 0x100000000
        return value
    except Exception:
        return 0


def _read_protobuf_int64(raw_data: bytes) -> int:
    """Read a protobuf-encoded int64 from Attr.RawData.

    Args:
        raw_data: The raw bytes from Attr.RawData.

    Returns:
        The decoded integer, or 0 on failure.
    """
    if not raw_data:
        return 0
    try:
        value, _ = _decode_varint(raw_data, 0)
        if value > 0x7FFFFFFFFFFFFFFF:
            value -= 0x10000000000000000
        return value
    except Exception:
        return 0


def _decode_varint(data: bytes, offset: int) -> tuple[int, int]:
    """Decode a protobuf varint from data at offset.

    Args:
        data: The byte buffer.
        offset: Starting position.

    Returns:
        Tuple of (value, new_offset). new_offset is -1 on failure.
    """
    result = 0
    shift = 0
    pos = offset
    while pos < len(data):
        b = data[pos]
        result |= (b & 0x7F) << shift
        pos += 1
        if (b & 0x80) == 0:
            return result, pos
        shift += 7
        if shift >= 64:
            break
    return 0, -1


class PlayerTracker:
    """Tracks the current player's position, name, profession, and stats.

    Thread-safe: all state is protected by a lock, callbacks are invoked
    outside the lock to prevent deadlocks.

    Supports both polling and push (callback) patterns for position and
    player info updates.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._position: PlayerPosition | None = None
        self._player_info: PlayerInfo = PlayerInfo()
        self._my_uuid: int | None = None  # char_id (not full entity UUID)
        self._position_callbacks: list[PositionCallback] = []
        self._player_info_callbacks: list[PlayerInfoCallback] = []

    # --- Public polling API ---

    def get_position(self) -> PlayerPosition | None:
        """Get the most recent known player position.

        Thread-safe polling API.

        Returns:
            The latest PlayerPosition, or None if no data has been received.
        """
        with self._lock:
            return self._position

    def get_player_info(self) -> PlayerInfo:
        """Get the current player info snapshot.

        Thread-safe polling API. Returns a copy so callers don't see
        partial updates.

        Returns:
            A copy of the current PlayerInfo.
        """
        with self._lock:
            return PlayerInfo(**self._player_info.__dict__)

    # --- Public callback API ---

    def on_position_update(self, callback: PositionCallback) -> None:
        """Register a callback for position updates.

        Args:
            callback: Function receiving a PlayerPosition on each update.
        """
        with self._lock:
            self._position_callbacks.append(callback)

    def on_player_info_update(self, callback: PlayerInfoCallback) -> None:
        """Register a callback for player info updates (name, profession, etc.).

        Args:
            callback: Function receiving a PlayerInfo on each update.
        """
        with self._lock:
            self._player_info_callbacks.append(callback)

    def remove_position_callback(self, callback: PositionCallback) -> None:
        """Remove a previously registered position callback."""
        with self._lock:
            try:
                self._position_callbacks.remove(callback)
            except ValueError:
                pass

    def remove_player_info_callback(self, callback: PlayerInfoCallback) -> None:
        """Remove a previously registered player info callback."""
        with self._lock:
            try:
                self._player_info_callbacks.remove(callback)
            except ValueError:
                pass

    # --- Message handler (called by MessageParser) ---

    def handle_world_ntf(
        self, service_uuid: int, method_id: int, payload: bytes
    ) -> None:
        """Handle a WorldNtf message and extract player data.

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
            # METHOD_SYNC_CONTAINER_DIRTY_DATA (22) uses custom binary format
            # with 0xFFFFFFFE markers — skipped for now
        except DecodeError as exc:
            logger.debug(
                f"Protobuf decode error for WorldNtf method 0x{method_id:02X}: {exc!r}"
            )
        except Exception as exc:
            import traceback

            tb = traceback.format_exc()
            logger.error(
                f"Error processing WorldNtf method 0x{method_id:02X}: {exc!r}\n{tb}"
            )

    # --- Internal message handlers ---

    def _handle_sync_container_data(self, payload: bytes) -> None:
        """Handle SyncContainerData (full player data sync at login).

        Extracts from CharSerialize:
        - CharBaseInfo: char_id, name, x/y/z/dir, fight_point
        - ProfessionList: cur_profession_id
        - RoleLevel: level
        - UserFightAttr: cur_hp, max_hp

        Args:
            payload: Protobuf-encoded SyncContainerData.
        """
        msg = world_ntf_pb2.WorldNtf.SyncContainerData()
        msg.ParseFromString(payload)

        if not msg.HasField("v_data"):
            return

        char_data = msg.v_data
        info_changed = False

        # Store our UUID for identifying our entity in delta updates
        if char_data.char_id != 0:
            with self._lock:
                self._my_uuid = char_data.char_id
                if self._player_info.char_id != char_data.char_id:
                    self._player_info.char_id = char_data.char_id
                    info_changed = True
            logger.info(f"Player char_id identified: {char_data.char_id}")

        # Extract from CharBaseInfo
        if char_data.HasField("char_base"):
            base = char_data.char_base
            self._update_position(base.x, base.y, base.z, base.dir, "SyncContainerData")

            with self._lock:
                if base.name and self._player_info.name != base.name:
                    self._player_info.name = base.name
                    info_changed = True
                    logger.info(f"Player name from SyncContainerData: {base.name!r}")

                if (
                    base.fight_point
                    and self._player_info.fight_point != base.fight_point
                ):
                    self._player_info.fight_point = base.fight_point
                    info_changed = True

        # Extract from ProfessionList
        if char_data.HasField("profession_list"):
            prof_id = char_data.profession_list.cur_profession_id
            if prof_id:
                with self._lock:
                    if self._player_info.profession_id != prof_id:
                        self._player_info.profession_id = prof_id
                        self._player_info.profession_name = PROFESSION_NAMES.get(
                            prof_id, f"Unknown({prof_id})"
                        )
                        info_changed = True
                        logger.info(
                            f"Player profession from SyncContainerData: "
                            f"{self._player_info.profession_name} (id={prof_id})"
                        )

        # Extract from RoleLevel
        if char_data.HasField("role_level"):
            level = char_data.role_level.level
            if level:
                with self._lock:
                    if self._player_info.level != level:
                        self._player_info.level = level
                        info_changed = True

        # Extract from UserFightAttr (HP)
        if char_data.HasField("attr"):
            with self._lock:
                cur_hp = char_data.attr.cur_hp
                max_hp = char_data.attr.max_hp
                if cur_hp and self._player_info.hp != cur_hp:
                    self._player_info.hp = cur_hp
                    info_changed = True
                if max_hp and self._player_info.max_hp != max_hp:
                    self._player_info.max_hp = max_hp
                    info_changed = True

        if info_changed:
            self._notify_player_info_changed()

    def _handle_sync_near_entities(self, payload: bytes) -> None:
        """Handle SyncNearEntities (entities appearing nearby).

        For player characters (EntChar), extracts position and identity
        attributes from the entity's AttrCollection.

        Args:
            payload: Protobuf-encoded SyncNearEntities.
        """
        msg = world_ntf_pb2.WorldNtf.SyncNearEntities()
        msg.ParseFromString(payload)

        for entity in msg.appear:
            # Only process player characters
            if entity.ent_type != ENT_CHAR:
                continue

            entity_uuid = entity.uuid
            with self._lock:
                is_me = self._my_uuid is not None and self._uuid_matches(
                    entity_uuid, self._my_uuid
                )

            if not is_me:
                continue

            if entity.HasField("attrs"):
                self._process_entity_attrs(entity.attrs, "SyncNearEntities")

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

        Also extracts the player UUID from the message if not already known,
        since SyncContainerData only occurs at login and may not be captured.

        Args:
            payload: Protobuf-encoded SyncToMeDeltaInfo.
        """
        msg = world_ntf_pb2.WorldNtf.SyncToMeDeltaInfo()
        msg.ParseFromString(payload)

        if not msg.HasField("DeltaInfo"):
            return

        to_me = msg.DeltaInfo

        # Extract player UUID if not already known
        if to_me.HasField("Uuid") and to_me.Uuid != 0:
            with self._lock:
                if self._my_uuid is None:
                    char_id = to_me.Uuid >> 16
                    self._my_uuid = char_id
                    self._player_info.char_id = char_id
                    logger.info(
                        f"Player char_id identified from SyncToMeDeltaInfo: "
                        f"{char_id} (entity uuid={to_me.Uuid})"
                    )

        # SyncToMeDeltaInfo is specifically for the current player
        if to_me.HasField("BaseDelta"):
            self._process_delta(to_me.BaseDelta, "SyncToMeDeltaInfo", force_self=True)

    # --- Internal processing ---

    def _process_delta(
        self,
        delta: world_ntf_pb2.WorldNtf.AoiSyncDelta,
        source: str,
        force_self: bool = False,
    ) -> None:
        """Process a single AoiSyncDelta for player data.

        Args:
            delta: The delta update message.
            source: Description of the source message type.
            force_self: If True, treat as belonging to current player.
        """
        if not force_self:
            delta_uuid = delta.Uuid if delta.HasField("Uuid") else 0
            with self._lock:
                if self._my_uuid is None:
                    return
                if not self._uuid_matches(delta_uuid, self._my_uuid):
                    return

        if not delta.HasField("Attrs"):
            return

        self._process_entity_attrs(delta.Attrs, source)

    def _process_entity_attrs(
        self, attrs: attr_pb2.AttrCollection, source: str
    ) -> None:
        """Process an AttrCollection, extracting position and player info.

        Handles both position attributes (52/53 → Position protobuf) and
        identity attributes (1 → string, 220/10000/etc. → int32).

        Args:
            attrs: The attribute collection.
            source: Description of the source message type.
        """
        pos_data: bytes | None = None
        dst_pos_data: bytes | None = None
        info_changed = False

        for attr in attrs.Attrs:
            attr_id = attr.Id
            raw = attr.RawData

            # Position attributes
            if attr_id == ATTR_POS and raw:
                pos_data = raw
            elif attr_id == ATTR_DST_POS and raw:
                dst_pos_data = raw

            # Identity/stats attributes
            elif attr_id == ATTR_NAME and raw:
                name = _read_protobuf_string(raw)
                if name:
                    with self._lock:
                        if self._player_info.name != name:
                            self._player_info.name = name
                            info_changed = True
                            logger.info(f"Player name from {source}: {name!r}")

            elif attr_id == ATTR_PROFESSION_ID and raw:
                prof_id = _read_protobuf_int32(raw)
                if prof_id:
                    with self._lock:
                        if self._player_info.profession_id != prof_id:
                            self._player_info.profession_id = prof_id
                            self._player_info.profession_name = PROFESSION_NAMES.get(
                                prof_id, f"Unknown({prof_id})"
                            )
                            info_changed = True
                            logger.info(
                                f"Player profession from {source}: "
                                f"{self._player_info.profession_name} (id={prof_id})"
                            )

            elif attr_id == ATTR_LEVEL and raw:
                level = _read_protobuf_int32(raw)
                if level:
                    with self._lock:
                        if self._player_info.level != level:
                            self._player_info.level = level
                            info_changed = True

            elif attr_id == ATTR_FIGHT_POINT and raw:
                fp = _read_protobuf_int32(raw)
                if fp:
                    with self._lock:
                        if self._player_info.fight_point != fp:
                            self._player_info.fight_point = fp
                            info_changed = True

            elif attr_id == ATTR_RANK_LEVEL and raw:
                rl = _read_protobuf_int32(raw)
                if rl:
                    with self._lock:
                        if self._player_info.rank_level != rl:
                            self._player_info.rank_level = rl
                            info_changed = True

            elif attr_id == ATTR_HP and raw:
                hp = _read_protobuf_int64(raw)
                if hp:
                    with self._lock:
                        if self._player_info.hp != hp:
                            self._player_info.hp = hp
                            info_changed = True

            elif attr_id == ATTR_MAX_HP and raw:
                max_hp = _read_protobuf_int64(raw)
                if max_hp:
                    with self._lock:
                        if self._player_info.max_hp != max_hp:
                            self._player_info.max_hp = max_hp
                            info_changed = True

            elif attr_id == ATTR_SEASON_LEVEL and raw:
                sl = _read_protobuf_int32(raw)
                if sl:
                    with self._lock:
                        if self._player_info.season_level != sl:
                            self._player_info.season_level = sl
                            info_changed = True

            elif attr_id == ATTR_SEASON_STRENGTH and raw:
                ss = _read_protobuf_int32(raw)
                if ss:
                    with self._lock:
                        if self._player_info.season_strength != ss:
                            self._player_info.season_strength = ss
                            info_changed = True

        # Process position (prefer AttrPos over AttrDstPos)
        raw_pos = pos_data or dst_pos_data
        if raw_pos is not None:
            try:
                pos = position_pb2.Position()
                pos.ParseFromString(raw_pos)
                self._update_position(pos.x, pos.y, pos.z, pos.dir, source)
            except DecodeError:
                logger.debug("Failed to decode position attribute RawData as Position")

        if info_changed:
            self._notify_player_info_changed()

    # --- UUID matching ---

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

    # --- State updates and notifications ---

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

        logger.debug(
            f"Position update [{source}]: "
            f"({pos.x:.2f}, {pos.y:.2f}, {pos.z:.2f}), dir={pos.dir:.2f}"
        )

        with self._lock:
            self._position = pos
            callbacks = list(self._position_callbacks)

        for cb in callbacks:
            try:
                cb(pos)
            except Exception:
                logger.exception("Error in position update callback")

    def _notify_player_info_changed(self) -> None:
        """Notify all player info callbacks with a copy of current info."""
        with self._lock:
            info = PlayerInfo(**self._player_info.__dict__)
            info.timestamp = time.time()
            callbacks = list(self._player_info_callbacks)

        for cb in callbacks:
            try:
                cb(info)
            except Exception:
                logger.exception("Error in player info callback")

    def reset(self) -> None:
        """Reset all tracking state."""
        with self._lock:
            self._position = None
            self._player_info = PlayerInfo()
            self._my_uuid = None
