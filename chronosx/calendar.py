import os
import pandas_market_calendars as mcal
import pandas as pd


class StaticScheduler:
    """Load last 3 years and next 1 year schedule, raise error if time is not in the schedule"""

    def __init__(self, calendar: mcal.MarketCalendar):
        self.calendar = calendar
        self.schedule = calendar.schedule(
            pd.Timestamp.now() - pd.Timedelta(days=365 * 3),
            pd.Timestamp.now() + pd.Timedelta(days=365),
            tz=calendar.tz,
        )

    def prepare(self, start: pd.Timestamp, end: pd.Timestamp):
        """No update, skip check"""
        ...


class Calendar:
    def __init__(self, calendar_name: str):
        self.calendar: mcal.MarketCalendar = mcal.get_calendar(calendar_name)
        # schedule a large range of trading days to avoid repeated schedule calculation
        self.scheduler = StaticScheduler(self.calendar)

    # bind schedule result of self.scheduer
    @property
    def schedule(self) -> pd.DataFrame:
        return self.scheduler.schedule

    @property
    def tz(self):
        return self.calendar.tz

    def shift(self, time: pd.Timestamp, delta: int, step) -> pd.Timestamp:
        """Shift the time by delta in trading time, i.e. jump to the next trading time if the result is not a trading time."""
        assert step.startswith("1"), f"only support 1unit, but got {step}"
        # TODO: how to handle delta? find the time idx first, then calc target idx?
        self.scheduler.prepare(time, time)
        # calendar time means the end time, but we want the start time, so we need to shift back by one step
        trading_minutes = mcal.date_range(self.schedule, frequency=step) - pd.Timedelta(
            step
        )
        # if time is not a trading time, raise an error
        time_idx = trading_minutes.get_loc(time)
        return trading_minutes[time_idx + delta]

    def is_trading_time(self, time: pd.Timestamp) -> bool:
        """Check if the time is a trading time."""
        # no need to get the whole schedule, just check if the time is in the market minutes
        self.scheduler.prepare(time, time)
        try:
            return self.calendar.open_at_time(self.schedule, time)
        except ValueError as _:
            # if time is not trading time(schedule won't have it)
            return False

    def trading_times(self, start: pd.Timestamp, end: pd.Timestamp, step) -> pd.Series:
        # select by date, to avoid end time delongs to the next day, alwasy add
        self.scheduler.prepare(start, end)
        tts = mcal.date_range(self.schedule, frequency=step) - pd.Timedelta(step)
        # only return [start, end)
        mask = (tts >= start) & (tts < end)
        return tts[mask].to_series()

    def next_trading_time(self, time: pd.Timestamp, step, inclusive) -> pd.Timestamp:
        self.scheduler.prepare(time, time)
        tts = mcal.date_range(self.schedule, frequency=step) - pd.Timedelta(step)
        # inclusive, search left means >= time
        # exclusive, search right means > time
        idx = tts.searchsorted(time, side="left" if inclusive else "right")
        return tts[idx] if idx < len(tts) else None

    def previous_trading_time(
        self, time: pd.Timestamp, step, inclusive
    ) -> pd.Timestamp:
        # TODO: short interval don't need long schedule, let scheduler give me the right schedule
        self.scheduler.prepare(time, time)
        tts = mcal.date_range(self.schedule, frequency=step) - pd.Timedelta(step)
        # inclusive, search right means > time, -1 must be <= time
        # exclusive, search left means >= time, -1 must be < time
        idx = tts.searchsorted(time, side="right" if inclusive else "left") - 1
        return tts[idx] if idx >= 0 else None

    def _search_interval(self, time: pd.Timestamp) -> pd.Interval:
        # find time belongs to which trading day in schedule
        # TODO: mv to scheduler for fast prepare
        intervals = pd.IntervalIndex.from_arrays(
            self.schedule["market_open"], self.schedule["market_close"], closed="left"
        )

        # check target_time, contains will return a mask
        is_inside = intervals.contains(time)

        if not is_inside.any():
            raise ValueError(f"Time {time} is not in trading interval")
        if is_inside.sum() != 1:
            raise ValueError(
                f"Time {time} is in multiple trading days {intervals[is_inside]}"
            )

        return self.schedule.loc[is_inside].iloc[0]

    def to_session_end(self, time: pd.Timestamp) -> pd.Timestamp:
        """use calendar cuz we may meet early close time before holidays"""
        trading_day = self._search_interval(time)
        return trading_day["market_close"]

    def to_session_start(self, time: pd.Timestamp) -> pd.Timestamp:
        trading_day = self._search_interval(time)
        return trading_day["market_open"]


# China Exchange (Shanghai, Shenzhen, CFE) are all in the same timezone, so we can use the same calendar for them.
# CME Globex Crypto
_calendar_name = os.getenv("CALENDAR_NAME", "SSE")
GLOBAL_CALENDAR = Calendar(_calendar_name)
