from __future__ import annotations

import unittest
from datetime import datetime

from calendar_app.event_utils import normalize_event
from calendar_app.parser import parse

NOW = datetime(2026, 11, 5, 14, 30)  # 星期四


class ParserTests(unittest.TestCase):
    def test_relative_day_and_afternoon(self):
        event = parse("明天下午3点和张总开会", NOW)[0]
        self.assertEqual(event["start"], "2026-11-06T15:00")
        self.assertEqual(event["end"], "2026-11-06T16:00")
        self.assertIn("张总", event["title"])

    def test_next_weekday(self):
        event = parse("下周一上午10点项目评审", NOW)[0]
        self.assertEqual(event["start"], "2026-11-09T10:00")

    def test_absolute_date_without_time(self):
        event = parse("2026年12月1日交季度报告", NOW)[0]
        self.assertEqual(event["start"], "2026-12-01T09:00")
        self.assertEqual(event["end"], "2026-12-01T10:00")

    def test_half_hour(self):
        event = parse("明天上午9点半体检", NOW)[0]
        self.assertEqual(event["start"], "2026-11-06T09:30")

    def test_location(self):
        event = parse("后天下午2点见客户 地点 3楼会议室", NOW)[0]
        self.assertEqual(event["start"], "2026-11-07T14:00")
        self.assertEqual(event["location"], "3楼会议室")
        self.assertNotIn("地点", event["title"])

    def test_duration(self):
        event = parse("明天下午3点开会2小时", NOW)[0]
        self.assertEqual(event["end"], "2026-11-06T17:00")

    def test_all_day(self):
        event = parse("明天全天团建", NOW)[0]
        self.assertTrue(event["all_day"])
        self.assertEqual(event["start"], "2026-11-06T00:00")
        self.assertEqual(event["end"], "2026-11-07T00:00")

    def test_relative_hours(self):
        event = parse("2小时后喝水", NOW)[0]
        self.assertEqual(event["start"], "2026-11-05T16:30")

    def test_evening(self):
        event = parse("晚上8点看电影", NOW)[0]
        self.assertEqual(event["start"], "2026-11-05T20:00")

    def test_passed_time_rolls_to_tomorrow(self):
        event = parse("上午10点开会", NOW)[0]
        self.assertEqual(event["start"], "2026-11-06T10:00")

    def test_explicit_today_does_not_roll(self):
        event = parse("今天上午10点开会", NOW)[0]
        self.assertEqual(event["start"], "2026-11-05T10:00")

    def test_day_of_month(self):
        event = parse("12号下午4点复查", NOW)[0]
        self.assertEqual(event["start"], "2026-11-12T16:00")

    def test_empty_title_falls_back(self):
        event = parse("明天", NOW)[0]
        self.assertEqual(event["title"], "新日程")


class NormalizeTests(unittest.TestCase):
    def test_end_before_start_is_fixed(self):
        event = normalize_event(
            {"title": "测试", "start": "2026-11-06T15:00", "end": "2026-11-06T14:00"}
        )
        self.assertEqual(event["end"], "2026-11-06T16:00")

    def test_all_day_normalization(self):
        event = normalize_event({"title": "团建", "start": "2026-11-06T15:00", "all_day": True})
        self.assertEqual(event["start"], "2026-11-06T00:00")
        self.assertEqual(event["end"], "2026-11-07T00:00")

    def test_missing_title(self):
        with self.assertRaises(ValueError):
            normalize_event({"start": "2026-11-06T15:00"})


if __name__ == "__main__":
    unittest.main()
