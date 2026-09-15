#!/bin/sh
# SPDX-License-Identifier: MIT

# called by dracut
check() {
    if [ -n "$hostonly" ] &&
       [ ! -e /proc/device-tree/chosen/gravity,efi-system-partition ]; then
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
installkernel() {
    instmods apple-mailbox nvme-apple vfat
}

# called by dracut
install() {
    inst_dir "/lib/firmware"
    ln_r "/vendorfw" "/lib/firmware/vendor"
    gravityscriptsdir="/usr/share/gravity-scripts"
    inst_dir $gravityscriptsdir
    $DRACUT_CP -R -L -t "${initdir}/${gravityscriptsdir}" "${dracutsysrootdir}${gravityscriptsdir}"/*
    inst_multiple cpio cut dirname grep mkdir modprobe mount seq sleep tr umount
    inst_hook pre-udev 10 "${moddir}/load-gravity-firmware.sh"
    inst_hook cleanup 99 "${moddir}/install-gravity-firmware.sh"
}
