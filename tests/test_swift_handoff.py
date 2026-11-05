# SPDX-License-Identifier: MIT
"""Cross-language tests using synthetic bundles exported by installer-next.

See docs/swift-firmware-handoff.md for the two commands that run both halves.
No Apple binaries or hardware-specific calibration are checked into either repo.
"""
import json
import os
import tarfile
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from gravity_firmware.profiles import j700
from gravity_firmware.update import update_firmware
from test_j700_firmware import cpio_files


def tar_files(path):
    with tarfile.open(path) as archive:
        return {entry.name: archive.extractfile(entry).read()
                for entry in archive if entry.isfile() or entry.islnk()}


@unittest.skipUnless(os.environ.get("GRAVITY_FIRMWARE_COMPAT_FIXTURES"),
                     "Export fixtures from installer-next to run the integration test")
class SwiftHandoffTests(unittest.TestCase):
    def test_swift_and_linux_firmware_match(self):
        root = Path(os.environ["GRAVITY_FIRMWARE_COMPAT_FIXTURES"])
        for machine in ("j700", "j773g"):
            with self.subTest(machine=machine), tempfile.TemporaryDirectory() as temp:
                fixture, output = root / machine, Path(temp)
                context = nullcontext()
                if machine == "j700":
                    metadata = json.loads((fixture / "fixture.json").read_text())
                    self.assertIs(metadata["synthetic"], True)
                    context = patch.object(j700, "BLUETOOTH_SHA256", metadata["bluetooth_sha256"])
                with context:
                    update_firmware(fixture / "source", output, machine=machine)
                expected = fixture / "expected"
                self.assertEqual(tar_files(expected / "firmware.tar"), tar_files(output / "firmware.tar"))
                self.assertEqual(cpio_files(expected / "firmware.cpio"), cpio_files(output / "firmware.cpio"))
                self.assertEqual((expected / "manifest.txt").read_bytes(), (output / "manifest.txt").read_bytes())
                for name in ("u-boot",):
                    def files(base):
                        return {str(path.relative_to(base)): path.read_bytes()
                                for path in (base / name).rglob("*") if path.is_file()}
                    self.assertEqual(files(expected), files(output))


if __name__ == "__main__":
    unittest.main()
