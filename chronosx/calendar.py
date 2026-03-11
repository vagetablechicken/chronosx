import os
import pandas_market_calendars as mcal
import pandas as pd


class Calendar:
    def __init__(self, calendar_name: str):
        self.calendar: mcal.MarketCalendar = mcal.get_calendar(calendar_name)
        # TODO: schedule a large range of trading days to avoid repeated schedule calculation

    def tz(self):
        return self.calendar.tz

    def shift(self, time: pd.Timestamp, delta: int, step="1min") -> pd.Timestamp:
        """Shift the time by delta in trading time, i.e. jump to the next trading time if the result is not a trading time."""
        assert step.startswith("1"), f"only support 1unit, bot got {step}"
        init_delta = pd.Timedelta(days=14)
        shift_delta = pd.Timedelta(pd.tseries.frequencies.to_offset(step) * abs(delta))
        shift_delta = shift_delta if shift_delta > init_delta else init_delta
        schedule = self.calendar.schedule(
            start_date=time - shift_delta, end_date=time + shift_delta, tz=self.tz()
        )
        # calendar time means the end time, but we want the start time, so we need to shift back by one step
        trading_minutes = mcal.date_range(schedule, frequency=step) - pd.Timedelta(step)
        # if time is not a trading time, raise an error
        time_idx = trading_minutes.get_loc(time)
        return trading_minutes[time_idx + delta]

    def is_trading_time(self, time: pd.Timestamp) -> bool:
        """Check if the time is a trading time."""
        # no need to get the whole schedule, just check if the time is in the market minutes
        schedule = self.calendar.schedule(
            start_date=time - pd.Timedelta(minutes=1),
            end_date=time + pd.Timedelta(minutes=1),
            tz=self.tz(),
        )
        try:
            return self.calendar.open_at_time(schedule, time)
        except ValueError as _:
            # if time is not trading time(schedule won't have it)
            return False

    def trading_times(self, start: pd.Timestamp, end: pd.Timestamp, step) -> pd.Series:
        # select by date
        schedule = self.calendar.schedule(start, end, tz=self.tz())
        tts = mcal.date_range(schedule, frequency=step) - pd.Timedelta(step)
        start = pd.to_datetime(start).tz_localize(None).tz_localize(tts.tz)
        end = pd.to_datetime(end).tz_localize(None).tz_localize(tts.tz)
        # only return [start, end)
        mask = (tts >= start) & (tts < end)
        return tts[mask].to_series()


# China Exchange (Shanghai, Shenzhen, CFE) are all in the same timezone, so we can use the same calendar for them.
# CME Globex Crypto
_calendar_name = os.getenv("CALENDAR_NAME", "XSHG")
GLOBAL_CALENDAR = Calendar(_calendar_name)
