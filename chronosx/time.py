from datetime import datetime
import pandas as pd

from chronosx.calendar import GLOBAL_CALENDAR, Calendar


class ChronoTime:
    def __init__(self, raw_time: datetime | str, calendar: Calendar = GLOBAL_CALENDAR):
        self.raw_time = pd.Timestamp(raw_time)
        if self.raw_time.tzinfo is None:
            self.raw_time = self.raw_time.replace(tzinfo=calendar.tz)
        self.calendar = calendar

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

    def next_trading_time(self, step="1min"):
        """Self can be invalid trading time, jump to next trading time"""
        return self.calendar.next_trading_time(self.raw_time, step)
