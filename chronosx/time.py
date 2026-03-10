from datetime import datetime
import pandas as pd

from chronosx.calendar import GLOBAL_CALENDAR, Calendar

class ChronoTime:
    def __init__(self, raw_time: datetime | str, calendar: Calendar=GLOBAL_CALENDAR):
        self.raw_time = raw_time
        if isinstance(raw_time, str):
            self.raw_time = datetime.fromisoformat(raw_time)
        if self.raw_time.tzinfo is None:
            self.raw_time = self.raw_time.replace(tzinfo=calendar.tz())
        self.calendar = calendar

    def jump(self, delta: int, step='1T') -> 'ChronoTime':
        """ Shift the time by delta in trading time, i.e. jump to the next trading time if the result is not a trading time.
        """
        new_time = self.calendar.shift(self.raw_time, delta, step)
        return ChronoTime(new_time, self.calendar)