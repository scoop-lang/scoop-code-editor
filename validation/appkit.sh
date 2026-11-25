#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
probe_dir=$(mktemp -d)
trap 'rm -rf "$probe_dir"' EXIT
clang -Wall -Wextra -Werror -fobjc-arc -dynamiclib -framework AppKit validation/appkit.m -o "$probe_dir/editor-probe.dylib"
export SCOOP_EDITOR_APPKIT_PROBE="$probe_dir/editor-probe.dylib"
case "${1:-test}" in
    test)
        scoop test . --release
        scoop test . --release --ignored --filter nativeClientSeesLocalText
        ;;
    benchmark)
        for shape in lines line; do
            SCOOP_EDITOR_BENCH_SHAPE="$shape" scoop test . --release --ignored --filter measureNativeEditorWorkload --nocapture
        done
        ;;
    *) echo 'Usage: validation/appkit.sh [test|benchmark]' >&2; exit 2 ;;
esac
