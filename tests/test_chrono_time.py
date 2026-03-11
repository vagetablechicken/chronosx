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
    with pytest.raises(ValueError):
        # left is not a trading time
        ChronoTime("2026-01-01T00:00:00", calendar).jump(1, step="1min")

    t = ChronoTime("2026-03-10T09:30:00", calendar).jump(1, step="1min")
    assert t.raw_time.isoformat() == "2026-03-10T09:31:00+08:00"

    t = ChronoTime("2026-03-10T11:29:00", calendar).jump(3, step="1min")
    assert t.raw_time.isoformat() == "2026-03-10T13:02:00+08:00"
    t = ChronoTime("2026-03-10T11:29:00", calendar).jump(3)  # default step is 1min
    assert t.raw_time.isoformat() == "2026-03-10T13:02:00+08:00"

    # if step is 3, t may not be a valid time in 3min step trading time series NOTE: don't support it
    with pytest.raises(ValueError):
        t = ChronoTime("2026-03-10T11:29:00", calendar).jump(1, step="3min")
        assert t.raw_time.isoformat() == "2026-03-10T13:02:00+08:00"


def test_is_trading():
    calendar = Calendar("XSHG")
    assert ChronoTime("2026-03-10T11:29:00", calendar).is_trading_time()
    assert not ChronoTime("2026-03-10T11:30:00", calendar).is_trading_time()
    assert not ChronoTime("2026-03-10T12:59:59", calendar).is_trading_time()
    assert ChronoTime("2026-03-10T13:00:00", calendar).is_trading_time()
    assert not ChronoTime("2026-03-10T15:00:00", calendar).is_trading_time()

def test_trading_times():
    # [start, end)
    calendar = Calendar("XSHG")
    tts = ChronoTime("2026-03-10T11:29:00", calendar).trading_times_until("2026-03-10T13:00:00")
    assert len(tts) == 1

    tts = ChronoTime("2026-03-10T09:30:00", calendar).trading_times_until("2026-03-10T15:00:00")
    assert len(tts) == 240
    tts = ChronoTime("2026-03-10T09:30:00", calendar).trading_times_until("2026-03-10T14:59:00")
    assert len(tts) == 239

def test_cme_shift():
    calendar = Calendar("CME Globex Crypto")
    t1 = ChronoTime("2025-10-24T00:00:00", calendar)
    assert t1.raw_time.isoformat() == "2025-10-24T00:00:00-05:00"
    t1 = ChronoTime("2025-12-24T00:00:00", calendar)
    assert t1.raw_time.isoformat() == "2025-12-24T00:00:00-06:00"
    t1 = ChronoTime("2025-12-24T16:00:00", calendar)
    assert t1.raw_time.isoformat() == "2025-12-24T16:00:00-06:00"


def test_cme_is_trading():
    calendar = Calendar("CME Globex Crypto")
    assert not ChronoTime("2025-12-24T16:00:00", calendar).is_trading_time(), (
        "2025-12-24T16:00:00 is not a trading time"
    )
