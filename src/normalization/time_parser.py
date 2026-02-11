from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional


@dataclass
class TimeParseResult:
    original_phrase: Optional[str]
    resolved: Optional[dict]


def _first_day_of_month(d: date) -> date:
    return d.replace(day=1)


def _first_day_of_last_month(d: date) -> date:
    first_this_month = d.replace(day=1)
    return (first_this_month - timedelta(days=1)).replace(day=1)


def _last_day_of_last_month(d: date) -> date:
    return d.replace(day=1) - timedelta(days=1)


def parse_time_phrase(text: str, now: Optional[datetime] = None) -> TimeParseResult:
    now = now or datetime.now()
    today = now.date()

    mappings = [
        (["今天", "今日", "today"], "single_date", today, today),
        (["昨天", "昨日", "yesterday"], "single_date", today - timedelta(days=1), today - timedelta(days=1)),
        (["近7天", "最近7天", "last 7 days"], "date_range", today - timedelta(days=6), today),
        (["本月", "这个月", "這個月", "this month"], "month_to_date", _first_day_of_month(today), today),
        (["今年", "this year"], "year_to_date", date(today.year, 1, 1), today),
        (["上月", "上個月", "last month"], "date_range", _first_day_of_last_month(today), _last_day_of_last_month(today)),
    ]

    lowered = text.lower()
    for keywords, kind, start, end in mappings:
        for keyword in keywords:
            if keyword.lower() in lowered:
                return TimeParseResult(
                    original_phrase=keyword,
                    resolved={
                        "type": kind,
                        "start_date": start.isoformat(),
                        "end_date": end.isoformat(),
                    },
                )

    return TimeParseResult(original_phrase=None, resolved=None)
