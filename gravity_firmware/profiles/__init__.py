# SPDX-License-Identifier: MIT
"""Add a product-number module exporting collect(raw, source, pkg, open_firmware)."""
import importlib
import pkgutil
import re


def available_profiles():
    return tuple(sorted(module.name for module in pkgutil.iter_modules(__path__)
                        if re.fullmatch(r"j[0-9]+[a-z]*", module.name)))


def collect(machine, raw, source, package, open_firmware):
    if machine not in available_profiles():
        raise ValueError(f"Unknown firmware machine profile: {machine}")
    module = importlib.import_module(f"{__name__}.{machine}")
    module.collect(raw, source, package, open_firmware)
