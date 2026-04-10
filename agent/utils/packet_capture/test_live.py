"""Test script for packet capture — periodically prints player status.

Starts live packet capture and prints all known player information
(position, name, profession, level, HP, etc.) every few seconds.

Usage (as admin):
    python -m agent.utils.packet_capture.test_live
    python -m agent.utils.packet_capture.test_live --interval 3
"""

from __future__ import annotations

import argparse
import os
import sys
import time

# Ensure project root is on sys.path
_project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from agent.utils.packet_capture import PacketCapture, PlayerInfo, PlayerPosition

# Suppress debug-level log output so only the periodic status block is
# printed.  The project logger is configured at DEBUG in agent.logger;
# raise minimum level to INFO for this script.
from agent.logger import logger as _app_logger, sink_function as _sink_fn

_app_logger.remove()
_app_logger.add(_sink_fn, level="INFO", enqueue=True, backtrace=True, diagnose=False)

# ANSI escape codes for terminal colors
_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_CYAN = "\033[36m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"


def _format_hp(hp: int, max_hp: int) -> str:
    """Format HP with percentage."""
    if max_hp == 0:
        return "--"
    pct = hp / max_hp * 100
    return f"{hp:,} / {max_hp:,} ({pct:.1f}%)"


def _format_position(pos: PlayerPosition | None) -> str:
    """Format position into a readable string."""
    if pos is None:
        return f"{_DIM}waiting for data...{_RESET}"
    age = time.time() - pos.timestamp
    age_str = f"{age:.1f}s ago" if age < 60 else f"{age / 60:.1f}m ago"
    return (
        f"({pos.x:.2f}, {pos.y:.2f}, {pos.z:.2f})  "
        f"dir={pos.dir:.1f}  "
        f"{_DIM}[{pos.source}, {age_str}]{_RESET}"
    )


def _print_status(
    capture: PacketCapture,
    tick: int,
    pos_count: int,
    info_count: int,
) -> None:
    """Print a full status block."""
    pos = capture.get_position()
    info = capture.get_player_info()

    # Clear line and print header
    print(f"\n{_BOLD}{'=' * 60}{_RESET}")
    print(f"{_BOLD} Player Status  {_DIM}(tick #{tick}){_RESET}")
    print(f"{_BOLD}{'=' * 60}{_RESET}")

    # Identity
    char_id_str = str(info.char_id) if info.char_id else f"{_DIM}--{_RESET}"
    name_str = info.name if info.name else f"{_DIM}--{_RESET}"
    print(f"  {_CYAN}char_id    {_RESET}: {char_id_str}")
    print(f"  {_CYAN}name       {_RESET}: {name_str}")

    # Profession
    if info.profession_name:
        prof_str = f"{info.profession_name} (id={info.profession_id})"
    elif info.profession_id:
        prof_str = f"Unknown (id={info.profession_id})"
    else:
        prof_str = f"{_DIM}--{_RESET}"
    print(f"  {_CYAN}profession {_RESET}: {prof_str}")

    # Level / Combat
    level_str = str(info.level) if info.level else f"{_DIM}--{_RESET}"
    fp_str = f"{info.fight_point:,}" if info.fight_point else f"{_DIM}--{_RESET}"
    rank_str = str(info.rank_level) if info.rank_level else f"{_DIM}--{_RESET}"
    print(f"  {_CYAN}level      {_RESET}: {level_str}")
    print(f"  {_CYAN}fight_point{_RESET}: {fp_str}")
    print(f"  {_CYAN}rank_level {_RESET}: {rank_str}")

    # HP
    hp_str = _format_hp(info.hp, info.max_hp) if info.max_hp else f"{_DIM}--{_RESET}"
    print(f"  {_CYAN}hp         {_RESET}: {hp_str}")

    # Season
    sl_str = str(info.season_level) if info.season_level else f"{_DIM}--{_RESET}"
    ss_str = str(info.season_strength) if info.season_strength else f"{_DIM}--{_RESET}"
    print(f"  {_CYAN}season_lv  {_RESET}: {sl_str}")
    print(f"  {_CYAN}season_str {_RESET}: {ss_str}")

    # Position
    print(f"  {_GREEN}position   {_RESET}: {_format_position(pos)}")

    # Stats
    print(f"{_BOLD}{'-' * 60}{_RESET}")
    print(f"  {_DIM}updates: position={pos_count}, player_info={info_count}{_RESET}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Live player status monitor via packet capture"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Print interval in seconds (default: 5)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable DEBUG-level logging for full diagnostic output",
    )
    args = parser.parse_args()

    if args.debug:
        # Re-configure logger to show debug output for diagnostics
        _app_logger.remove()
        _app_logger.add(
            _sink_fn, level="DEBUG", enqueue=True, backtrace=True, diagnose=False
        )

    print(f"{_BOLD}Star Resonance — Live Player Monitor{_RESET}")
    print(f"{_DIM}Requires admin privileges and Npcap.{_RESET}")
    print(f"{_DIM}Press Ctrl+C to stop.{_RESET}\n")

    capture = PacketCapture()

    # Counters (mutable container for closure)
    counts = {"pos": 0, "info": 0}

    def on_pos(pos: PlayerPosition) -> None:
        counts["pos"] += 1

    def on_info(info: PlayerInfo) -> None:
        counts["info"] += 1

    capture.on_position_update(on_pos)
    capture.on_player_info_update(on_info)

    capture.start()

    tick = 0
    try:
        while True:
            time.sleep(args.interval)
            tick += 1
            _print_status(capture, tick, counts["pos"], counts["info"])
    except KeyboardInterrupt:
        print(f"\n{_YELLOW}Stopping...{_RESET}")

    capture.stop()

    # Final summary
    print(f"\n{_BOLD}Final Status{_RESET}")
    _print_status(capture, tick, counts["pos"], counts["info"])


if __name__ == "__main__":
    main()
