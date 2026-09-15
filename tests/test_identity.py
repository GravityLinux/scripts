# SPDX-License-Identifier: MIT
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GravityIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dt = Path(self.tmp.name) / "chosen"
        self.dt.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def shell(self, relative, command):
        script = (ROOT / relative).read_text().replace(
            "/proc/device-tree/chosen", str(self.dt)
        )
        return subprocess.run(["sh", "-c", script + "\n" + command],
                              text=True, capture_output=True)

    def test_esp_uuid_requires_gravity_property(self):
        old = self.dt / "asahi,efi-system-partition"
        old.write_bytes(b"old-uuid\x00")
        result = self.shell("functions.sh", "get_system_esp_uuid")
        self.assertEqual(1, result.returncode)
        self.assertEqual("", result.stdout)
        (self.dt / "gravity,efi-system-partition").write_bytes(b"gravity-uuid\x00")
        result = self.shell("functions.sh", "get_system_esp_uuid")
        self.assertEqual(0, result.returncode)
        self.assertEqual("gravity-uuid", result.stdout)

    def test_dracut_hostonly_selection(self):
        for module in ("99gravity-firmware", "99gravity-dev-modules"):
            relative = f"dracut/modules.d/{module}/module-setup.sh"
            self.assertEqual(0, self.shell(relative, "hostonly=; check").returncode)
            self.assertEqual(1, self.shell(relative, "hostonly=1; check").returncode)
            (self.dt / "asahi,efi-system-partition").touch()
            self.assertEqual(1, self.shell(relative, "hostonly=1; check").returncode)
            (self.dt / "gravity,efi-system-partition").touch()
            self.assertEqual(0, self.shell(relative, "hostonly=1; check").returncode)
            (self.dt / "gravity,efi-system-partition").unlink()


if __name__ == "__main__":
    unittest.main()
