# Gravity Linux scripts

This repository provides miscellaneous admin scripts for Gravity Linux.

It also owns `gravity-fwextract` and the `gravity_firmware` Python package,
moved from the retired installer repository. The macOS installer remains Swift
and needs no Python. The Linux extractor consumes the firmware archive created
on the user's Mac; it distributes no Apple firmware.

The diagnostic command is `gravity-diagnose`. Firmware tools and initramfs
hooks use `/usr/share/gravity-scripts` and the
`gravity,efi-system-partition` device-tree property. The Asahi ESP property
is not accepted. Standalone boot assets default to `/usr/lib/gravity-boot`;
Fedora overrides these paths in `/etc/sysconfig/update-m1n1`.

Upstream `asahi,*` firmware-version properties, the Asahi GPU module and
Fedora's `asahi-audio` / `alsa-ucm-asahi` packages retain their actual names.
The Arch first-boot helper expects a `gravitylinux` keyring; Fedora uses the
separate gravity-remix-scripts package for first-boot setup.

Tests: `make check` (Python 3.9 or newer). `make install` installs the shell
tools, `gravity-fwextract`, and its Python modules. `make install-firmware`
installs only the Python firmware tools; both support `DESTDIR` and `PREFIX`.
`PYTHON_SITE_PACKAGES` and `FIRMWARE_BIN_DIR` can override their destinations.
Python wheels can instead be built from `pyproject.toml`; they provide the same
package and console command. RPM builds set `INSTALL_FIRMWARE=0` for the shell
installation and install the wheel separately.
Manual firmware installations also need `tar` and `liblzfse` to decompress
Apple firmware; the RPM declares these dependencies and uses Fedora's ASN.1
library in place of the bundled fallback.

`gravity-fwupdate` reads the board's product number (for example `j700` or
`j773g`) from the live device tree and passes it to `gravity-fwextract`. The
extractor owns the supported-board list. The existing `python3-gravity_firmware`
binary RPM is now built from the `gravity-scripts` source RPM so existing systems
can upgrade. See [the firmware archive contract](docs/swift-firmware-handoff.md)
for j700/j773g layouts and the paired Swift/Linux compatibility tests.

Fedora RPM specs and COPR integration live in Gravity's `packages` repository;
this repository does not submit builds to the upstream Asahi Packit project.

## License

Copyright The Asahi Linux Contributors

These scripts is distributed under the MIT license. See LICENSE for the license text.
