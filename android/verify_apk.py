"""检查 MaaFwApp APK 的证书、安装身份、资源和目标 ABI 运行时。"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import struct
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from android.prepare import ABIS, START_NODE, load_config

ELF_MACHINE = {"arm64-v8a": 183, "x86_64": 62}


def require_elf(header: bytes, abi: str, name: str) -> None:
    """检查 ELF 位数与机器类型，避免把构建机的解释器或另一 ABI 打包。"""
    if (
        len(header) < 20 or header[:6] != b"\x7fELF\x02\x01"
        or struct.unpack_from("<H", header, 18)[0] != ELF_MACHINE[abi]
    ):
        raise ValueError(f"Wrong ELF architecture: {name}, expected {abi}")


def verify_contents(apk: Path, abi: str, config: dict[str, Any]) -> None:
    """校验内嵌 PI、Agent 描述符及 bundle，而不依赖 APK 文件名。"""
    with zipfile.ZipFile(apk) as archive:
        names = set(archive.namelist())
        packed_abis = {
            name.split("/")[1] for name in names
            if name.startswith("lib/") and name.endswith(".so")
        }
        if packed_abis != {abi}:
            raise ValueError(f"APK ABI mismatch: {sorted(packed_abis)}, expected {abi}")
        for library in (
            "MaaFramework", "MaaUtils", "MaaAndroidNativeControlUnit",
            "MaaAgentClient", "MaaAgentServer", "bridge", "launcher", "agentexec",
        ):
            name = f"lib/{abi}/lib{library}.so"
            with archive.open(name) as stream:
                require_elf(stream.read(20), abi, name)
        with zipfile.ZipFile(io.BytesIO(archive.read("assets/pi.zip"))) as payload:
            required = {
                "interface.json", "agent/main.py", "LICENSE", "README.md", "CONTACT",
                "logo.png", "android-build.json",
                "resource/base/model/ocr/det.onnx",
                "resource/base/model/ocr/rec.onnx",
                "resource/base/model/ocr/keys.txt",
                "resource/base/pipeline/android_start.json",
            }
            missing = required - set(payload.namelist())
            if missing:
                raise ValueError(f"APK payload is incomplete: {sorted(missing)}")
            interface = json.loads(payload.read("interface.json"))
            if interface["agent"] != {"child_exec": "python3", "child_args": ["agent/main.py"]}:
                raise ValueError("APK still contains a desktop Agent command")
            build = json.loads(payload.read("android-build.json"))
            if build["abi"] != abi or build["maafw"] != config["maafw"]:
                raise ValueError("APK payload and native runtime pins disagree")
            startup = json.loads(payload.read("resource/base/pipeline/android_start.json"))
            if startup[START_NODE]["action"]["param"]["package"] != config["gamePackage"]:
                raise ValueError("Virtual-display startup targets the wrong game")
        descriptor = json.loads(archive.read("assets/agent/agent-runtime.json"))
        runtime = descriptor["runtimes"]
        if len(runtime) != 1 or runtime[0]["executable"] != "bin/python3":
            raise ValueError("APK Python runtime descriptor is not launchable")
        bundle_bytes = archive.read("assets/agent/bundle.zip")
        fingerprint = archive.read("assets/agent.fingerprint").decode().strip()
        if hashlib.sha256(bundle_bytes).hexdigest() != fingerprint:
            raise ValueError("APK Agent bundle fingerprint mismatch")
        with zipfile.ZipFile(io.BytesIO(bundle_bytes)) as bundle:
            if {name.split("/")[0] for name in bundle.namelist()} != {abi}:
                raise ValueError("Agent bundle contains the wrong ABI")
            manifest = json.loads(bundle.read(f"{abi}/agent-core.json"))
            if (
                manifest["abi"] != abi
                or manifest["python"] != config["agentCore"]["python"]
                or manifest["provides"]["maafw"] != config["maafw"]
            ):
                raise ValueError("APK Agent Core does not match the native framework")
            with bundle.open(f"{abi}/bin/python3") as stream:
                require_elf(stream.read(20), abi, "Agent Python")


def verify_install_metadata(
    badging: str, signing: str, application_id: str,
    version: str, version_code: int, certificate: str,
) -> None:
    """核对 aapt2 与 apksigner 的真实产物输出，而非 Gradle 配置值。"""
    attributes = dict(re.findall(r"(\w+)='([^']*)'", badging.splitlines()[0]))
    if (
        attributes.get("name") != application_id
        or attributes.get("versionName") != version
        or attributes.get("versionCode") != str(version_code)
    ):
        raise ValueError("APK application ID or version does not match this build")
    minimum = re.search(r"^sdkVersion:'(\d+)'", badging, re.MULTILINE)
    if minimum is None or int(minimum[1]) < 29:
        raise ValueError("Virtual-display APK must require Android 10 or newer")
    digests = re.findall(r"^Signer #\d+ certificate SHA-256 digest: (.+)$", signing, re.MULTILINE)
    normalized = {digest.replace(":", "").strip().lower() for digest in digests}
    if normalized != {certificate.replace(":", "").strip().lower()}:
        raise ValueError("APK was not signed with the configured keystore certificate")


def main() -> None:
    """对构建出的单 ABI APK 执行完整静态产物检查。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--abi", choices=ABIS, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--version-code", type=int, required=True)
    parser.add_argument("--certificate", required=True)
    parser.add_argument("--build-tools", type=Path, required=True)
    args = parser.parse_args()
    config = load_config()
    signing = subprocess.run(
        [str(args.build_tools / "apksigner"), "verify", "--print-certs", str(args.apk)],
        check=True, capture_output=True, text=True,
    ).stdout
    badging = subprocess.run(
        [str(args.build_tools / "aapt2"), "dump", "badging", str(args.apk)],
        check=True, capture_output=True, text=True,
    ).stdout
    verify_install_metadata(
        badging, signing, config["app"]["applicationId"],
        args.version, args.version_code, args.certificate,
    )
    verify_contents(args.apk, args.abi, config)
    print(f"Verified signed Android APK: {args.apk}")


if __name__ == "__main__":
    main()
