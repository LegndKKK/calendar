"""运行数据目录解析与旧数据迁移。

默认把数据库和 API Key 配置放到用户系统盘的应用数据目录，
避免仓库或项目目录中残留个人信息：

    Windows: %LOCALAPPDATA%\\LocalCalendar
    Linux/macOS: ~/.local/share/LocalCalendar

可用环境变量 CALENDAR_DATA_DIR 覆盖。
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

APP_DIR_NAME = "LocalCalendar"
MIGRATABLE_FILES = ("calendar.db", "config.json", "error.log")


def system_data_dir() -> Path:
    override = os.environ.get("CALENDAR_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()

    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_DIR_NAME
        return Path.home() / "AppData" / "Local" / APP_DIR_NAME

    base = os.environ.get("XDG_DATA_HOME", "").strip()
    if base:
        return Path(base).expanduser() / APP_DIR_NAME
    return Path.home() / ".local" / "share" / APP_DIR_NAME


def migrate_legacy_data(legacy_dir: Path | None, target_dir: Path) -> list[str]:
    """把旧项目目录中的运行数据移动到系统数据目录。

    只移动不存在于目标位置的文件，避免覆盖现有数据。
    """
    if legacy_dir is None:
        return []

    legacy = Path(legacy_dir)
    target = Path(target_dir)
    if not legacy.is_dir():
        return []

    try:
        if legacy.resolve() == target.resolve():
            return []
    except OSError:
        pass

    migrated: list[str] = []
    for name in MIGRATABLE_FILES:
        source = legacy / name
        destination = target / name
        if not source.is_file() or destination.exists():
            continue
        try:
            shutil.move(str(source), str(destination))
            migrated.append(name)
        except OSError:
            try:
                shutil.copy2(source, destination)
                migrated.append(name)
            except OSError:
                continue
    return migrated


def resolve_data_dir(legacy_dir: Path | None = None) -> tuple[Path, list[str]]:
    data_dir = system_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    migrated = migrate_legacy_data(legacy_dir, data_dir)
    return data_dir, migrated
