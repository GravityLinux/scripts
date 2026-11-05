#!/bin/sh
set -eu

base=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
test_dir=$(mktemp -d "${TMPDIR:-/tmp}/gravity-fwupdate.XXXXXX")
trap 'rm -rf "$test_dir"' EXIT HUP INT TERM

mkdir -p "$test_dir/gravity" "$test_dir/vendorfw"
: > "$test_dir/gravity/all_firmware.tar.gz"
: > "$test_dir/vendorfw/old-firmware"

GRAVITYFW="$test_dir/gravity" \
VENDORFW="$test_dir/vendorfw" \
VENDORFWTMP="$test_dir/vendorfw-tmp" \
FWEXTRACT="$base/tests/fake-fwextract" \
GRAVITY_MACHINE=j773g \
TEST_LOG="$test_dir/arguments" \
    sh "$base/gravity-fwupdate"

test -f "$test_dir/vendorfw/firmware.cpio"
test ! -e "$test_dir/vendorfw/old-firmware"
test ! -e "$test_dir/vendorfw-tmp"
test ! -e "$test_dir/vendorfw.new"
grep -qx -- '--machine' "$test_dir/arguments"
grep -qx -- 'j773g' "$test_dir/arguments"

mkdir -p "$test_dir/vendorfw"
: > "$test_dir/vendorfw/known-good"
if GRAVITYFW="$test_dir/gravity" \
   VENDORFW="$test_dir/vendorfw" \
   VENDORFWTMP="$test_dir/vendorfw-tmp" \
   FWEXTRACT="$base/tests/fake-fwextract" \
   GRAVITY_MACHINE=j773g \
   TEST_FAIL=1 \
   TEST_LOG="$test_dir/failed-arguments" \
       sh "$base/gravity-fwupdate"; then
    echo "gravity-fwupdate unexpectedly accepted a failed extraction" >&2
    exit 1
fi
test -f "$test_dir/vendorfw/known-good"
test ! -e "$test_dir/vendorfw-tmp"
test ! -e "$test_dir/vendorfw.new"

echo "gravity-fwupdate test passed"

GRAVITYFW="$test_dir/gravity" \
VENDORFW="$test_dir/vendorfw" \
VENDORFWTMP="$test_dir/vendorfw-tmp" \
FWEXTRACT="$base/tests/fake-fwextract" \
GRAVITY_MACHINE=j700 \
TEST_MACHINE=j700 \
TEST_LOG="$test_dir/neo-arguments" \
    sh "$base/gravity-fwupdate"
grep -qx -- 'j700' "$test_dir/neo-arguments"

. "$base/functions.sh"
for product in j700 j773g j616c; do
    printf 'apple,%s\0apple,t8140\0apple,arm-platform\0' "$product" > "$test_dir/compatible"
    test "$(get_firmware_machine "$test_dir/compatible")" = "$product"
done
printf 'apple,t8140\0apple,arm-platform\0' > "$test_dir/compatible"
if get_firmware_machine "$test_dir/compatible"; then
    echo 'Accepted a missing product number' >&2; exit 1
fi
printf 'apple,j700\0apple,j773g\0' > "$test_dir/compatible"
if get_firmware_machine "$test_dir/compatible"; then
    echo 'Accepted ambiguous product numbers' >&2; exit 1
fi
echo 'j700 firmware update and board detection tests passed'
