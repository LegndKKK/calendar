"""本地规则解析：没有 API Key 时的兜底方案。

支持常见中文表达：
    今天/明天/后天/大后天、本周五/下周一、11月6日、5号、3天后
    上午/下午/晚上 3 点、15:30、9 点半、2 小时后
    地点 xxx、全天/整天、持续 2 小时
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta

_CN = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
_WEEK = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}

_FULLWIDTH = str.maketrans("０１２３４５６７８９：／", "0123456789:/")

_RELATIVE_DAYS = {
    "大后天": 3,
    "后天": 2,
    "明天": 1,
    "明日": 1,
    "今天": 0,
    "今日": 0,
    "今早": 0,
    "今晚": 0,
    "昨天": -1,
    "昨日": -1,
    "前天": -2,
}

_PERIOD_DEFAULT = {
    "凌晨": 6,
    "早上": 9,
    "早晨": 9,
    "上午": 9,
    "中午": 12,
    "下午": 15,
    "傍晚": 18,
    "晚上": 20,
    "夜里": 21,
}

_CN_NUM_CHARS = "一二三四五六七八九十两"


def _cn_number(value: str | None) -> int | None:
    """解析中文数字或阿拉伯数字（0-99）。"""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if value.isdigit():
        return int(value)
    if value in _CN:
        return _CN[value]
    if "十" in value:
        left, _, right = value.partition("十")
        if left and left not in _CN:
            return None
        if right and right not in _CN:
            return None
        tens = _CN[left] if left else 1
        ones = _CN[right] if right else 0
        return tens * 10 + ones
    return None


def _date_from_month_day(now: datetime, month: int, day: int) -> date | None:
    for year in (now.year, now.year + 1):
        try:
            candidate = date(year, month, day)
        except ValueError:
            continue
        if candidate >= now.date() - timedelta(days=1):
            return candidate
    return None


def _date_from_day(now: datetime, day: int) -> date | None:
    for offset in (0, 1):
        year = now.year + (1 if now.month + offset > 12 else 0)
        month = (now.month + offset - 1) % 12 + 1
        try:
            candidate = date(year, month, day)
        except ValueError:
            continue
        if candidate >= now.date():
            return candidate
    return None


def _weekday_date(now: datetime, prefix: str | None, weekday: int) -> date:
    today = now.date()
    monday = today - timedelta(days=today.weekday())
    if prefix == "下下":
        return monday + timedelta(days=14 + weekday)
    if prefix == "下":
        return monday + timedelta(days=7 + weekday)
    if prefix in ("这", "本"):
        candidate = monday + timedelta(days=weekday)
        return candidate if candidate >= today else candidate + timedelta(days=7)
    delta = (weekday - today.weekday()) % 7
    return today + timedelta(days=delta)


def parse(text: str, now: datetime | None = None) -> list[dict]:
    """把一段自然语言解析成一条（或零条）日程。"""
    now = (now or datetime.now()).replace(second=0, microsecond=0)
    original = (text or "").strip()
    if not original:
        return []

    norm = original.translate(_FULLWIDTH).strip()
    spans: list[tuple[int, int]] = []

    def take(match: re.Match | None) -> re.Match | None:
        if match:
            spans.append(match.span())
        return match

    base_date = now.date()
    explicit_date = False
    explicit_today = False
    forced_period: str | None = None

    # ---------- 日期 ----------
    match = take(
        re.search(
            r"(?<!\d)(\d{4})\s*[-/年]\s*(\d{1,2})\s*[-/月]\s*(\d{1,2})\s*[日号]?",
            norm,
        )
    )
    if match:
        try:
            base_date = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            explicit_date = True
        except ValueError:
            spans.pop()

    if not explicit_date:
        match = take(re.search(r"(?<![\d年])(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]?", norm))
        if match:
            candidate = _date_from_month_day(now, int(match.group(1)), int(match.group(2)))
            if candidate:
                base_date = candidate
                explicit_date = True
            else:
                spans.pop()

    if not explicit_date:
        match = take(re.search(r"(?<![\d月])(\d{1,2})\s*[日号](?!线)", norm))
        if match:
            candidate = _date_from_day(now, int(match.group(1)))
            if candidate:
                base_date = candidate
                explicit_date = True
            else:
                spans.pop()

    if not explicit_date:
        match = take(re.search(r"大后天|后天|明天|明日|今天|今日|今早|今晚|昨天|昨日|前天", norm))
        if match:
            word = match.group(0)
            base_date = now.date() + timedelta(days=_RELATIVE_DAYS[word])
            explicit_date = True
            explicit_today = word in ("今天", "今日", "今早", "今晚")
            if word == "今晚":
                forced_period = "晚上"
            elif word == "今早":
                forced_period = "早上"

    if not explicit_date:
        match = take(
            re.search(r"(?P<prefix>下下|下|这|本)?\s*(?:周|星期|礼拜)\s*(?P<wd>[一二三四五六日天])", norm)
        )
        if match:
            base_date = _weekday_date(now, match.group("prefix"), _WEEK[match.group("wd")])
            explicit_date = True

    if not explicit_date:
        match = take(re.search(rf"(\d+|[{_CN_NUM_CHARS}]+)\s*天(?:之)?后", norm))
        number = _cn_number(match.group(1)) if match else None
        if number is not None:
            base_date = now.date() + timedelta(days=number)
            explicit_date = True

    if not explicit_date:
        match = take(re.search(rf"(\d+|[{_CN_NUM_CHARS}]+)\s*(?:周|星期)\s*(?:之)?后", norm))
        number = _cn_number(match.group(1)) if match else None
        if number is not None:
            base_date = now.date() + timedelta(weeks=number)
            explicit_date = True

    # ---------- 时间 ----------
    start: datetime | None = None
    explicit_time = False
    period: str | None = None
    hour = minute = 0

    relative_minutes = re.search(rf"(\d+|[{_CN_NUM_CHARS}]+)\s*分钟(?:之)?后", norm)
    relative_hours = re.search(rf"(\d+|[{_CN_NUM_CHARS}]+)\s*(?:个)?小时(?:之)?后", norm)

    if relative_minutes:
        take(relative_minutes)
        number = _cn_number(relative_minutes.group(1)) or 0
        start = now + timedelta(minutes=number)
        explicit_time = True
    elif relative_hours:
        take(relative_hours)
        number = _cn_number(relative_hours.group(1)) or 0
        start = now + timedelta(hours=number)
        explicit_time = True
    else:
        match = take(
            re.search(
                r"(?P<period>凌晨|早上|早晨|上午|中午|下午|傍晚|晚上|夜里)?\s*"
                r"(?P<h>\d{1,2}|[一二三四五六七八九十两]{1,3})\s*"
                r"(?:点|(?<!小)时|:|：)\s*"
                r"(?P<mi>\d{1,2}|半|一刻|三刻|[一二三四五六七八九十两]{1,3})?\s*分?",
                norm,
            )
        )
        if match:
            hour_value = _cn_number(match.group("h"))
            minute_value = match.group("mi")
            if minute_value == "半":
                minute = 30
            elif minute_value == "一刻":
                minute = 15
            elif minute_value == "三刻":
                minute = 45
            elif minute_value:
                minute = _cn_number(minute_value) or 0
            else:
                minute = 0
            period = match.group("period") or forced_period
            if hour_value is not None and 0 <= hour_value <= 23 and 0 <= minute <= 59:
                hour = hour_value
                explicit_time = True
            else:
                spans.pop()
                period = None

    if not explicit_time:
        match = take(re.search(r"凌晨|早上|早晨|上午|中午|下午|傍晚|晚上|夜里", norm))
        if match:
            period = match.group(0)

    # 12 小时制换算
    if explicit_time and period:
        if period in ("下午", "傍晚", "晚上", "夜里") and hour < 12:
            hour += 12
        elif period == "中午" and hour < 11:
            hour += 12
        elif period in ("凌晨", "早上", "早晨", "上午") and hour == 12:
            hour = 0

    if start is None:
        if explicit_time:
            start = datetime.combine(base_date, time(hour, minute))
            if not explicit_date and not explicit_today and start < now:
                start += timedelta(days=1)
        else:
            default_hour = _PERIOD_DEFAULT.get(period or "", 9)
            start = datetime.combine(base_date, time(default_hour, 0))
            if not explicit_date and not explicit_today and start < now:
                start += timedelta(days=1)

    # ---------- 全天 ----------
    all_day = bool(take(re.search(r"全天|整天", norm)))

    # ---------- 时长 ----------
    duration: timedelta | None = None
    match = re.search(rf"(\d+(?:\.\d+)?|[{_CN_NUM_CHARS}]+)\s*(?:个)?(?:小时|钟头)(?!\s*后)", norm)
    if match:
        spans.append(match.span())
        raw_hours = match.group(1)
        hours = float(raw_hours) if re.fullmatch(r"\d+(?:\.\d+)?", raw_hours) else float(_cn_number(raw_hours) or 0)
        if hours > 0:
            duration = timedelta(minutes=round(hours * 60))
    if duration is None:
        match = re.search(r"(\d+)\s*分钟(?!\s*后)", norm)
        if match:
            spans.append(match.span())
            duration = timedelta(minutes=int(match.group(1)))

    # ---------- 地点 ----------
    location = ""
    match = take(re.search(r"(?:地点|地址|位置)\s*[:：]?\s*([^\s，,。；;、]+)", norm))
    if match:
        location = match.group(1).strip()

    # ---------- 标题 ----------
    chars = list(norm)
    for begin, end in sorted(spans, reverse=True):
        if 0 <= begin < end <= len(chars):
            chars[begin:end] = [" "] * (end - begin)
    title = "".join(chars)
    title = re.sub(r"[,，。；;、:：]+", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    title = re.sub(r"^(?:在|于|和|跟|与|及|还有|我们|咱们)\s*", "", title)
    title = title.strip(" -—")
    if not title:
        title = "新日程"

    if all_day:
        start = datetime.combine(start.date(), time(0, 0))
        end = start + timedelta(days=1)
    else:
        end = start + (duration or timedelta(hours=1))

    return [
        {
            "title": title,
            "start": start.isoformat(timespec="minutes"),
            "end": end.isoformat(timespec="minutes"),
            "all_day": all_day,
            "location": location,
            "notes": "",
            "confidence": 0.55,
        }
    ]
