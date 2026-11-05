"""本地 HTTP 服务：静态页面 + JSON API。"""

from __future__ import annotations

import io
import json
import mimetypes
import re
import sys
import tempfile
import threading
import traceback
import zipfile
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import __version__, llm, parser
from .config import load_config, public_config, save_config
from .event_utils import normalize_event, parse_datetime
from .store import Store

MAX_BODY = 2 * 1024 * 1024


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def create_server(
    base_dir: Path,
    host: str = "127.0.0.1",
    port: int = 8765,
    static_dir: Path | None = None,
    data_dir: Path | None = None,
) -> ThreadingHTTPServer:
    base_dir = Path(base_dir)
    static_dir = Path(static_dir).resolve() if static_dir else (base_dir / "static").resolve()
    data_dir = Path(data_dir) if data_dir else base_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    store = Store(data_dir / "calendar.db")
    config_path = data_dir / "config.json"

    class Handler(BaseHTTPRequestHandler):
        server_version = "LocalCalendar/1.0"

        # ---------- 基础响应 ----------
        def _send_json(self, value: object, status: int = 200) -> None:
            body = _json_bytes(value)
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _error(self, status: int, message: str) -> None:
            self._send_json({"error": message}, status)

        def _send_bytes(
            self, body: bytes, content_type: str, filename: str | None = None
        ) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args) -> None:
            if sys.stdout is not None:
                print(f"[{self.log_date_time_string()}] {fmt % args}")

        def _log_exception(self) -> None:
            detail = traceback.format_exc()
            try:
                with (data_dir / "error.log").open("a", encoding="utf-8") as handle:
                    handle.write(f"\n[{datetime.now().isoformat(timespec='seconds')}]\n{detail}\n")
            except OSError:
                pass
            if sys.stdout is not None:
                print(detail)

        # ---------- 安全 ----------
        def _guard(self) -> bool:
            host_header = self.headers.get("Host") or ""
            host = host_header.rsplit(":", 1)[0].strip("[]").lower()
            if host not in ("127.0.0.1", "localhost", "::1"):
                self._error(403, "只允许从本机访问")
                return False
            origin = self.headers.get("Origin")
            if origin:
                actual_port = self.server.server_address[1]
                allowed = {
                    f"http://127.0.0.1:{actual_port}",
                    f"http://localhost:{actual_port}",
                    f"http://[::1]:{actual_port}",
                }
                if origin.rstrip("/") not in allowed:
                    self._error(403, "拒绝跨站请求")
                    return False
            return True

        def _json_body(self, required: bool = True) -> dict:
            content_type = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if content_type != "application/json":
                if required:
                    raise ApiError(415, "请求必须使用 application/json")
                return {}
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                raise ApiError(413, "请求内容过大")
            if length <= 0:
                if required:
                    raise ApiError(400, "请求内容为空")
                return {}
            raw = self.rfile.read(length)
            try:
                value = json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                raise ApiError(400, "JSON 格式无效") from None
            if not isinstance(value, dict):
                raise ApiError(400, "请求内容必须是 JSON 对象")
            return value

        # ---------- 路由 ----------
        def do_GET(self) -> None:
            self._dispatch("GET")

        def do_POST(self) -> None:
            self._dispatch("POST")

        def do_PUT(self) -> None:
            self._dispatch("PUT")

        def do_PATCH(self) -> None:
            self._dispatch("PATCH")

        def do_DELETE(self) -> None:
            self._dispatch("DELETE")

        def _dispatch(self, method: str) -> None:
            try:
                if not self._guard():
                    return
                parsed = urlparse(self.path)
                path = parsed.path
                if path.startswith("/api/"):
                    self._handle_api(method, path, parse_qs(parsed.query))
                elif method == "GET":
                    self._serve_static(path)
                else:
                    self._error(405, "不支持的请求方法")
            except ApiError as exc:
                self._error(exc.status, exc.message)
            except Exception as exc:  # pragma: no cover - 兜底
                self._log_exception()
                self._error(500, f"服务器内部错误：{exc}")

        def _handle_api(self, method: str, path: str, query: dict) -> None:
            if method == "GET" and path == "/api/health":
                self._send_json({"ok": True, "app": "local-calendar", "version": "1.0.0"})
                return

            if method == "POST" and path == "/api/shutdown":
                self._json_body()
                self._send_json({"ok": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return

            if method == "GET" and path == "/api/backup":
                self._send_backup()
                return

            if method == "GET" and path == "/api/config":
                self._send_json(public_config(load_config(config_path)))
                return

            if method == "PUT" and path == "/api/config":
                body = self._json_body()
                try:
                    config = save_config(config_path, body)
                except ValueError as exc:
                    raise ApiError(400, str(exc)) from None
                self._send_json(public_config(config))
                return

            if method == "POST" and path == "/api/config/test":
                body = self._json_body(required=False)
                stored = load_config(config_path)
                config = {
                    "base_url": str(body.get("base_url") or stored["base_url"]).strip(),
                    "model": str(body.get("model") or stored["model"]).strip(),
                    "api_key": str(body.get("api_key") or stored["api_key"]).strip(),
                }
                try:
                    models = llm.test_connection(config)
                except llm.LLMError as exc:
                    raise ApiError(502, str(exc)) from None
                self._send_json({"ok": True, "models": models[:12], "count": len(models)})
                return

            if method == "GET" and path == "/api/events":
                start = (query.get("start") or [None])[0]
                end = (query.get("end") or [None])[0]
                try:
                    if start:
                        parse_datetime(start, "start")
                    if end:
                        parse_datetime(end, "end")
                except ValueError as exc:
                    raise ApiError(400, str(exc)) from None
                self._send_json({"events": store.list_events(start, end)})
                return

            if method == "POST" and path == "/api/parse":
                body = self._json_body()
                text = str(body.get("text") or "").strip()
                if not text:
                    raise ApiError(400, "请输入要解析的内容")
                if len(text) > 2000:
                    raise ApiError(400, "输入内容不能超过 2000 字")
                self._send_json(self._parse_text(text))
                return

            if method == "POST" and path == "/api/events":
                event = self._normalize_body(self._json_body())
                self._send_json({"event": store.create_event(event)}, 201)
                return

            if method == "POST" and path == "/api/events/bulk":
                body = self._json_body()
                items = body.get("events")
                if not isinstance(items, list) or not items:
                    raise ApiError(400, "events 必须是非空数组")
                if len(items) > 50:
                    raise ApiError(400, "一次最多添加 50 条日程")
                events = []
                for index, item in enumerate(items):
                    try:
                        events.append(normalize_event(item))
                    except ValueError as exc:
                        raise ApiError(400, f"第 {index + 1} 条：{exc}") from None
                self._send_json({"events": store.create_events(events)}, 201)
                return

            match = re.fullmatch(r"/api/events/(\d+)", path)
            if match:
                event_id = int(match.group(1))
                if method in ("PATCH", "PUT"):
                    if store.get_event(event_id) is None:
                        raise ApiError(404, "日程不存在")
                    event = self._normalize_body(self._json_body())
                    self._send_json({"event": store.update_event(event_id, event)})
                    return
                if method == "DELETE":
                    if not store.delete_event(event_id):
                        raise ApiError(404, "日程不存在")
                    self._send_json({"ok": True})
                    return

            raise ApiError(404, "接口不存在")

        # ---------- 业务 ----------
        def _normalize_body(self, body: dict) -> dict:
            try:
                return normalize_event(body)
            except ValueError as exc:
                raise ApiError(400, str(exc)) from None

        def _parse_text(self, text: str) -> dict:
            now = datetime.now()
            config = load_config(config_path)
            source = "local"
            warning = ""
            raw_events: list[dict] = []

            if config.get("api_key"):
                try:
                    raw_events = llm.parse_text(text, config, now)
                    source = "model"
                except llm.LLMError as exc:
                    raw_events = parser.parse(text, now)
                    warning = f"模型调用失败，已改用本地解析：{exc}"
            else:
                raw_events = parser.parse(text, now)
                warning = "未配置 API Key，当前使用本地规则解析"

            events: list[dict] = []
            invalid: list[str] = []
            for item in raw_events:
                try:
                    events.append(normalize_event(item))
                except ValueError as exc:
                    invalid.append(str(exc))

            # 模型返回了内容但全部无效时，退回本地规则。
            if source == "model" and raw_events and not events:
                fallback = []
                for item in parser.parse(text, now):
                    try:
                        fallback.append(normalize_event(item))
                    except ValueError:
                        pass
                if fallback:
                    events = fallback
                    source = "local"
                    warning = "模型返回的结果无法解析，已改用本地规则"
            elif invalid:
                warning = (warning + "；" if warning else "") + "；".join(invalid)

            return {
                "events": events,
                "source": source,
                "warning": warning,
                "model": config.get("model") if source == "model" else None,
            }

        def _send_backup(self) -> None:
            now = datetime.now()
            events = store.list_events()
            exported_at = now.isoformat(timespec="seconds")
            filename = f"calendar-backup-{now.strftime('%Y%m%d-%H%M%S')}.zip"
            manifest = {
                "app": "local-calendar",
                "version": __version__,
                "exported_at": exported_at,
                "event_count": len(events),
                "files": ["calendar.db", "events.json", "manifest.json", "README.txt"],
            }
            readme = (
                "本地日历备份 / Local Calendar backup\n"
                "====================================\n\n"
                f"导出时间 / Exported: {exported_at}\n"
                f"日程数量 / Events: {len(events)}\n\n"
                "包含文件 / Files:\n"
                "- calendar.db    SQLite 数据库 / SQLite database\n"
                "- events.json   日程 JSON / events JSON\n"
                "- manifest.json 备份信息 / metadata\n\n"
                "恢复方法 / Restore:\n"
                "1. 退出本地日历 / Quit Local Calendar\n"
                "2. 备份当前数据库 / Back up the current database\n"
                "3. 用本压缩包中的 calendar.db 替换 / Replace calendar.db with this one\n"
                "   默认位置 / Default: %LOCALAPPDATA%\\LocalCalendar\\calendar.db\n"
                "4. 重新启动 / Restart the app\n\n"
                "注意：备份不包含 config.json，因此不包含 API Key。\n"
                "Note: config.json and the API key are NOT included.\n"
            )

            buffer = io.BytesIO()
            with tempfile.TemporaryDirectory() as temp_dir:
                database_copy = Path(temp_dir) / "calendar.db"
                store.backup_to(database_copy)
                with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                    archive.write(database_copy, "calendar.db")
                    archive.writestr(
                        "events.json", json.dumps(events, ensure_ascii=False, indent=2)
                    )
                    archive.writestr(
                        "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2)
                    )
                    archive.writestr("README.txt", readme)

            self._send_bytes(buffer.getvalue(), "application/zip", filename)

        # ---------- 静态文件 ----------
        def _serve_static(self, path: str) -> None:
            relative = path.lstrip("/") or "index.html"
            candidate = (static_dir / relative).resolve()
            try:
                candidate.relative_to(static_dir)
            except ValueError:
                self._error(404, "文件不存在")
                return
            if not candidate.is_file():
                self._error(404, "文件不存在")
                return

            content_type = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
            if candidate.suffix == ".js":
                content_type = "text/javascript; charset=utf-8"
            elif candidate.suffix == ".css":
                content_type = "text/css; charset=utf-8"
            elif candidate.suffix in (".html", ".htm"):
                content_type = "text/html; charset=utf-8"
            elif candidate.suffix == ".svg":
                content_type = "image/svg+xml"

            body = candidate.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    return server
