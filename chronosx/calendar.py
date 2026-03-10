import os
import pandas_market_calendars as mcal
import pandas as pd

class Calendar:
    def __init__(self, calendar_name: str):
        self.calendar = mcal.get_calendar(calendar_name)
        # TODO: schedule a large range of trading days to avoid repeated schedule calculation
    
    def tz(self):
        return self.calendar.tz

    def shift(self, time: pd.Timestamp, delta: int, step='1min') -> pd.Timestamp:
        """ Shift the time by delta in trading time, i.e. jump to the next trading time if the result is not a trading time.
        """
        init_delta = pd.Timedelta(days=14)
        shift_delta = pd.Timedelta(pd.tseries.frequencies.to_offset(step) * abs(delta))
        shift_delta = shift_delta if shift_delta > init_delta else init_delta
        schedule = self.calendar.schedule(start_date=time - shift_delta, end_date=time + shift_delta, tz=self.tz())
        market_minutes = mcal.date_range(schedule, frequency=step)
        time_idx = market_minutes.get_loc(time)
        return market_minutes.values[time_idx + delta]


# China Exchange (Shanghai, Shenzhen, CFE) are all in the same timezone, so we can use the same calendar for them.
# CME Globex Crypto
_calendar_name = os.getenv("CALENDAR_NAME", "XSHG")
GLOBAL_CALENDAR = Calendar(_calendar_name)
