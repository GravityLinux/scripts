# SPDX-License-Identifier: MIT
"""Consume the Swift installer's version-1 j700 firmware archive on Linux.

Swift extracts the hardware-bound caches from BWC2 while macOS is available.
Linux verifies and repackages those caches; it does not probe a different Mac
or reimplement the factory-data conversion. Raw BWC2 and AID44 audio tuning
remain in the archive for future extraction tools.
"""
import hashlib
import json
import re
import struct

from ..core import FWFile
from ..multitouch import MultitouchFWCollection

WIFI_ALIASES = {
    "mediatek/W7932_2.bin": "IZUBA_W7932_2.bin",
    "mediatek/WIFI_MT7932_patch_mcu_1_2_hdr.bin": "IZUBA_WIFI_MT7932_patch_mcu_1_2_hdr.bin",
    "mediatek/EEPROM_MT7932_1.bin": "IZUBA_EEPROM_MT7932_1.bin",
    "mediatek/PPR_MT7932.bin": "IZUBA_PPR_MT7932.bin",
}
BLUETOOTH_NAME = "mediatek/mt793b/neo-25G72.bin"
BLUETOOTH_SHA256 = "9e23414afebeb5ed90aca1fe93a8384252861cbdff6406e09ed66961cbd09492"
CAMERA_NAME = "apple/isp_1925_03XX.dat"
CAMERA_SIZE = 0xcba8
CAMERA_MAGIC = 0x19250306


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def checked_file(root, name, digest, maximum):
    # Names here are constants or derived from the validated radio address,
    # never paths supplied by the metadata.
    path = root / name
    require(0 < path.stat().st_size <= maximum, f"Invalid saved j700 firmware size: {name}")
    data = path.read_bytes()
    require(sha256(data) == digest, f"Saved j700 firmware checksum mismatch: {name}")
    return data


def validate_calibration(data, kind, address, factory):
    mac = bytes.fromhex(address)
    magic, maximum = ((b"MT7932C1", 65536) if kind == "calibration"
                      else (b"MT7932P1", 409600))
    require(20 <= len(data) <= maximum and data[:8] == magic and data[8:14] == mac,
            "Saved j700 calibration belongs to another radio or has an invalid header")
    count = struct.unpack_from("<I" if kind == "calibration" else "<H", data,
                               16 if kind == "calibration" else 14)[0]
    require(1 <= count <= 128, "Invalid j700 calibration record count")
    if kind == "precal":
        require(struct.unpack_from("<I", data, 16)[0] == len(data), "Invalid j700 precal length")
    offset = 20
    for _ in range(count):
        header = 8 if kind == "calibration" else 20
        require(offset + header <= len(data), "Truncated j700 calibration record")
        length = struct.unpack_from("<I", data, offset + 4)[0]
        require(0 < length <= 1536 and offset + header + length <= len(data),
                "Invalid j700 calibration record bounds")
        body = data[offset + header:offset + header + length]
        cid, ext = data[offset:offset + 2]
        if kind == "precal":
            require({1: 1080, 2: 604, 3: 16}.get(cid) == length and ext == 0,
                    "Unsupported j700 operating calibration record")
            require(body in factory, "j700 operating calibration does not match factory data")
        else:
            require(data[offset + 2] <= 1 and data[offset + 3] <= 1,
                    "Invalid j700 calibration command flags")
            if cid == 0xd7:
                require(ext == 0 and length == 1, "Unsupported j700 calibration selector")
            elif cid == 0xed:
                require(ext == 0x21 and 4 <= length <= 1028 and body[0] == 3 and
                        struct.unpack_from("<H", body, 2)[0] == length - 4,
                        "Invalid j700 efuse calibration record")
                require(body[4:] in factory, "j700 efuse cache does not match factory data")
            elif cid == 0xd6:
                require(ext == 0 and length > 20 and body[0] <= 3,
                        "Unsupported j700 RF calibration record")
                require(body[20:] in factory, "j700 RF cache does not match factory data")
            else:
                raise ValueError("Unsupported command in j700 calibration cache")
        offset += header + length
    require(offset == len(data), "Unexpected trailing j700 calibration data")


def collect(raw, source, package, open_firmware):
    saved = raw / "neo-board-data"
    metadata = json.loads((saved / "metadata.json").read_text())
    require(metadata.get("version") == 1 and metadata.get("board") == "j700" and
            metadata.get("calibration_generated_locally") is True,
            "Invalid saved j700 firmware metadata")
    address = metadata.get("wifi_address", "")
    require(isinstance(address, str) and re.fullmatch(r"[0-9a-f]{12}", address) is not None,
            "Invalid j700 radio address")
    require(address not in ("000000000000", "ffffffffffff") and int(address[:2], 16) & 1 == 0,
            "Invalid j700 radio address")
    records = list((saved / "factory").iterdir())
    require(len(records) == 1 and records[0].name.startswith("BWC2-"),
            "Missing or ambiguous saved j700 factory calibration")
    factory = checked_file(saved / "factory", records[0].name,
                           metadata["factory_sha256"], 1_048_576)
    require(len(factory) >= 100, "Invalid saved j700 factory calibration size")
    expected = metadata.get("calibration", [])
    names = [f"mediatek/mt7932/{kind}-{address}.bin" for kind in ("calibration", "precal")]
    require(isinstance(expected, list) and len(expected) == 2 and
            all(isinstance(item, dict) for item in expected) and
            {item.get("name") for item in expected} == set(names),
            "Missing or duplicate saved j700 calibration files")
    digests = {item["name"]: item["sha256"] for item in expected}
    files = []
    for name, source_name in sorted(WIFI_ALIASES.items()):
        data = (raw / "neo-wifi" / source_name).read_bytes()
        require(bool(data), f"Empty j700 Wi-Fi firmware: {source_name}")
        files.append((name, FWFile(name, data)))
    for kind, name in zip(("calibration", "precal"), names):
        data = checked_file(saved, name, digests[name], 409600)
        validate_calibration(data, kind, address, factory)
        files.append((name, FWFile(name, data)))
    bluetooth = checked_file(saved, BLUETOOTH_NAME, metadata["bluetooth_sha256"], 4_194_304)
    require(sha256(bluetooth) == BLUETOOTH_SHA256, "Unqualified saved j700 Bluetooth payload")
    files.append((BLUETOOTH_NAME, FWFile(BLUETOOTH_NAME, bluetooth)))
    camera = checked_file(saved, CAMERA_NAME, metadata["camera_sha256"], CAMERA_SIZE)
    require(len(camera) == CAMERA_SIZE and struct.unpack_from(">I", camera)[0] == CAMERA_MAGIC,
            "Invalid saved j700 camera setfile")
    files.append((CAMERA_NAME, FWFile(CAMERA_NAME, camera)))
    multitouch = sorted(MultitouchFWCollection(str(raw / "fud_firmware")).files())
    require(any(name == "apple/tpmtfw-j700.bin" for name, _ in multitouch),
            "Missing trackpad firmware for j700")
    files.extend(multitouch)
    # j700 has no ASMedia controller or bundled open firmware. In particular,
    # do not apply the j773g kernelcache collector to this board.
    package.add_files(files)
