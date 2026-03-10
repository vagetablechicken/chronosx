import pandas as pd
from chronosx.calendar import Calendar
from chronosx.time import ChronoTime

def test_init():
    # use local calendar for testing
    calendar = Calendar("XSHG")
    t1 = ChronoTime("2024-01-01T00:00:00", calendar)
    assert t1.raw_time.isoformat() == "2024-01-01T00:00:00+08:00"

    t1 = ChronoTime("2024-01-01T09:30:00", calendar)
    assert t1.raw_time.isoformat() == "2024-01-01T09:30:00+08:00"

def test_time_shift():
    calendar = Calendar("XSHG")
    t1 = ChronoTime("2026-01-01T00:00:00", calendar)
    t2 = t1.jump(1, step='1min')
    assert t2.raw_time.isoformat() == "2026-01-01T00:01:00+08:00"


def test_cme_globex_crypto_calendar():
    calendar = Calendar("CME Globex Crypto")
    trading_days = calendar.get_trading_days("2024-01-01", "2024-01-10")
    assert len(trading_days) == 6
    assert trading_days[0].isoformat() == "2024-01-01T00:00:00+00:00"
    assert trading_days[-1].isoformat() == "2024-01-10T00:00:00+00:00"
