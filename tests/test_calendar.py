from chronosx.calendar import Calendar
import pandas as pd


def test_shift():
    calendar = Calendar("SSE")
    time = calendar.shift(
        pd.Timestamp("2026-03-10T09:30:00", tz=calendar.tz), 1, "1min"
    )
    assert time == pd.Timestamp("2026-03-10T09:31:00", tz=calendar.tz)
    time = calendar.shift(
        pd.Timestamp("2026-03-10T09:30:00", tz=calendar.tz), -1, "1min"
    )
    assert time == pd.Timestamp("2026-03-09T14:59:00", tz=calendar.tz)
