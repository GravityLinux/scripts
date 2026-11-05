# SPDX-License-Identifier: MIT
import hashlib
import json
import plistlib
import struct
import subprocess
import sys
import tarfile
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

from gravity_firmware.profiles import available_profiles
from gravity_firmware.profiles import j700
from gravity_firmware.update import update_firmware


def digest(data):
    return hashlib.sha256(data).hexdigest()


def der(tag, data):
    size = len(data)
    length = bytes([size]) if size < 128 else bytes([0x82]) + struct.pack(">H", size)
    return bytes([tag]) + length + data


def write(root, name, data):
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def cpio_files(path):
    """Read newc independently, resolving duplicate-content hardlinks."""
    data, offset, files, inodes = path.read_bytes(), 0, {}, {}
    while True:
        offset = (offset + 3) & ~3
        if data[offset:offset + 6] != b"070701":
            raise AssertionError(f"Invalid newc header at {offset}")
        fields = [int(data[offset + 6 + i * 8:offset + 14 + i * 8], 16) for i in range(13)]
        inode, mode, size, namesize = fields[0], fields[1], fields[6], fields[11]
        offset += 110
        name = data[offset:offset + namesize - 1].decode("ascii")
        offset = (offset + namesize + 3) & ~3
        body = data[offset:offset + size]
        offset += size
        if name == "TRAILER!!!":
            break
        if mode & 0o170000 == 0o100000:
            if size or inode not in inodes:
                inodes[inode] = body
            files[name] = inode
    return {name: inodes[inode] for name, inode in files.items()}


class J700FirmwareTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.raw, self.source, self.dest = (self.root / name for name in ("raw", "source", "dest"))
        self.source.mkdir()
        self.saved = self.raw / "neo-board-data"
        self.address = "021122334455"
        mac, rf = bytes.fromhex(self.address), b"synthetic-rf!!!!"
        rf = rf.ljust(16, b"!")
        startup = b"MT7932C1" + mac + b"\0\0" + struct.pack("<I", 1)
        startup += bytes([0xed, 0x21, 1, 0]) + struct.pack("<I", 20) + bytes([3, 0, 16, 0]) + rf
        precal = b"MT7932P1" + mac + struct.pack("<HI", 1, 56)
        precal += bytes([3, 0, 0, 0]) + struct.pack("<I", 16) + bytes(12) + rf
        factory = b"synthetic-local-BWC2" + bytes(100) + rf
        write(self.saved, "factory/BWC2-fixture", factory)
        self.calibration = {f"mediatek/mt7932/calibration-{self.address}.bin": startup,
                            f"mediatek/mt7932/precal-{self.address}.bin": precal}
        for name, data in self.calibration.items():
            write(self.saved, name, data)
        self.bluetooth = b"synthetic-qualified-bluetooth"
        self.camera = struct.pack(">I", j700.CAMERA_MAGIC) + bytes(j700.CAMERA_SIZE - 4)
        write(self.saved, j700.BLUETOOTH_NAME, self.bluetooth)
        write(self.saved, j700.CAMERA_NAME, self.camera)
        self.wifi = {}
        for name, source in j700.WIFI_ALIASES.items():
            self.wifi[name] = source.encode("ascii")
            write(self.raw, "neo-wifi/" + source, self.wifi[name])
        config = {"C1FE-fixture": [{"Type": "Config", "Config": {
            "Interface Config": [{"bInterfaceNumber": 1}]}},
            {"Type": "Binary", "Payload": b"synthetic-trackpad", "Address": 4096}]}
        tree = ET.fromstring(plistlib.dumps(config, sort_keys=False))
        self.multitouch = der(0x30, der(0x16, b"IM4P") + der(0x16, b"mtfw") +
                              der(0x16, b"synthetic") + der(4, ET.tostring(tree[0])))
        write(self.raw, "fud_firmware/j700/Multitouch.im4p", self.multitouch)
        self.metadata = {"version": 1, "board": "j700", "wifi_address": self.address,
                         "calibration_generated_locally": True, "factory_sha256": digest(factory),
                         "bluetooth_sha256": digest(self.bluetooth), "camera_sha256": digest(self.camera),
                         "calibration": [{"name": name, "sha256": digest(data)}
                                         for name, data in self.calibration.items()]}
        self.board = {"version": 1, "boardProfileID": "j700"}

    def tearDown(self):
        self.temp.cleanup()

    def archive(self):
        write(self.saved, "metadata.json", json.dumps(self.metadata).encode())
        write(self.raw, "board-profile.json", json.dumps(self.board).encode())
        with tarfile.open(self.source / "all_firmware.tar.gz", "w:gz") as archive:
            for path in sorted(self.raw.iterdir()):
                archive.add(path, arcname=path.name)

    def extract(self, machine="j700", qualified_fixture=True):
        self.archive()
        if qualified_fixture:
            # No Apple firmware is checked in. Only replace the release pin in
            # positive synthetic tests; a separate test checks the actual pin.
            with patch.object(j700, "BLUETOOTH_SHA256", digest(self.bluetooth)):
                update_firmware(self.source, self.dest, machine=machine)
        else:
            update_firmware(self.source, self.dest, machine=machine)

    def test_complete_j700_archive_without_kernelcache(self):
        self.extract()
        expected = {**self.wifi, **self.calibration, j700.BLUETOOTH_NAME: self.bluetooth,
                    j700.CAMERA_NAME: self.camera}
        with tarfile.open(self.dest / "firmware.tar") as archive:
            files = {member.name: archive.extractfile(member).read() for member in archive}
        for name, data in expected.items():
            self.assertEqual(files[name], data)
        self.assertTrue(files["apple/tpmtfw-j700.bin"].startswith(b"HIDF"))
        cpio = cpio_files(self.dest / "firmware.cpio")
        self.assertEqual({"vendorfw/" + name: data for name, data in files.items()},
                         {name: data for name, data in cpio.items() if name != "vendorfw/.vendorfw.manifest"})
        self.assertEqual((self.dest / "manifest.txt").read_bytes(), cpio["vendorfw/.vendorfw.manifest"])

    def test_machine_discovery_and_cli(self):
        self.assertIn("j700", available_profiles())
        self.assertIn("j773g", available_profiles())
        result = subprocess.run([sys.executable, "-m", "gravity_firmware.update", "--help"],
                                text=True, capture_output=True, check=True)
        self.assertIn("j700", result.stdout)
        self.assertIn("j773g", result.stdout)

    def test_implicit_machine_uses_board_metadata(self):
        self.extract(machine=None)

    def test_wrong_machine_rejected_before_creating_output(self):
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.extract(machine="j773g")
        self.assertFalse(self.dest.exists())

    def test_unknown_archive_version_rejected(self):
        self.board["version"] = 2
        with self.assertRaisesRegex(ValueError, "metadata version"):
            self.extract()

    def test_tampered_calibration_rejected(self):
        write(self.saved, next(iter(self.calibration)), b"tampered")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.extract()

    def test_calibration_for_another_radio_rejected_even_with_updated_digest(self):
        name, data = next(iter(self.calibration.items()))
        data = data[:8] + bytes.fromhex("021122334456") + data[14:]
        write(self.saved, name, data)
        self.metadata["calibration"][0]["sha256"] = digest(data)
        with self.assertRaisesRegex(ValueError, "another radio"):
            self.extract()

    def test_calibration_unrelated_to_factory_rejected(self):
        factory = bytes(200)
        write(self.saved, "factory/BWC2-fixture", factory)
        self.metadata["factory_sha256"] = digest(factory)
        with self.assertRaisesRegex(ValueError, "does not match factory"):
            self.extract()

    def test_missing_calibration_and_ambiguous_factory_rejected(self):
        self.metadata["calibration"].pop()
        with self.assertRaisesRegex(ValueError, "Missing or duplicate"):
            self.extract()
        write(self.saved, "factory/BWC2-second", bytes(200))
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            self.extract()

    def test_unqualified_bluetooth_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unqualified"):
            self.extract(qualified_fixture=False)

    def test_missing_c1fe_trackpad_rejected(self):
        (self.raw / "fud_firmware/j700/Multitouch.im4p").unlink()
        with self.assertRaisesRegex(ValueError, "Missing trackpad"):
            self.extract()


if __name__ == "__main__":
    unittest.main()
