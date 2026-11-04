"""日程数据的校验与规范化。"""

from __future__ import annotations

from datetime import datetime, timedelta


def parse_datetime(value: object, label: str = "时间") -> datetime:
    """把 ISO 字符串或 datetime 转成本地时间（naive）。"""
    if value is None or value == "":
        raise ValueError(f"{label}不能为空")

    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip().replace("/", "-")
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        text = text.replace(" ", "T", 1)
        if len(text) == 10:
            text += "T09:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            raise ValueError(f"{label}格式无效：{value}") from None

    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt.replace(second=0, microsecond=0)


def normalize_event(raw: dict) -> dict:
    """校验并补全一条日程，返回可直接入库的字段。"""
    if not isinstance(raw, dict):
        raise ValueError("日程格式无效")

    title = str(raw.get("title") or "").strip()
    if not title:
        raise ValueError("标题不能为空")
    title = title[:200]

    start = parse_datetime(raw.get("start"), "开始时间")
    all_day = bool(raw.get("all_day"))
    end_raw = raw.get("end")

    if all_day:
        start = start.replace(hour=0, minute=0)
        if end_raw:
            end = parse_datetime(end_raw, "结束时间").replace(hour=0, minute=0)
            if end <= start:
                end = start + timedelta(days=1)
        else:
            end = start + timedelta(days=1)
    else:
        end = parse_datetime(end_raw, "结束时间") if end_raw else start + timedelta(hours=1)
        if end <= start:
            end = start + timedelta(hours=1)

    return {
        "title": title,
        "start": start.isoformat(timespec="minutes"),
        "end": end.isoformat(timespec="minutes"),
        "all_day": all_day,
        "location": str(raw.get("location") or "").strip()[:200],
        "notes": str(raw.get("notes") or "").strip()[:2000],
    }


def row_to_event(row) -> dict:
    """SQLite Row -> 前端 JSON。"""
    return {
        "id": row["id"],
        "title": row["title"],
        "start": row["start_at"],
        "end": row["end_at"],
        "all_day": bool(row["all_day"]),
        "location": row["location"],
        "notes": row["notes"],
    }
