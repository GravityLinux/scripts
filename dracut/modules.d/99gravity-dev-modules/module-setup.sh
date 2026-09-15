#!/bin/sh
# SPDX-License-Identifier: MIT

# called by dracut
check() {
    if [ -n "$hostonly" ] && [ ! -e /proc/device-tree/chosen/gravity,efi-system-partition ]; then
       return 1
    elif [ -z "$hostonly" ]; then
        return 0
    else
       return 0
    fi
}

# called by dracut
depends() {
    echo fs-lib
    return 0
}

# called by dracut
install() {
    inst_multiple cp ln mkdir mount
    inst_hook pre-udev 99 "${moddir}/link-gravity-dev-modules.sh"
    inst_hook pre-pivot 99 "${moddir}/install-gravity-dev-modules.sh"
}
