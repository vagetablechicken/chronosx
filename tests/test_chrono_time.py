import pandas as pd
import pytest
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
    with pytest.raises(ValueError):
        # left is not a trading time
        t1.jump(1, step='1min')
    t1 = ChronoTime("2026-03-10T09:30:00", calendar)
    t2 = t1.jump(1, step='1min')
    assert t2.raw_time.isoformat() == "2026-03-10T09:31:00+08:00"


def test_cme_globex_crypto_calendar():
    calendar = Calendar("CME Globex Crypto")
    t1 = ChronoTime("2025-10-24T00:00:00", calendar)
    assert t1.raw_time.isoformat() == "2025-10-24T00:00:00-05:00"
    t1 = ChronoTime("2025-12-24T00:00:00", calendar)
    assert t1.raw_time.isoformat() == "2025-12-24T00:00:00-06:00"
    t1 = ChronoTime("2025-12-24T16:00:00", calendar)
    assert t1.raw_time.isoformat() == "2025-12-24T16:00:00-06:00"

    assert not t1.is_trading_time(), "2025-12-24T16:00:00 is not a trading time"
