#!/usr/bin/env python3
"""本地日历启动入口。"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
import urllib.request
import webbrowser
from pathlib import Path

from calendar_app.paths import resolve_data_dir
from calendar_app.server import create_server


def paths() -> tuple[Path, Path]:
    """返回 (系统数据目录, 静态资源目录)。"""
    if getattr(sys, "frozen", False):
        app_root = Path(sys.executable).resolve().parent
        resource_dir = Path(getattr(sys, "_MEIPASS", app_root))
    else:
        app_root = Path(__file__).resolve().parent
        resource_dir = app_root

    legacy_dir = app_root / "data"
    try:
        data_dir, migrated = resolve_data_dir(legacy_dir)
    except OSError:
        # 系统目录不可写时退回应用目录，保证应用仍能启动。
        data_dir = legacy_dir
        data_dir.mkdir(parents=True, exist_ok=True)
        migrated = []

    if migrated:
        log(f"已将本地数据迁移到：{data_dir}（{', '.join(migrated)}）")
    return data_dir, resource_dir / "static"


def log(message: str) -> None:
    """无控制台窗口时 stdout 为 None，需要安全地忽略。"""
    if sys.stdout is None:
        return
    try:
        print(message)
    except (OSError, ValueError):
        pass


def show_error(message: str) -> None:
    try:
        data_dir, _ = paths()
        data_dir.mkdir(parents=True, exist_ok=True)
        with (data_dir / "error.log").open("a", encoding="utf-8") as handle:
            handle.write(f"{message}\n")
    except OSError:
        pass

    log(message)
    if sys.stdout is None and sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(None, message, "本地日历", 0x10)
        except Exception:
            pass


def find_running(host: str, start: int, count: int = 20) -> int | None:
    """查找已经运行的实例，避免重复启动多个服务。"""
    for port in range(start, start + count):
        try:
            with urllib.request.urlopen(f"http://{host}:{port}/api/health", timeout=0.4) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            continue
        if isinstance(payload, dict) and payload.get("app") == "local-calendar":
            return port
    return None


def open_browser(url: str) -> None:
    if os.environ.get("CALENDAR_NO_BROWSER") == "1":
        return
    try:
        webbrowser.open(url)
    except Exception:
        pass


def pick_port(host: str, start: int) -> int:
    for port in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return port
    raise RuntimeError("没有找到可用的本地端口")


def run() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

    data_dir, static_dir = paths()
    host = "127.0.0.1"
    start_port = int(os.environ.get("CALENDAR_PORT", "8765"))

    running_port = find_running(host, start_port)
    if running_port is not None:
        url = f"http://{host}:{running_port}"
        log(f"本地日历已在运行：{url}")
        open_browser(url)
        return

    port = pick_port(host, start_port)
    try:
        server = create_server(data_dir, host, port, static_dir=static_dir, data_dir=data_dir)
    except OSError:
        # 并发启动时另一个实例可能刚好抢占了端口。
        running_port = find_running(host, start_port)
        if running_port is not None:
            url = f"http://{host}:{running_port}"
            log(f"本地日历已在运行：{url}")
            open_browser(url)
            return
        raise

    url = f"http://{host}:{port}"
    log("=" * 58)
    log("  本地日历")
    log(f"  地址：{url}")
    log(f"  数据：{data_dir}")
    log("  退出方式：页面右上角「设置」→「退出应用」")
    log("=" * 58)

    if os.environ.get("CALENDAR_NO_BROWSER") != "1":
        timer = threading.Timer(0.8, lambda: open_browser(url))
        timer.daemon = True
        timer.start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        log("\n已退出。")


def main() -> None:
    try:
        run()
    except Exception as exc:
        show_error(f"本地日历启动失败：{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
