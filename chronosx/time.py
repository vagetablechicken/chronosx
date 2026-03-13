from __future__ import annotations
from datetime import datetime
import threading
import pandas as pd

from chronosx.calendar import GLOBAL_CALENDAR, Calendar


class ChronoTime:
    # 使用 Thread-Local 确保多线程测试互不干扰
    _local = threading.local()

    @staticmethod
    def _get_stack():
        if not hasattr(ChronoTime._local, "stack"):
            ChronoTime._local.stack = []
        return ChronoTime._local.stack

    @staticmethod
    def now(calendar: Calendar = GLOBAL_CALENDAR):
        stack = ChronoTime._get_stack()
        if stack:
            # 返回栈顶的模拟时间
            return stack[-1]
        return ChronoTime(pd.Timestamp.now(calendar.tz), calendar)

    def __init__(
        self,
        raw_time: datetime | str | "ChronoTime",
        calendar: Calendar = GLOBAL_CALENDAR,
    ):
        if isinstance(raw_time, ChronoTime):
            self.raw_time = raw_time.raw_time
            # use the same calendar of input
            self.calendar = raw_time.calendar
            return

        self.raw_time = pd.Timestamp(raw_time)
        if self.raw_time.tzinfo is None:
            self.raw_time = self.raw_time.replace(tzinfo=calendar.tz)
        self.calendar = calendar

    def __repr__(self):
        return f"ChronoTime({self.raw_time}, {self.calendar})"

    def __str__(self):
        return str(self.raw_time)

    def __eq__(self, value):
        """ignore calendar"""
        if isinstance(value, ChronoTime):
            return self.raw_time == value.raw_time
        elif isinstance(value, pd.Timestamp) or isinstance(value, datetime):
            return self.raw_time == value
        else:
            return False

    def jump(self, delta: int, step="1min") -> "ChronoTime":
        """Shift the time by delta in trading time, i.e. jump to the next trading time if the result is not a trading time.

        Self should be a valid trading time.
        """
        try:
            new_time = self.calendar.shift(self.raw_time, delta, step)
        except KeyError as e:
            raise ValueError(f"Time {self.raw_time} is not a trading time") from e
        except AssertionError as e:
            raise ValueError("unsupported input") from e
        return ChronoTime(new_time, self.calendar)

    def is_trading_time(self) -> bool:
        """Check if the time is a trading time."""
        return self.calendar.is_trading_time(self.raw_time)

    def trading_times_until(self, end, step="1min"):
        """From self time to end time, get all times to be a list"""
        end_dt: pd.Timestamp = pd.to_datetime(end)
        if end_dt.tz is None:
            end_dt = end_dt.tz_localize(self.calendar.tz)

        return self.calendar.trading_times(self.raw_time, end_dt, step)

    def next_trading_time(self, step="1min", inclusive=True) -> "ChronoTime":
        """trading time >= self, > self if inclusive is False"""
        new_time = self.calendar.next_trading_time(self.raw_time, step, inclusive)
        return ChronoTime(new_time, self.calendar)

    def previous_trading_time(self, step="1min", inclusive=True) -> "ChronoTime":
        """trading time <= self, < self if inclusive is False"""
        new_time = self.calendar.previous_trading_time(self.raw_time, step, inclusive)
        return ChronoTime(new_time, self.calendar)

    def to_session_end(self) -> "ChronoTime":
        """use calendar cuz we may meet early close time before holidays"""
        return ChronoTime(self.calendar.to_session_end(self.raw_time), self.calendar)

    def to_session_start(self) -> "ChronoTime":
        return ChronoTime(self.calendar.to_session_start(self.raw_time), self.calendar)

    def timestamp(self) -> pd.Timestamp:
        return self.raw_time.to_pydatetime()

    def __add__(self, other):
        other = (
            other.raw_time if isinstance(other, ChronoTime) else pd.to_datetime(other)
        )
        return self.raw_time + other

    def __sub__(self, other):
        other = (
            other.raw_time if isinstance(other, ChronoTime) else pd.to_datetime(other)
        )
        return self.raw_time - other

    def __lt__(self, other):
        other = (
            other.raw_time if isinstance(other, ChronoTime) else pd.to_datetime(other)
        )
        return self.raw_time < other

    def __le__(self, other):
        other = (
            other.raw_time if isinstance(other, ChronoTime) else pd.to_datetime(other)
        )
        return self.raw_time <= other

    def __gt__(self, other):
        other = (
            other.raw_time if isinstance(other, ChronoTime) else pd.to_datetime(other)
        )
        return self.raw_time > other

    def __ge__(self, other):
        other = (
            other.raw_time if isinstance(other, ChronoTime) else pd.to_datetime(other)
        )
        return self.raw_time >= other

    def __ne__(self, other):
        return not self.__eq__(other)
