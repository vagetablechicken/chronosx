from contextlib import contextmanager
from datetime import tzinfo
from functools import wraps
import os
import threading

import pandas_market_calendars as mcal
import pandas as pd

"""
Scheduler abstractions for trading-calendar queries.

The scheduler implementation is customizable, but the default runtime scheduler is
`StaticMinuteScheduler` because it precomputes a fixed timeline and is optimized
for performance.
"""


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
        Temporarily switch the active scheduler and restore it after the `with` block.

        Usage:
        with SchedulerManager.use_schedule(MockSchedule()):
            # run test logic
        """
        # 1. Save the previous scheduler state.
        has_old = hasattr(SchedulerManager._storage, "schedule")
        old_schedule = getattr(SchedulerManager._storage, "schedule", None)

        # 2. Install the temporary scheduler.
        SchedulerManager.set_scheduler(temp_schedule)

        try:
            yield
        finally:
            # 3. Restore the previous scheduler state.
            if has_old:
                SchedulerManager.set_scheduler(old_schedule)
            else:
                # If there was no scheduler before, remove the temporary value so
                # the thread-local storage stays clean.
                if hasattr(SchedulerManager._storage, "schedule"):
                    del SchedulerManager._storage.schedule


class SchedulerTemplate:
    def shift(self, time: pd.Timestamp, delta: int, step: str) -> pd.Timestamp: ...
    def trading_times(
        self, start: pd.Timestamp, end: pd.Timestamp, step: str
    ) -> pd.Series: ...
    def trading_day_delta(self, start: pd.Timestamp, end: pd.Timestamp) -> int: ...
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
        self.session_intervals = pd.IntervalIndex.from_arrays(
            self.schedule["market_open"],
            self.schedule["market_close"],
            closed="left",
        )
        if "break_start" not in self.schedule.columns:
            self.intervals = self.session_intervals
        else:
            # SSE has one break per trading day; multi-break calendars are not
            # handled here.
            starts_1 = self.schedule["market_open"]
            ends_1 = self.schedule["break_start"]

            starts_2 = self.schedule["break_end"]
            ends_2 = self.schedule["market_close"]

            # Flatten the split sessions into a single list of intervals.
            all_starts = pd.concat([starts_1, starts_2]).dropna().sort_values()
            all_ends = pd.concat([ends_1, ends_2]).dropna().sort_values()

            # Build the interval index once so ordering stays strictly increasing
            # and duplicates are avoided.
            self.intervals = pd.IntervalIndex.from_arrays(
                all_starts, all_ends, closed="left"
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

        Time should be a valid trading time, second and microsecond will be preserved.
        """
        # save second and microsecond
        second = time.second
        microsecond = time.microsecond
        time = time.replace(second=0, microsecond=0)
        # raise an error if time is not a trading time
        time_idx = self.trading_minutes.get_loc(time)
        # raise an error if out of range
        shifted = self.trading_minutes[time_idx + delta]
        # restore second and microsecond
        return shifted.replace(second=second, microsecond=microsecond)

    @require_1min_step
    def trading_times(
        self, start: pd.Timestamp, end: pd.Timestamp, *, step: str
    ) -> pd.Series:
        # [start, end)
        left_idx = self.trading_minutes.searchsorted(start, side="left")
        right_idx = self.trading_minutes.searchsorted(end, side="left")
        return self.trading_minutes[left_idx:right_idx].to_series()

    def trading_day_delta(self, start: pd.Timestamp, end: pd.Timestamp) -> int:
        """
        Return the signed trading-day distance between `start` and `end`.

        The delta is based on calendar dates in the scheduler timezone, so intraday
        time does not matter. If either endpoint falls on a non-trading date, that
        date contributes 0. Order is preserved: forward ranges are positive and
        backward ranges are negative.
        """
        start_day = start.normalize().tz_localize(None)
        end_day = end.normalize().tz_localize(None)
        if start_day <= end_day:
            left_idx = self.schedule.index.searchsorted(start_day, side="left")
            right_idx = self.schedule.index.searchsorted(end_day, side="right")
            return right_idx - left_idx

        left_idx = self.schedule.index.searchsorted(end_day, side="left")
        right_idx = self.schedule.index.searchsorted(start_day, side="right")
        return -(right_idx - left_idx)

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
        # be careful to exclude break times
        idx = self.intervals.get_indexer([time])
        return idx[0] != -1

    def is_trading_day(self, time: pd.Timestamp) -> bool:
        """Check if the date is in trading, no matter if it's a trading time."""
        # trading day may start from previous day, use interval to check
        day_start = time.normalize()
        day_end = day_start + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)

        # O(log N) fast overlap check instead of O(N) `self.session_intervals.overlaps().any()`
        # 1. Find the first trading session that ends AFTER the day starts
        close_times = self.schedule["market_close"]
        idx = close_times.searchsorted(day_start, side="right")

        if idx == len(close_times):
            return False
            
        # 2. Check if this session starts BEFORE the day ends
        return self.schedule["market_open"].iloc[idx] <= day_end

    def _fetch_interval(self, time: pd.Timestamp):
        # We use `get_indexer` instead of `contains` for performance.
        # `contains` evaluates all intervals and returns a full boolean mask (O(N)),
        # which is slow over thousands of trading days. Because trading sessions
        # do not overlap, `get_indexer` safely uses the underlying C-level
        # IntervalTree for O(log N) lookups, providing massive speedups.
        idx = self.session_intervals.get_indexer([time])[0]
        if idx == -1:
            raise ValueError(f"Time {time} is not in trading interval")
        
        return self.schedule.iloc[idx]

    def to_session_end(self, time: pd.Timestamp) -> pd.Timestamp:
        """use calendar cuz we may meet early close time before holidays"""
        trading_day = self._fetch_interval(time)
        return trading_day["market_close"]

    def to_session_start(self, time: pd.Timestamp) -> pd.Timestamp:
        trading_day = self._fetch_interval(time)
        return trading_day["market_open"]
