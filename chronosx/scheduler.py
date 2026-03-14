from contextlib import contextmanager
from datetime import tzinfo
from functools import wraps
import os
import threading

import pandas_market_calendars as mcal
import pandas as pd

"""Scheduler is a wrapper of Calendar and schedules, """


def require_1min_step(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        step = kwargs.get("step")
        if step is not None and step != "1min":
            raise ValueError(
                f"Performance Lock: '{func.__name__}' only supports step='1min'."
            )

        return func(*args, **kwargs)

    return wrapper


class SchedulerManager:
    _storage = threading.local()

    @staticmethod
    def get_scheduler():
        if not hasattr(SchedulerManager._storage, "schedule"):
            # SSE: China Exchange (Shanghai, Shenzhen, CFE) are all in the same timezone, so we can use the same calendar for them.
            # CME Globex Crypto
            # other calendars haven't been checked
            SchedulerManager._storage.schedule = StaticMinuteScheduler(
                os.getenv("CALENDAR_NAME", "SSE")
            )
        return SchedulerManager._storage.schedule

    @staticmethod
    def set_scheduler(schedule):
        SchedulerManager._storage.schedule = schedule

    @staticmethod
    @contextmanager
    def use_scheduler(temp_schedule):
        """
        临时切换 Schedule，退出 with 块后自动恢复。
        用法:
        with SchedulerManager.use_schedule(MockSchedule()):
            # 执行测试逻辑
        """
        # 1. 记录旧状态
        has_old = hasattr(SchedulerManager._storage, "schedule")
        old_schedule = getattr(SchedulerManager._storage, "schedule", None)

        # 2. 设置新状态
        SchedulerManager.set_scheduler(temp_schedule)

        try:
            yield
        finally:
            # 3. 恢复旧状态
            if has_old:
                SchedulerManager.set_scheduler(old_schedule)
            else:
                # 如果原本没有 schedule，则清理掉，保持 threading.local 干净
                if hasattr(SchedulerManager._storage, "schedule"):
                    del SchedulerManager._storage.schedule


class SchedulerTemplate:
    def shift(self, time: pd.Timestamp, delta: int, step: str) -> pd.Timestamp: ...
    def trading_times(
        self, start: pd.Timestamp, end: pd.Timestamp, step: str
    ) -> pd.Series: ...
    def previous_trading_time(
        self, time: pd.Timestamp, step: str, inclusive=True
    ) -> pd.Timestamp: ...
    def next_trading_time(
        self, time: pd.Timestamp, step: str, inclusive=True
    ) -> pd.Timestamp: ...

    def is_trading(self, time: pd.Timestamp) -> bool: ...
    def is_trading_day(self, time: pd.Timestamp) -> bool:
        """Check if the time is a trading day, no matter if it's a trading time."""
        ...

    def to_session_start(self, time: pd.Timestamp) -> pd.Timestamp: ...
    def to_session_end(self, time: pd.Timestamp) -> pd.Timestamp: ...

    @property
    def tz(self) -> tzinfo: ...


class StaticMinuteScheduler(SchedulerTemplate):
    """
    Load last 3 years and next 3 year schedule, let it crash if time is not in the schedule

    For performance, only support 1 minute step, prepare all timeline when init, no more updates
    """

    def __init__(self, calendar_name: str):
        self.calendar = mcal.get_calendar(calendar_name)
        self.schedule = self.calendar.schedule(
            pd.Timestamp.now() - pd.Timedelta(days=365 * 3),
            pd.Timestamp.now() + pd.Timedelta(days=365 * 3),
            tz=self.calendar.tz,
        )
        self.intervals = pd.IntervalIndex.from_arrays(
            self.schedule["market_open"], self.schedule["market_close"], closed="left"
        )
        # date_range time is the end time, but we want the start time, so we need to shift back by one step
        self.trading_minutes = mcal.date_range(
            self.schedule, frequency="1min"
        ) - pd.Timedelta("1min")

    @property
    def tz(self):
        return self.calendar.tz

    def __repr__(self):
        return f"StaticMinuteScheduler({self.calendar.name}, end={self.schedule.index[-1]})"

    @require_1min_step
    def shift(self, time: pd.Timestamp, delta: int, *, step: str) -> pd.Timestamp:
        """
        Shift the time by delta in trading time, i.e. jump to the next trading time if the result is not a trading time.

        Time should be a valid trading time.
        """
        # raise an error if time is not a trading time
        time_idx = self.trading_minutes.get_loc(time)
        # raise an error if out of range
        return self.trading_minutes[time_idx + delta]

    @require_1min_step
    def trading_times(
        self, start: pd.Timestamp, end: pd.Timestamp, *, step: str
    ) -> pd.Series:
        # [start, end)
        left_idx = self.trading_minutes.searchsorted(start, side="left")
        right_idx = self.trading_minutes.searchsorted(end, side="left")
        return self.trading_minutes[left_idx:right_idx].to_series()

    @require_1min_step
    def previous_trading_time(
        self, time: pd.Timestamp, *, step: str, inclusive: bool
    ) -> pd.Timestamp:
        # inclusive, search right means > time, -1 must be <= time
        # exclusive, search left means >= time, -1 must be < time
        # TODO: binary search is quick, but time may out of range
        idx = (
            self.trading_minutes.searchsorted(
                time, side="right" if inclusive else "left"
            )
            - 1
        )
        return self.trading_minutes[idx] if idx >= 0 else None

    @require_1min_step
    def next_trading_time(
        self, time: pd.Timestamp, *, step: str, inclusive: bool
    ) -> pd.Timestamp:
        # inclusive, search left means >= time
        # exclusive, search right means > time
        idx = self.trading_minutes.searchsorted(
            time, side="left" if inclusive else "right"
        )
        return self.trading_minutes[idx] if idx < len(self.trading_minutes) else None

    def is_trading(self, time: pd.Timestamp) -> bool:
        """Check if the time is a trading time."""
        idx = self.intervals.get_indexer([self])
        return idx[0] != -1

    def is_trading_day(self, time: pd.Timestamp) -> bool:
        """Check if the date is in trading, no matter if it's a trading time."""
        # trading day may start from previous day, use interval to check
        day_start = time.normalize()
        day_end = day_start + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)
        target_interval = pd.Interval(day_start, day_end, closed="left")

        # 检查 IntervalIndex 中是否有任何区间与这一天重叠
        # overlaps 返回一个布尔数组，.any() 判断是否存在至少一个 True
        return self.intervals.overlaps(target_interval).any()

    def _fetch_interval(self, time: pd.Timestamp):
        # find time belongs to which trading day in schedule
        # check target_time, contains will return a mask
        is_inside = self.intervals.contains(time)

        if not is_inside.any():
            raise ValueError(f"Time {time} is not in trading interval")
        if is_inside.sum() != 1:
            raise ValueError(
                f"Time {time} is in multiple trading days {self.intervals[is_inside]}"
            )

        return self.schedule.loc[is_inside].iloc[0]

    def to_session_end(self, time: pd.Timestamp) -> pd.Timestamp:
        """use calendar cuz we may meet early close time before holidays"""
        trading_day = self._fetch_interval(time)
        return trading_day["market_close"]

    def to_session_start(self, time: pd.Timestamp) -> pd.Timestamp:
        trading_day = self._fetch_interval(time)
        return trading_day["market_open"]
