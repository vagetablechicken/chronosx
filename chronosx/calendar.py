from functools import wraps
import os
import pandas_market_calendars as mcal
import pandas as pd


def require_1min_step(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 检查位置参数中的 step (假设在参数列表的较前位置)
        # 或者检查关键字参数 kwargs
        step = kwargs.get("step")

        # 如果不在 kwargs 里，尝试从 args 获取（根据你的函数定义，step 通常是第 3 或第 4 个参数）
        # 这里建议统一强制使用关键字传参，或在代码中固定位置
        if step is not None and step != "1min":
            raise ValueError(
                f"Performance Lock: '{func.__name__}' only supports step='1min'."
            )

        return func(*args, **kwargs)

    return wrapper


class StaticMinuteScheduler:
    """Load last 3 years and next 1 year schedule, raise error if time is not in the schedule

    Minute step, prepare all timeline at init, no more update
    """

    def __init__(self, calendar: mcal.MarketCalendar):
        self.calendar = calendar
        self.schedule = calendar.schedule(
            pd.Timestamp.now() - pd.Timedelta(days=365 * 3),
            pd.Timestamp.now() + pd.Timedelta(days=365),
            tz=calendar.tz,
        )
        self.intervals = pd.IntervalIndex.from_arrays(
            self.schedule["market_open"], self.schedule["market_close"], closed="left"
        )
        # date_range time is the end time, but we want the start time, so we need to shift back by one step
        self.trading_minutes = mcal.date_range(
            self.schedule, frequency="1min"
        ) - pd.Timedelta("1min")

    def __repr__(self):
        return f"StaticMinuteScheduler({self.calendar.name}, end={self.schedule.index[-1]})"

    def fetch_raw(self, time: pd.Timestamp):
        # TODO: should short the df?
        return self.schedule

    def fetch(
        self,
        start: pd.Timestamp,
        end: pd.Timestamp = None,
    ):
        if end is None:
            # only start time, return the min schedule range
            end = start + pd.Timedelta(days=1)

        left_idx = self.trading_minutes.searchsorted(start, side="left")
        right_idx = self.trading_minutes.searchsorted(end, side="left")
        return self.trading_minutes[left_idx:right_idx]

    def fetch_range(self, start: pd.Timestamp, delta: int):
        # hard to know, just return all
        return self.trading_minutes

    def fetch_previous(self, time: pd.Timestamp, inclusive):
        # quick search, use full data
        # inclusive, search right means > time, -1 must be <= time
        # exclusive, search left means >= time, -1 must be < time
        idx = (
            self.trading_minutes.searchsorted(
                time, side="right" if inclusive else "left"
            )
            - 1
        )
        return self.trading_minutes[idx] if idx >= 0 else None

    def fetch_next(self, time: pd.Timestamp, inclusive: bool):
        # quick search, use full data
        # inclusive, search left means >= time
        # exclusive, search right means > time
        idx = self.trading_minutes.searchsorted(
            time, side="left" if inclusive else "right"
        )
        return self.trading_minutes[idx] if idx < len(self.trading_minutes) else None

    def fetch_interval(self, time: pd.Timestamp):
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


class Calendar:
    def __init__(self, calendar_name: str):
        self.calendar: mcal.MarketCalendar = mcal.get_calendar(calendar_name)
        # schedule a large range of trading days to avoid repeated schedule calculation
        # TODO: step must be 1min, supporting other steps should consider the performance
        self.scheduler = StaticMinuteScheduler(self.calendar)

    @property
    def tz(self):
        return self.calendar.tz

    def __repr__(self):
        return f"Calendar({self.calendar.name}, {self.scheduler})"

    @require_1min_step
    def shift(self, time: pd.Timestamp, delta: int, step) -> pd.Timestamp:
        """Shift the time by delta in trading time, i.e. jump to the next trading time if the result is not a trading time."""
        assert step.startswith("1"), f"only support 1unit, but got {step}"
        trading_minutes = self.scheduler.fetch_range(time, delta)
        # if time is not a trading time, raise an error
        time_idx = trading_minutes.get_loc(time)
        return trading_minutes[time_idx + delta]

    def is_trading_time(self, time: pd.Timestamp) -> bool:
        """Check if the time is a trading time."""
        try:
            return self.calendar.open_at_time(self.scheduler.fetch_raw(time), time)
        except ValueError as _:
            # if time is not trading time(schedule won't have it)
            return False

    @require_1min_step
    def trading_times(self, start: pd.Timestamp, end: pd.Timestamp, step) -> pd.Series:
        # [start, end)
        tts = self.scheduler.fetch(start, end)
        return tts.to_series()

    @require_1min_step
    def next_trading_time(self, time: pd.Timestamp, step, inclusive) -> pd.Timestamp:
        return self.scheduler.fetch_next(time, inclusive)

    @require_1min_step
    def previous_trading_time(
        self, time: pd.Timestamp, step, inclusive
    ) -> pd.Timestamp:
        return self.scheduler.fetch_previous(time, inclusive)

    def to_session_end(self, time: pd.Timestamp) -> pd.Timestamp:
        """use calendar cuz we may meet early close time before holidays"""
        trading_day = self.scheduler.fetch_interval(time)
        return trading_day["market_close"]

    def to_session_start(self, time: pd.Timestamp) -> pd.Timestamp:
        trading_day = self.scheduler.fetch_interval(time)
        return trading_day["market_open"]


# China Exchange (Shanghai, Shenzhen, CFE) are all in the same timezone, so we can use the same calendar for them.
# CME Globex Crypto
_calendar_name = os.getenv("CALENDAR_NAME", "SSE")
GLOBAL_CALENDAR = Calendar(_calendar_name)
