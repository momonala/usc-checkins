import logging
from calendar import monthrange
from datetime import datetime
from typing import Callable

import pandas as pd

from usc.database import get_attendance_per_month, get_sport_per_month

logger = logging.getLogger(__name__)


def get_value_counts_for_frame(check_ins: pd.DataFrame) -> pd.DataFrame:
    """Get the value counts based off "venue", "checkin_limit", "cost" for the check_ins DataFrame."""
    value_counts = check_ins.value_counts(["venue", "checkin_limit", "cost"]).reset_index()
    value_counts.columns = ["venue", "checkin_limit", "cost", "count"]
    value_counts["cost"] = value_counts["cost"] * value_counts["count"]
    return value_counts


def format_checkins_rows_for_message(
    _format_row: Callable, check_ins_this_month: pd.DataFrame | pd.Series
) -> tuple[str, pd.Series]:
    check_ins_this_month.sort_values("count", ascending=False, inplace=True)
    rows = [
        _format_row(row["venue"], row["count"], row["checkin_limit"])
        for _, row in check_ins_this_month.iterrows()
    ]
    rows = "\n".join(rows)
    totals = check_ins_this_month[["count", "cost"]].sum()
    return rows, totals


def format_sports_for_msg(sports_this_month: pd.DataFrame) -> str:
    sports_this_month = sports_this_month.to_dict()["count"]
    return "\n".join([f"{sport:29s}{count}" for sport, count in sports_this_month.items()]).replace(" ", "-")


def format_attendance_per_month_for_msg(year: int = None, month: int = None) -> str:
    """Formats the return of `get_attendance_per_month` as a Markdown string for sending to Telegram."""

    def _format_row(_venue, _checkin_count: str, _checkin_limit: str) -> str:
        return f"{_venue[:25]:25s}{_checkin_count:>4}/{_checkin_limit}".replace(" ", "-")

    today = datetime.today()
    if not all([month, year]):
        month, year = (today.month, today.year)
        date_header = today.strftime("%a, %d %B %Y")
        days_remaining = f"🕠 Days remaining: {monthrange(2023, 7)[1] - today.day}"
    else:
        d = datetime(day=1, month=month, year=year)
        date_header = f'for {d.strftime("%B %Y")}'
        days_remaining = None

    check_ins_this_month = get_attendance_per_month(year=year, month=month)
    rows_checkins, totals_checkins = format_checkins_rows_for_message(_format_row, check_ins_this_month)
    sports_this_month = format_sports_for_msg(get_sport_per_month(year=year, month=month))
    msg = f"""
👀 Check ins {date_header} 👀
💪🏾 Count: {int(totals_checkins["count"])}
💰 Value: {totals_checkins["cost"]}€
{days_remaining if days_remaining else ""}

Venues:
```\n{rows_checkins}```

Sports:
```\n{sports_this_month}```
"""
    return msg


def get_total_check_ins_for_msg():
    """Formats the full checkins dataframe (total value counts) as a Markdown string for sending to Telegram."""

    def _format_row(_venue, _checkin_count: str, _checkin_limit: str) -> str:
        return f"{_venue[:25]:25s}{_checkin_count:>4}".replace(" ", "-")

    checkins_value_counts = get_attendance_per_month()
    rows_checkins, totals_checkins = format_checkins_rows_for_message(_format_row, checkins_value_counts)
    sports_this_month = format_sports_for_msg(get_sport_per_month())
    msg = f"""
⭐ Check ins all time! ⭐ 
💪🏾 Count: {int(totals_checkins["count"])}
💰 Value: {totals_checkins["cost"]}€

Venues:
```\n{rows_checkins}```

Sports:
```\n{sports_this_month}```
"""
    return msg
