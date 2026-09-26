"""CAVR disposable-sandbox runner.

Executed as a *separate* interpreter process inside a disposable working
directory.  It installs a CPython audit hook *before* importing or executing
any untrusted package code, so every observable file, process and socket
operation performed through the interpreter is appended as one JSON record
per line to the trace file.

This is a prototype observation backend: it sees CPython-level activity only
(no native-code or raw syscall visibility).  That limitation is reported as
residual uncertainty in every evidence document.
"""

from __future__ import annotations

import json
import os
import runpy
import sys
import traceback


def _run_kind(mode, flags) -> tuple[bool, bool]:
    """Derive (read, write) from an ``open`` audit event's mode/flags."""
    read = write = False
    if mode is not None:
        text = str(mode)
        if "r" in text or "+" in text:
            read = True
        if any(flag in text for flag in ("w", "a", "x", "+")):
            write = True
    if not read and not write:
        access = flags & getattr(os, "O_ACCMODE", 3)
        if access == getattr(os, "O_WRONLY", 1):
            write = True
        elif access == getattr(os, "O_RDWR", 2):
            read = write = True
        else:
            read = True
    return read, write


def _address_text(value) -> str:
    if isinstance(value, (tuple, list)) and value:
        host = value[0]
        port = value[1] if len(value) > 1 else ""
        return f"{host}:{port}" if port != "" else str(host)
    return str(value)


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(
            "usage: _runner.py <package-src-dir> <module> <trace-path> <workdir>",
            file=sys.stderr,
        )
        return 64
    pkgsrc, module, trace_path, workdir = argv
    pkgsrc = os.path.abspath(pkgsrc)
    workdir = os.path.abspath(workdir)
    trace_path = os.path.abspath(trace_path)
    runner_file = os.path.abspath(__file__)

    ignore_prefixes = []
    for prefix in (sys.base_prefix, sys.prefix, sys.base_exec_prefix, sys.exec_prefix):
        if prefix:
            normalized = os.path.abspath(prefix).replace("\\", "/").rstrip("/") + "/"
            if normalized not in ignore_prefixes:
                ignore_prefixes.append(normalized)
    ignore_exact = {runner_file.replace("\\", "/"), trace_path.replace("\\", "/")}

    def normalize(path):
        try:
            text = os.fspath(path)
        except TypeError:
            return None
        if isinstance(text, bytes):
            text = text.decode("utf-8", "replace")
        if not os.path.isabs(text):
            text = os.path.abspath(text)
        return text

    def ignored(path: str) -> bool:
        slashed = path.replace("\\", "/")
        if slashed in ignore_exact:
            return True
        return any(slashed.startswith(prefix) for prefix in ignore_prefixes)

    handle = open(trace_path, "w", encoding="utf-8")

    def emit(record: dict) -> None:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
        handle.flush()

    def hook(name: str, args: tuple) -> None:
        try:
            if name == "open":
                path = normalize(args[0])
                if path is None or ignored(path):
                    return
                mode = args[1] if len(args) > 1 else None
                flags = args[2] if len(args) > 2 else 0
                read, write = _run_kind(mode, flags)
                if read:
                    emit({"kind": "FILE_READ", "path": path, "via": str(mode or "flags")})
                if write:
                    emit({"kind": "FILE_WRITE", "path": path, "via": str(mode or "flags")})
            elif name == "open_code":
                path = normalize(args[0])
                if path is None or ignored(path):
                    return
                emit({"kind": "FILE_READ", "path": path, "via": "open_code"})
            elif name in ("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn"):
                target = args[0] if args else None
                if isinstance(target, (list, tuple)):
                    target = target[0] if target else None
                emit({"kind": "PROCESS_CREATE", "target": str(target), "via": name})
            elif name in ("socket.connect", "socket.sendto"):
                address = args[1] if len(args) > 1 else None
                emit({"kind": "NETWORK_CONNECT", "target": _address_text(address), "via": name})
            elif name == "socket.getaddrinfo":
                host = args[0] if args else None
                port = args[1] if len(args) > 1 else ""
                emit(
                    {
                        "kind": "NETWORK_CONNECT",
                        "target": f"{host}:{port}" if port != "" else str(host),
                        "via": name,
                    }
                )
        except Exception:
            # An audit hook must never break the observed process.
            return

    sys.addaudithook(hook)
    sys.path.insert(0, pkgsrc)
    os.chdir(workdir)
    emit({"kind": "RUN_START", "module": module, "workdir": workdir})

    exit_code = 0
    try:
        runpy.run_module(module, run_name="__main__", alter_sys=True)
    except SystemExit as exc:
        code = exc.code
        if code is None:
            exit_code = 0
        elif isinstance(code, int):
            exit_code = code
        else:
            print(code, file=sys.stderr)
            exit_code = 1
    except BaseException:
        traceback.print_exc()
        emit({"kind": "PYTHON_EXCEPTION", "exception": repr(sys.exc_info()[1])})
        exit_code = 2
    finally:
        handle.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
