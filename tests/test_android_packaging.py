"""覆盖会导致装机失败、空资源或错误运行时的 Android 打包边界。"""

import copy
import hashlib
import io
import json
import struct
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from android.build_runtime import verify_core_archive, verify_pure_wheel
from android.prepare import PROJECT_ROOT, START_NODE, framework_tag, prepare_payload
from android.verify_apk import require_elf, verify_install_metadata
from scripts.json_utils import remove_line_comments, strip_interface_json_comments


class AndroidPackagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / "project"
        self.config = json.loads(
            (PROJECT_ROOT / "android/build-config.json").read_text(encoding="utf-8")
        )
        self.write("android/build-config.json", json.dumps(self.config))
        self.write(
            "pyproject.toml",
            '[project]\nversion = "0.12.0"\ndependencies = '
            + json.dumps([f"maafw=={self.config['maafw']}"]),
        )
        self.write("requirements-android.txt", f"maafw=={self.config['maafw']}\n")
        self.interface = {
            "interface_version": 2,
            "github": "https://example.com/a//b",
            "agent": {"child_exec": "python.exe", "child_args": ["../agent/main.py"]},
            "mirrorchyan_rid": "desktop-stream",
            "task": [{"name": "钓鱼", "entry": "钓鱼入口"}],
            "resource": [{"name": "国服", "path": ["./resource/base"]}],
        }
        self.write("assets/interface.json", "// 注释\n" + json.dumps(self.interface))
        self.write("assets/resource/base/pipeline/fishing.json", '{"钓鱼入口": {}}')
        for model in ("det.onnx", "rec.onnx", "keys.txt"):
            self.write(f"assets/MaaCommonAssets/OCR/ppocr_v5/zh_cn/{model}", model)
        self.write("agent/main.py", "# init_python_env()\n")
        self.write("agent/constant/fish/data.json", '{"鱼": "鲈鱼"}')
        self.write("agent/plugins/windows/dependency.dll", "desktop-only")
        self.write("static/img/logo_transparent.png", "project-icon")
        for name in ("LICENSE", "README.md", "CONTACT"):
            self.write(name, f"project {name}")

    def write(self, name, content):
        path = self.project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_payload_is_android_only_without_mutating_desktop(self):
        source = (self.project / "assets/interface.json").read_bytes()
        output = self.root / "prepared"
        prepare_payload(self.project, output, "arm64-v8a", "0.12.0-ci.1", 10101)
        payload = output / "payload"
        interface = json.loads((payload / "interface.json").read_text(encoding="utf-8"))
        self.assertEqual((self.project / "assets/interface.json").read_bytes(), source)
        self.assertEqual(interface["github"], self.interface["github"])
        self.assertEqual(interface["task"][1:], self.interface["task"])
        self.assertEqual(interface["task"][0]["entry"], START_NODE)
        self.assertEqual(interface["agent"]["child_args"], ["agent/main.py"])
        self.assertNotIn("mirrorchyan_rid", interface)
        self.assertFalse((payload / "agent/plugins").exists())
        self.assertEqual(
            (payload / "agent/constant/fish/data.json").read_text(encoding="utf-8"),
            '{"鱼": "鲈鱼"}',
        )
        for model in ("det.onnx", "rec.onnx", "keys.txt"):
            self.assertEqual(
                (payload / "resource/base/model/ocr" / model).read_text(), model
            )
        profile = json.loads((output / "profile.json").read_text(encoding="utf-8"))
        self.assertEqual(profile["agent"]["abi"], ["arm64-v8a"])
        self.assertEqual(
            (output / profile["app"]["icon"]).read_text(), "project-icon"
        )
        startup = json.loads(
            (payload / "resource/base/pipeline/android_start.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            startup[START_NODE]["action"],
            {"type": "StartApp", "param": {"package": self.config["gamePackage"]}},
        )

    def test_missing_ocr_does_not_destroy_previous_payload(self):
        output = self.root / "prepared"
        output.mkdir()
        previous = output / "payload/interface.json"
        previous.parent.mkdir()
        previous.write_text("previous-build")
        (self.project / "assets/MaaCommonAssets/OCR/ppocr_v5/zh_cn/rec.onnx").unlink()
        with self.assertRaisesRegex(FileNotFoundError, "rec.onnx"):
            prepare_payload(self.project, output, "x86_64", "0.12.0-ci.1", 10101)
        self.assertEqual(previous.read_text(), "previous-build")

    def test_framework_mismatch_fails_before_packaging(self):
        self.write("requirements-android.txt", "maafw==5.12.3\n")
        with self.assertRaisesRegex(ValueError, "pins disagree"):
            prepare_payload(self.project, self.root / "prepared", "x86_64", "0.12.0", 1)

    def test_release_tags_use_semver_not_python_notation(self):
        for version, expected in (
            ("6.0.0b3", "v6.0.0-beta.3"),
            ("6.0.0a1", "v6.0.0-alpha.1"),
            ("6.0.0rc2", "v6.0.0-rc.2"),
            ("5.16.1", "v5.16.1"),
        ):
            with self.subTest(version=version):
                self.assertEqual(framework_tag(version), expected)

    def test_comment_parser_preserves_urls_and_escaped_quotes(self):
        value = {"url": "https://example.com/a//b", "text": '引号"后面//不是注释'}
        text = "\ufeff" + json.dumps(value, ensure_ascii=False) + " // 尾部注释\n"
        path = self.root / "interface.json"
        path.write_text(text, encoding="utf-8")
        strip_interface_json_comments(path)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), value)
        self.assertEqual(json.loads(remove_line_comments(text.lstrip("\ufeff"))), value)

    def test_rejects_host_or_other_abi_executable(self):
        header = bytearray(20)
        header[:6] = b"\x7fELF\x02\x01"
        struct.pack_into("<H", header, 18, 62)
        with self.assertRaisesRegex(ValueError, "Wrong ELF architecture"):
            require_elf(header, "arm64-v8a", "python3")

    def test_rejects_native_code_hidden_in_pure_wheel(self):
        wheel = self.root / "rapidfuzz.whl"
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr(
                "rapidfuzz-3.14.3.dist-info/WHEEL",
                "Root-Is-Purelib: true\nTag: py3-none-any\n",
            )
            archive.writestr(
                "rapidfuzz-3.14.3.dist-info/METADATA", "Name: RapidFuzz\nVersion: 3.14.3\n"
            )
            archive.writestr("rapidfuzz/fuzz_cpp.so", b"host-native-library")
        with self.assertRaisesRegex(ValueError, "pure Python wheel"):
            verify_pure_wheel(wheel, "3.14.3")

    def test_rejects_wrong_core_even_with_valid_archive_checksum(self):
        path = self.root / "core.tar.gz"
        manifest = {
            "abi": "arm64-v8a", "python": self.config["agentCore"]["python"],
            "provides": {"maafw": "5.12.3", "numpy": "2.3.2", "strenum": "0.4.15"},
        }
        data = json.dumps(manifest).encode()
        with tarfile.open(path, "w:gz") as archive:
            entry = tarfile.TarInfo("arm64-v8a/bundle/agent-core.json")
            entry.size = len(data)
            archive.addfile(entry, io.BytesIO(data))
        config = copy.deepcopy(self.config)
        config["agentCore"]["sha256"]["arm64-v8a"] = hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, "does not match"):
            verify_core_archive(path, "arm64-v8a", config)
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            verify_core_archive(path, "arm64-v8a", self.config)

    def test_rejects_debug_certificate_and_stale_apk_version(self):
        package = "io.github.asterleedsguild0.maastarresonance"
        badging = (
            f"package: name='{package}' versionCode='10101' versionName='0.12.0-ci.1'\n"
            "minSdkVersion:'29'\n"
        )
        signing = "Signer #1 certificate SHA-256 digest: " + "a" * 64
        with self.assertRaisesRegex(ValueError, "configured keystore certificate"):
            verify_install_metadata(badging, signing, package, "0.12.0-ci.1", 10101, "b" * 64)
        with self.assertRaisesRegex(ValueError, "version does not match"):
            verify_install_metadata(badging, signing, package, "0.12.0-ci.2", 10102, "a" * 64)
        upstream_badging = badging.replace(
            package, "com.aliothmoon.maafw.maastarresonance"
        )
        with self.assertRaises(ValueError):
            verify_install_metadata(
                upstream_badging, signing, package, "0.12.0-ci.1", 10101, "a" * 64
            )
        for minimum in ("minSdkVersion:'28'", ""):
            with self.subTest(minimum=minimum):
                with self.assertRaisesRegex(ValueError, "Android 10 or newer"):
                    verify_install_metadata(
                        badging.replace("minSdkVersion:'29'", minimum),
                        signing, package, "0.12.0-ci.1", 10101, "a" * 64,
                    )


if __name__ == "__main__":
    unittest.main()
