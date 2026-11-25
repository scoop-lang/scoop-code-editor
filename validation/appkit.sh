#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
probe_dir=$(mktemp -d)
trap 'rm -rf "$probe_dir"' EXIT
clang -Wall -Wextra -Werror -fobjc-arc -dynamiclib -framework AppKit validation/appkit.m -o "$probe_dir/editor-probe.dylib"
SCOOP_EDITOR_APPKIT_PROBE="$probe_dir/editor-probe.dylib" scoop test . --release
