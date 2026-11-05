# SPDX-License-Identifier: MIT
from setuptools import find_packages, setup

setup(
    name="gravity_firmware",
    version="0.1",
    description="Gravity Linux firmware extraction tools",
    author="The Gravity Linux and Asahi Linux contributors",
    url="https://github.com/GravityLinux/scripts",
    license="MIT",
    python_requires=">=3.9",
    packages=find_packages(include=["gravity_firmware", "gravity_firmware.*"]),
    entry_points={"console_scripts": ["gravity-fwextract = gravity_firmware.update:main"]},
)
