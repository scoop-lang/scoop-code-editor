"""Verify the native editor through independent GTK/AT-SPI or TSF/UI Automation clients."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INITIAL = "首\r\nA🙂B\r\n尾"
COMMITTED = "首\r\nA🙂中B\r\n尾"


def compiled_case(listing, case_name):
    if listing:
        output = listing.read_text(encoding="utf-8-sig")
    else:
        tool = "sco" if sys.platform == "win32" else "scoop"
        output = subprocess.check_output(
            [tool, "test", ".", "--release", "--message-format=json", "--list"],
            cwd=ROOT,
            encoding="utf-8",
            stderr=subprocess.STDOUT,
        )
    for line in output.splitlines():
        if not line.startswith("{"):
            continue
        report = json.loads(line)
        if report.get("kind") != "executable":
            continue
        cases = [
            c
            for group in report["test_directory"]["containers"]
            for c in group["cases"]
        ]
        for index, case in enumerate(cases):
            if case["name"] == case_name:
                return Path(report["output"]).resolve(), index
    raise ValueError(f"Compiled test directory is missing {case_name}")


def wait_for(check, name, child):
    deadline = time.monotonic() + 18
    while time.monotonic() < deadline:
        value = check()
        if value:
            return value
        if child.poll() is not None:
            raise RuntimeError(f"Editor exited before {name}")
        time.sleep(0.05)
    raise TimeoutError(f"Timed out waiting for {name}")


def linux_client(directory, child):
    import gi

    gi.require_version("Atspi", "2.0")
    from gi.repository import Atspi, GLib

    desktop = Atspi.get_desktop(0)

    def editor_text():
        stack = [
            desktop.get_child_at_index(i) for i in range(desktop.get_child_count())
        ]
        while stack:
            node = stack.pop()
            if node is None:
                continue
            try:
                if (
                    "Text" in node.get_interfaces()
                    and Atspi.Text.get_text(node, 0, -1) == INITIAL
                ):
                    return node
                stack.extend(
                    node.get_child_at_index(i) for i in range(node.get_child_count())
                )
            except GLib.Error:
                continue
        return None

    def marker(name):
        wait_for((directory / name).exists, name, child)

    marker("ready")
    node = wait_for(editor_text, "full AT-SPI document", child)
    window = subprocess.check_output(
        ["xdotool", "search", "--name", "^Scoop editor native protocol$"], text=True
    ).splitlines()[-1]
    subprocess.run(["xdotool", "windowfocus", "--sync", window], check=True, timeout=8)
    (directory / "start").touch()
    subprocess.run(["xdotool", "key", "ctrl+shift+u"], check=True)
    subprocess.run(["xdotool", "type", "--delay", "45", "4e2d"], check=True)
    marker("preedit")
    subprocess.run(["xdotool", "key", "Return"], check=True)
    marker("committed")
    wait_for(
        lambda: Atspi.Text.get_text(node, 0, -1) == COMMITTED,
        "committed AT-SPI document",
        child,
    )
    if not Atspi.Text.add_selection(node, 3, 5):
        raise ValueError("AT-SPI rejected the A🙂 selection")
    marker("selection")
    if not Atspi.EditableText.set_text_contents(node, "accessible replacement"):
        raise ValueError("AT-SPI rejected the replacement")


def windows_probe(directory):
    dll = directory / "editor-tsf.dll"
    subprocess.run(
        [
            "cl",
            "/nologo",
            "/LD",
            "/EHsc",
            "/std:c++17",
            str(ROOT / "validation/windows_tsf.cpp"),
            f"/Fe{dll}",
            "/link",
            "ole32.lib",
            "uuid.lib",
            "user32.lib",
        ],
        cwd=directory,
        check=True,
    )
    if not dll.is_file():
        raise FileNotFoundError(dll)
    return dll


def run(listing):
    linux = sys.platform.startswith("linux")
    case = (
        "gtkCompositionAndAtspiValueSelectionAndEditing"
        if linux
        else "tsfCompositionAndUiaValueSelectionAndEditing"
    )
    binary, index = compiled_case(listing, case)
    with tempfile.TemporaryDirectory(prefix="scoop-editor-native-") as temp:
        directory = Path(temp)
        result = directory / "result"
        result.touch()
        env = dict(
            os.environ,
            SCOOP_TEST_CASE_RESULT=str(result),
            SCOOP_EDITOR_PROTOCOL_DIR=temp,
        )
        if not linux:
            env["SCOOP_EDITOR_TSF_PROBE"] = str(windows_probe(directory))
        with (directory / "editor.log").open("w+", encoding="utf-8") as log:
            child = subprocess.Popen(
                [str(binary), "--scoop-test-child", str(index)],
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            try:
                if linux:
                    linux_client(directory, child)
                else:
                    subprocess.run(
                        [
                            "powershell.exe",
                            "-NoProfile",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-File",
                            str(ROOT / "validation/windows_uia.ps1"),
                            str(child.pid),
                            temp,
                        ],
                        check=True,
                        timeout=85,
                    )
                if child.wait(timeout=12) or not (directory / "verified").exists():
                    raise ValueError(
                        "Editor did not confirm the accessibility replacement"
                    )
                if not result.read_text(encoding="utf-8").startswith(
                    f"{index} passed "
                ):
                    raise ValueError("Missing native protocol test result")
            finally:
                if child.poll() is None:
                    child.terminate()
                    child.wait(timeout=8)
                log.seek(0)
                print(log.read(), end="")
                print(result.read_text(encoding="utf-8"), end="")
        print(f"{case} passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--listing", type=Path, help="test directory JSON from scoop test --list"
    )
    parser.add_argument("--linux-session", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if sys.platform.startswith("linux") and not args.linux_session:
        # XTest keyboard events are confined to this private display and accessibility bus.
        interpreter = (
            "/usr/bin/python3" if Path("/usr/bin/python3").exists() else sys.executable
        )
        command = [
            "dbus-run-session",
            "--",
            "xvfb-run",
            "-a",
            interpreter,
            __file__,
            "--linux-session",
        ]
        if args.listing:
            command.extend(["--listing", str(args.listing.resolve())])
        return subprocess.call(
            command,
            env=dict(
                os.environ, GDK_BACKEND="x11", GTK_A11Y="atspi", GTK_IM_MODULE="simple"
            ),
        )
    if args.linux_session:
        with subprocess.Popen(
            ["openbox"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ) as wm:
            try:
                run(args.listing)
            finally:
                wm.terminate()
    elif sys.platform == "win32":
        run(args.listing)
    else:
        parser.error("Use validation/appkit.sh on macOS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
