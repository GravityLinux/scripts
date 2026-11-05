# SPDX-License-Identifier: MIT
from ..wifi import WiFiFWCollection
from ..bluetooth import BluetoothFWCollection
from ..radio_calibration import BluetoothCalibration, WiFiCalibration
from ..multitouch import MultitouchFWCollection
from ..kernel import KernelFWCollection
from ..open_firmware import OpenFirmwareCollection


def collect(raw, source, package, open_firmware):
    wifi = next((path for path in (raw / "apple_bcmwlan_firmware",
                                   raw / "firmware/wifi") if path.is_dir()), None)
    if wifi is None:
        raise FileNotFoundError("Could not find raw Wi-Fi firmware")
    package.add_files(sorted(WiFiFWCollection(str(wifi), machine="j773g").files()))
    package.add_files(sorted(BluetoothFWCollection(
        str(raw / "firmware/bluetooth"), machine="j773g").files()))
    for kind in (BluetoothCalibration, WiFiCalibration):
        calibration = kind.from_archive(raw)
        if calibration is not None:
            package.add_files(calibration.files())
    package.add_files(sorted(MultitouchFWCollection(str(raw / "fud_firmware")).files()))
    package.add_files(sorted(KernelFWCollection(str(source)).files()))
    package.add_files(sorted(OpenFirmwareCollection(
        machine="j773g", source_path=open_firmware).files()))
