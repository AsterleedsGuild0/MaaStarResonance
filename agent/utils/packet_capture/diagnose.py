"""Diagnostic script for packet capture pipeline.

Run this standalone (with admin privileges for packet sniffing) to:
1. Discover game ports and verify process detection
2. Capture raw packets to a file for offline replay
3. Replay captured packets through the pipeline with full error tracing
4. Print position data as it's extracted

Usage (as admin):
    python -m agent.utils.packet_capture.diagnose [--capture SECONDS] [--replay FILE]
    python -m agent.utils.packet_capture.diagnose --capture 30     # Capture 30s of traffic
    python -m agent.utils.packet_capture.diagnose --replay dump.bin # Replay from file
    python -m agent.utils.packet_capture.diagnose                   # Live mode (capture + process)
"""

from __future__ import annotations

import argparse
import os
import pickle
import sys
import time
import traceback

# Ensure project root is on sys.path
_project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def diagnose_ports() -> None:
    """Discover and print game ports."""
    from agent.utils.packet_capture.process_ports import (
        build_bpf_filter,
        discover_game_ports,
    )

    print("=" * 60)
    print("STEP 1: Port Discovery")
    print("=" * 60)

    ports = discover_game_ports()
    print(f"  PIDs:      {sorted(ports.pids)}")
    print(f"  TCP ports: {sorted(ports.tcp_ports)}")
    print(f"  UDP ports: {sorted(ports.udp_ports)}")
    print(f"  Local IPs: {sorted(ports.local_ips)}")
    print(f"  BPF:       {build_bpf_filter(ports)}")
    print()
    return ports


def capture_packets(duration: float, output_file: str) -> None:
    """Capture raw packets to a file for offline replay."""
    from scapy.all import IFACES, IP, TCP, AsyncSniffer, conf

    from agent.utils.packet_capture.process_ports import (
        build_bpf_filter,
        discover_game_ports,
    )

    ports = diagnose_ports()
    if not ports.has_ports:
        print("ERROR: No game ports found. Is the game running?")
        return

    bpf = build_bpf_filter(ports)

    # Resolve interfaces
    ifaces = []
    for iface in IFACES.data.values():
        if getattr(iface, "ip", None) in ports.local_ips:
            ifaces.append(iface.name)

    print(f"Capturing for {duration}s on interfaces: {ifaces or ['default']}")
    print(f"BPF filter: {bpf}")

    captured_packets = []

    def on_packet(pkt):
        if pkt.haslayer(IP) and pkt.haslayer(TCP):
            ip = pkt[IP]
            tcp = pkt[TCP]
            payload = bytes(tcp.payload)
            if payload:
                captured_packets.append(
                    {
                        "src_ip": ip.src,
                        "src_port": tcp.sport,
                        "dst_ip": ip.dst,
                        "dst_port": tcp.dport,
                        "seq": tcp.seq,
                        "payload": payload,
                        "time": time.time(),
                    }
                )

    conf.verb = 0
    kwargs = {"filter": bpf, "prn": on_packet, "store": False}
    if ifaces:
        kwargs["iface"] = ifaces if len(ifaces) > 1 else ifaces[0]

    sniffer = AsyncSniffer(**kwargs)
    sniffer.start()

    try:
        for i in range(int(duration)):
            time.sleep(1)
            print(f"  {i + 1}s: {len(captured_packets)} TCP packets with payload")
    except KeyboardInterrupt:
        pass

    sniffer.stop()

    print(f"\nCaptured {len(captured_packets)} packets total")

    # Save using pickle (binary data)
    with open(output_file, "wb") as f:
        pickle.dump(
            {
                "packets": captured_packets,
                "local_ips": list(ports.local_ips),
                "tcp_ports": list(ports.tcp_ports),
                "udp_ports": list(ports.udp_ports),
                "pids": list(ports.pids),
            },
            f,
        )
    print(f"Saved to {output_file}")


def replay_packets(input_file: str) -> None:
    """Replay captured packets through the pipeline with full error tracing."""
    from agent.utils.packet_capture.message_parser import (
        WORLD_NTF_SERVICE_UUID,
        MessageParser,
    )
    from agent.utils.packet_capture.player_tracker import PlayerTracker
    from agent.utils.packet_capture.tcp_reassembly import TcpReassembler

    print("=" * 60)
    print("REPLAYING PACKETS")
    print("=" * 60)

    with open(input_file, "rb") as f:
        data = pickle.load(f)

    packets = data["packets"]
    local_ips = set(data.get("local_ips", []))
    print(f"  Loaded {len(packets)} packets")
    print(f"  Local IPs: {sorted(local_ips)}")

    # Set up pipeline
    player_tracker = PlayerTracker()
    message_parser = MessageParser()

    # Counters
    stats = {
        "tcp_packets": 0,
        "reassembled_calls": 0,
        "messages_parsed": 0,
        "world_ntf_calls": 0,
        "positions_found": 0,
        "player_info_updates": 0,
        "errors": 0,
    }

    # Wrap message_parser.feed to count
    original_feed = message_parser.feed

    def counting_feed(data_bytes: bytes) -> None:
        stats["reassembled_calls"] += 1
        original_feed(data_bytes)

    # Wrap position handler to count
    original_handler = player_tracker.handle_world_ntf

    def counting_handler(service_uuid: int, method_id: int, payload: bytes) -> None:
        stats["world_ntf_calls"] += 1
        print(f"  [WorldNtf] method=0x{method_id:02X}, payload_len={len(payload)}")
        original_handler(service_uuid, method_id, payload)

    message_parser.register_handler(WORLD_NTF_SERVICE_UUID, counting_handler)

    def on_position(pos):
        stats["positions_found"] += 1
        print(f"  >>> POSITION: {pos}")

    def on_player_info(info):
        stats["player_info_updates"] += 1
        print(f"  >>> PLAYER INFO: {info}")

    player_tracker.on_position_update(on_position)
    player_tracker.on_player_info_update(on_player_info)

    tcp_reassembler = TcpReassembler(on_data=counting_feed, local_ips=local_ips)

    # Process each packet
    for i, pkt in enumerate(packets):
        stats["tcp_packets"] += 1

        payload = pkt["payload"]

        # Apply the same Npcap artifact filter as sniffer.py._packet_handler:
        # short all-zero payloads are Windows/Npcap capture artifacts that would
        # corrupt TCP reassembly if processed.
        if len(payload) <= 16 and not any(payload):
            stats.setdefault("npcap_artifacts_skipped", 0)
            stats["npcap_artifacts_skipped"] += 1
            continue

        try:
            tcp_reassembler.process_packet(
                src_ip=pkt["src_ip"],
                src_port=pkt["src_port"],
                dst_ip=pkt["dst_ip"],
                dst_port=pkt["dst_port"],
                seq=pkt["seq"],
                payload=payload,
            )
        except Exception as exc:
            stats["errors"] += 1
            print(f"\n  ERROR on packet #{i}:")
            print(
                f"    src={pkt['src_ip']}:{pkt['src_port']} -> "
                f"dst={pkt['dst_ip']}:{pkt['dst_port']}"
            )
            print(f"    seq={pkt['seq']}, len={len(payload)}")
            print(f"    payload[:32] = {payload[:32].hex()}")
            print(f"    exception: {exc!r}")
            traceback.print_exc()
            print()

    print("\n" + "=" * 60)
    print("REPLAY STATS")
    print("=" * 60)
    for key, val in stats.items():
        print(f"  {key}: {val}")
    pos = player_tracker.get_position()
    info = player_tracker.get_player_info()
    print(f"  final_position: {pos}")
    print(f"  final_player_info: {info}")
    print(f"  server_endpoints: {tcp_reassembler.server_endpoints}")


def live_mode() -> None:
    """Live capture with full diagnostic output."""
    from agent.utils.packet_capture import PacketCapture

    ports = diagnose_ports()
    if not ports.has_ports:
        print("ERROR: No game ports found. Is the game running?")
        return

    print("=" * 60)
    print("STEP 2: Live Capture")
    print("=" * 60)

    capture = PacketCapture()

    position_count = [0]
    info_count = [0]

    def on_pos(pos):
        position_count[0] += 1
        print(f"  [pos #{position_count[0]}] {pos}")

    def on_info(info):
        info_count[0] += 1
        print(f"  [info #{info_count[0]}] {info}")

    capture.on_position_update(on_pos)
    capture.on_player_info_update(on_info)
    capture.start()

    try:
        print("Listening... Press Ctrl+C to stop.\n")
        while True:
            time.sleep(5)
            pos = capture.get_position()
            info = capture.get_player_info()
            if pos:
                print(f"  [poll] Position: {pos}")
            else:
                print("  [poll] No position data yet")
            if info.char_id:
                print(f"  [poll] Player: {info}")
    except KeyboardInterrupt:
        print("\nStopping...")

    capture.stop()
    print(f"\nTotal position updates: {position_count[0]}")
    print(f"Total player info updates: {info_count[0]}")
    final = capture.get_position()
    final_info = capture.get_player_info()
    print(f"Final position: {final}")
    print(f"Final player info: {final_info}")


def main():
    parser = argparse.ArgumentParser(description="Packet capture diagnostic tool")
    parser.add_argument(
        "--capture",
        type=float,
        default=0,
        help="Capture packets for N seconds to a dump file",
    )
    parser.add_argument(
        "--replay", type=str, default="", help="Replay packets from a dump file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="packet_dump.pkl",
        help="Output file for --capture mode",
    )
    parser.add_argument(
        "--ports-only", action="store_true", help="Only run port discovery"
    )

    args = parser.parse_args()

    if args.ports_only:
        diagnose_ports()
    elif args.capture > 0:
        capture_packets(args.capture, args.output)
    elif args.replay:
        replay_packets(args.replay)
    else:
        live_mode()


if __name__ == "__main__":
    main()
