# SPDX-License-Identifier: MIT
import json
import pathlib
import subprocess
import tempfile

from .core import FWPackage
from .profiles import available_profiles, collect


def update_firmware(source, dest, machine=None, open_firmware=None):
    raw_fw = source.joinpath("all_firmware.tar.gz")
    if not raw_fw.exists():
        raise FileNotFoundError(f"Could not find {raw_fw}")

    with tempfile.TemporaryDirectory() as tmpdir:
        raw = pathlib.Path(tmpdir)
        subprocess.run(["tar", "xf", str(raw_fw.resolve())], cwd=raw, check=True)
        metadata_path = raw / "board-profile.json"
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text())
            if metadata.get("version") != 1:
                raise ValueError("Unsupported raw firmware metadata version")
            archived_machine = metadata.get("boardProfileID")
            if machine is not None and machine != archived_machine:
                raise ValueError("Requested machine does not match firmware archive")
            machine = archived_machine
        # Historical archives have no board-profile.json and were j773g-only.
        if machine is None:
            machine = "j773g"
        if machine not in available_profiles():
            raise ValueError(f"Unknown firmware machine profile: {machine}")
        dest.mkdir(parents=True, exist_ok=True)
        with FWPackage(dest) as package:
            collect(machine, raw, source, package, open_firmware)


def main():
    import argparse
    import logging
    logging.basicConfig()
    parser = argparse.ArgumentParser(description='Update vendor firmware tarball')
    parser.add_argument('source', metavar='SOURCE', type=pathlib.Path,
                        help='path containing raw firmware')
    parser.add_argument('dest', metavar='DEST', type=pathlib.Path,
                        help='output path for vendor firmware')
    parser.add_argument('--machine', choices=available_profiles(), required=True,
                        help='machine product number')
    parser.add_argument('--open-firmware', type=pathlib.Path,
                        help='root containing open firmware to add')
    args = parser.parse_args()
    update_firmware(args.source, args.dest, machine=args.machine,
                    open_firmware=args.open_firmware)


if __name__ == "__main__":
    main()
