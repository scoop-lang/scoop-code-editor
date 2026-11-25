"""Run the editor's AppKit tests as a foreground application in the current desktop session."""

import json
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def compiled_tests():
    build = subprocess.run(
        ["scoop", "test", ".", "--release", "--message-format=json", "--list"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if build.returncode:
        raise SystemExit(build.stdout)
    for line in build.stdout.splitlines():
        if line.startswith("{"):
            report = json.loads(line)
            if report.get("kind") == "executable":
                cases = [
                    case
                    for container in report["test_directory"]["containers"]
                    for case in container["cases"]
                ]
                return Path(report["output"]), cases
    raise SystemExit("The build did not report a test executable.")


def run_case(bundle, probe, directory, index, case, shape=None):
    record = directory / "result"
    output = directory / "stdout"
    error = directory / "stderr"
    for path in (record, output, error):
        path.write_text("")
    command = [
        "open",
        "-W",
        "-n",
        "-a",
        str(bundle),
        "--stdout",
        str(output),
        "--stderr",
        str(error),
        "--env",
        f"SCOOP_EDITOR_APPKIT_PROBE={probe}",
        "--env",
        f"SCOOP_TEST_CASE_RESULT={record}",
    ]
    if shape:
        command.extend(["--env", f"SCOOP_EDITOR_BENCH_SHAPE={shape}"])
    # LaunchServices can lose the wait registration for a case that exits immediately.
    launch = subprocess.run(
        [*command, "--args", "--scoop-test-child", str(index)],
        check=False,
        capture_output=True,
        text=True,
    )
    result = record.read_text()
    print(output.read_text(), end="")
    print(error.read_text(), end="", file=sys.stderr)
    if not result.startswith(f"{index} passed "):
        raise SystemExit(f"{case['name']} failed\n{result}{launch.stderr}")
    print(f"{case['name']} passed", flush=True)


def main():
    mode, *filters = sys.argv[1:] or ["test"]
    if mode not in {"test", "benchmark"} or (mode == "benchmark" and filters):
        raise SystemExit("Usage: validation/appkit.sh [test [name ...] | benchmark]")
    os.chdir(Path(__file__).resolve().parent.parent)
    binary, cases = compiled_tests()
    selected = []
    for index, case in enumerate(cases):
        if mode == "benchmark":
            if case["name"] == "measureNativeEditorWorkload":
                selected.extend(
                    (index, case, shape)
                    for _ in range(3)
                    for shape in ("lines", "line")
                )
        elif case["ignore_reason"] in (None, "Run validation/appkit.sh on macOS") and (
            not filters or any(term in case["display_name"] for term in filters)
        ):
            selected.append((index, case, None))
    if not selected:
        raise SystemExit("No matching editor tests.")
    with tempfile.TemporaryDirectory(prefix="scoop-editor-appkit-") as temporary:
        directory = Path(temporary)
        bundle = directory / "ScoopEditorValidation.app"
        mac = bundle / "Contents" / "MacOS"
        mac.mkdir(parents=True)
        shutil.copy2(binary, mac / "EditorProbe")
        (mac.parent / "Info.plist").write_bytes(
            plistlib.dumps(
                {
                    "CFBundleExecutable": "EditorProbe",
                    "CFBundleIdentifier": "org.scooplang.editor.validation",
                    "CFBundleName": "Scoop Editor Validation",
                    "CFBundlePackageType": "APPL",
                    "CFBundleVersion": "1",
                    "NSHighResolutionCapable": True,
                }
            )
        )
        probe = directory / "editor-probe.dylib"
        subprocess.run(
            [
                "clang",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-fobjc-arc",
                "-dynamiclib",
                "-framework",
                "AppKit",
                "validation/appkit.m",
                "-o",
                str(probe),
            ],
            check=True,
        )
        for index, case, shape in selected:
            run_case(bundle, probe, directory, index, case, shape)
    print(f"{len(selected)} editor tests passed")


if __name__ == "__main__":
    main()
