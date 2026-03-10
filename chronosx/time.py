from datetime import datetime
import pandas as pd

from chronosx.calendar import GLOBAL_CALENDAR, Calendar

class ChronoTime:
    def __init__(self, raw_time: datetime | str, calendar: Calendar=GLOBAL_CALENDAR):
        self.raw_time = pd.Timestamp(raw_time)
        if self.raw_time.tzinfo is None:
            self.raw_time = self.raw_time.replace(tzinfo=calendar.tz())
        self.calendar = calendar

    def jump(self, delta: int, step='1min') -> 'ChronoTime':
        """ Shift the time by delta in trading time, i.e. jump to the next trading time if the result is not a trading time.
        """
        try:
            new_time = self.calendar.shift(self.raw_time, delta, step)
        except KeyError as e:
            raise ValueError(f"Time {self.raw_time} is not a trading time") from e
        return ChronoTime(new_time, self.calendar)

    def is_trading_time(self) -> bool:
        """ Check if the time is a trading time.
        """
        return self.calendar.is_trading_time(self.raw_time)
