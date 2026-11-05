# SPDX-License-Identifier: MIT
"""Verify the scripts repo can install and run its firmware tools by itself."""
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

from test_j700_firmware import cpio_files

ROOT = Path(__file__).resolve().parents[1]


class FirmwareInstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.site = self.root / "usr/lib/python3/site-packages"
        self.command = self.root / "usr/bin/gravity-fwextract"
        self.make_arguments = ["make", f"DESTDIR={self.root}", "PREFIX=/usr",
                               f"PYTHON={sys.executable}",
                               "PYTHON_SITE_PACKAGES=/usr/lib/python3/site-packages"]
        subprocess.run(self.make_arguments + ["install-firmware"], cwd=ROOT,
                       check=True, capture_output=True, text=True)
        self.environment = dict(os.environ, PYTHONPATH=str(self.site))

    def tearDown(self):
        self.temporary.cleanup()

    def test_installed_launcher_and_profiles_outside_checkout(self):
        result = subprocess.run([sys.executable, str(self.command), "--help"],
                                cwd=self.root, env=self.environment,
                                check=True, capture_output=True, text=True)
        self.assertIn("j700", result.stdout)
        self.assertIn("j773g", result.stdout)
        result = subprocess.run([sys.executable, "-c",
                                 "from gravity_firmware.profiles import j700; print(j700.__file__)"],
                                cwd=self.root, env=self.environment,
                                check=True, capture_output=True, text=True)
        self.assertEqual(str(self.site / "gravity_firmware/profiles/j700.py"), result.stdout.strip())

    def test_uninstall_preserves_other_python_packages(self):
        unrelated = self.site / "unrelated.py"
        unrelated.write_text("# belongs to another package\n")
        subprocess.run(self.make_arguments + ["uninstall-firmware"], cwd=ROOT,
                       check=True, capture_output=True, text=True)
        self.assertFalse(self.command.exists())
        self.assertFalse((self.site / "gravity_firmware").exists())
        self.assertTrue(unrelated.exists())

    @unittest.skipUnless(os.environ.get("GRAVITY_FIRMWARE_COMPAT_FIXTURES"),
                         "Export the Swift firmware fixtures first")
    def test_real_updater_uses_installed_extractor(self):
        fixture = Path(os.environ["GRAVITY_FIRMWARE_COMPAT_FIXTURES"]) / "j773g"
        output = self.root / "vendorfw"
        output.mkdir()
        (output / "old-firmware").touch()
        # Run the real installed launcher under this test's interpreter, which
        # may be a venv containing the distro's unbundled ASN.1 dependency.
        launcher = self.root / "run-installed-extractor"
        launcher.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + " " +
                            shlex.quote(str(self.command)) + ' "$@"\n')
        launcher.chmod(0o755)
        environment = dict(self.environment, GRAVITYFW=str(fixture / "source"),
                           VENDORFW=str(output), VENDORFWTMP=str(self.root / "staging"),
                           FWEXTRACT=str(launcher), GRAVITY_MACHINE="j773g")
        subprocess.run(["sh", str(ROOT / "gravity-fwupdate")], cwd=self.root,
                       env=environment, check=True, capture_output=True, text=True)
        self.assertFalse((output / "old-firmware").exists())
        self.assertEqual(cpio_files(fixture / "expected/firmware.cpio"),
                         cpio_files(output / "firmware.cpio"))
        self.assertEqual((fixture / "expected/manifest.txt").read_bytes(),
                         (output / "manifest.txt").read_bytes())


if __name__ == "__main__":
    unittest.main()
