# Swift installer firmware handoff

The macOS installer is maintained in `GravityLinux/installer-next` and runs
entirely in Swift. This repository supplies the Linux `gravity-fwextract`
command, packaged as `python3-gravity_firmware`. Python is required on Linux,
not on macOS.

Both `gravity-fwextract` and `gravity-fwupdate` now live in `GravityLinux/scripts`.
The former installer repository is not a build or runtime dependency. The updater
mounts the installation's ESP and calls:

```sh
gravity-fwextract /run/.system-efi/gravity /run/.vendorfw-tmp \
  --machine j700 --open-firmware /usr/lib/firmware
```

The updater replaces `/run/.system-efi/vendorfw` only after extraction succeeds.
The bootloader and initramfs consume its `firmware.cpio`, whose entries begin
with `vendorfw/`. The package also contains `firmware.tar`, `manifest.txt`,
and any firmware copies needed by U-Boot.

The source directory contains `all_firmware.tar.gz`. For j700, its layout is:

```text
board-profile.json                  version=1, boardProfileID=j700
neo-wifi/                           four qualified IZUBA Wi-Fi inputs
neo-board-data/
  metadata.json                     version=1, board=j700, radio MAC and hashes
  factory/BWC2-*                    original local factory record
  mediatek/mt7932/calibration-<mac>.bin
  mediatek/mt7932/precal-<mac>.bin
  mediatek/mt793b/neo-25G72.bin      extracted, qualified Bluetooth payload
  apple/isp_1925_03XX.dat            extracted IMX558 camera setfile
  audio/AID44/                      saved audio tuning, retained for future tools
fud_firmware/j700/Multitouch.im4p    C1FE trackpad firmware, possibly a symlink
fud_firmware/...                     referenced restore firmware files
```

Swift creates the calibration caches from that Mac's BWC2 factory record and
live Wi-Fi MAC. The Linux consumer verifies their hashes, radio identity,
command structure, and opaque RF data against the archived factory record.
It checks the Bluetooth release pin and camera size/magic, and requires the
j700 trackpad output. It does not repeat the BWC2 conversion in Python. Audio
tuning and factory inputs remain available in the raw archive; they are not
added to the kernel firmware package. No Apple firmware is distributed in this
repository or its RPM.

j700 has no ASMedia extraction step and needs no kernelcache to rebuild this
package. j773g retains its existing archive layout and requires a saved
`kernelcache*` beside `all_firmware.tar.gz`. Legacy j773g archives without
`board-profile.json` remain supported. If board metadata exists, a mismatched
`--machine` or unsupported metadata version is rejected.

Add a Linux board consumer as one `gravity_firmware/profiles/j<product>.py`
file exporting `collect(raw, source, package, open_firmware)`. Discovery and
CLI choices are automatic. Its macOS collector remains in installer-next.

## Validation

Run the ordinary tests in this repository:

```sh
make check
```

To compare the actual Swift and Linux writers, first export synthetic bundles
from installer-next:

```sh
GRAVITY_FIRMWARE_COMPAT_FIXTURES=/tmp/gravity-firmware-fixtures \
  ./test.sh --filter exportLinuxFirmwareCompatibilityFixtures
```

Then, in this repository:

```sh
GRAVITY_FIRMWARE_COMPAT_FIXTURES=/tmp/gravity-firmware-fixtures \
  python3 -m unittest discover -s tests -p test_swift_handoff.py -v
```

This compares firmware payloads from both TAR and CPIO, manifests, hardlinks,
and U-Boot files for j700 and j773g. The j700 positive fixture substitutes a
synthetic Bluetooth hash only within the test; production always uses the
qualified payload hash. These tests establish archive compatibility, not
hardware or boot qualification.

## Shipping

The `gravity-scripts` source RPM builds both the scripts and the existing
`python3-gravity_firmware` binary RPM. Merge this source change and the companion
`GravityLinux/packages` change, then build and publish the resulting RPMs and
include them in the OS image. The retired `gravity-installer` source RPM is no
longer needed. Git merges alone do not update installed tools or OS images.
