# Gravity Linux scripts

This repository provides miscellaneous admin scripts for Gravity Linux.

The diagnostic command is `gravity-diagnose`. Firmware tools and initramfs
hooks use `/usr/share/gravity-scripts` and the
`gravity,efi-system-partition` device-tree property. The Asahi ESP property
is not accepted. Standalone boot assets default to `/usr/lib/gravity-boot`;
Fedora overrides these paths in `/etc/sysconfig/update-m1n1`.

Upstream `asahi,*` firmware-version properties, the Asahi GPU module and
Fedora's `asahi-audio` / `alsa-ucm-asahi` packages retain their actual names.
The Arch first-boot helper expects a `gravitylinux` keyring; Fedora uses the
separate gravity-remix-scripts package for first-boot setup.

Tests: `sh tests/test-fwupdate.sh` and
`python3 -m unittest discover -s tests`.

Fedora RPM specs and COPR integration live in Gravity's `packages` repository;
this repository does not submit builds to the upstream Asahi Packit project.

## License

Copyright The Asahi Linux Contributors

These scripts is distributed under the MIT license. See LICENSE for the license text.
