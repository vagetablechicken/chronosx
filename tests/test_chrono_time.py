import pytest
from chronosx.calendar import Calendar
from chronosx.time import ChronoTime


def test_init():
    # use local calendar for testing
    calendar = Calendar("SSE")
    t1 = ChronoTime("2024-01-01T00:00:00", calendar)
    assert t1.raw_time.isoformat() == "2024-01-01T00:00:00+08:00"

    t1 = ChronoTime("2024-01-01T09:30:00", calendar)
    assert t1.raw_time.isoformat() == "2024-01-01T09:30:00+08:00"


def test_time_shift():
    calendar = Calendar("SSE")
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
    calendar = Calendar("SSE")
    assert ChronoTime("2026-03-10T11:29:00", calendar).is_trading_time()
    assert not ChronoTime("2026-03-10T11:30:00", calendar).is_trading_time()
    assert not ChronoTime("2026-03-10T12:59:59", calendar).is_trading_time()
    assert ChronoTime("2026-03-10T13:00:00", calendar).is_trading_time()
    assert not ChronoTime("2026-03-10T15:00:00", calendar).is_trading_time()


def test_trading_times():
    # [start, end)
    calendar = Calendar("SSE")
    tts = ChronoTime("2026-03-10T11:29:00", calendar).trading_times_until(
        "2026-03-10T13:00:00"
    )
    assert len(tts) == 1

    tts = ChronoTime("2026-03-10T09:30:00", calendar).trading_times_until(
        "2026-03-10T15:00:00"
    )
    assert len(tts) == 240
    tts = ChronoTime("2026-03-10T09:30:00", calendar).trading_times_until(
        "2026-03-10T14:59:00"
    )
    assert len(tts) == 239

def test_previous_and_next():
    calendar = Calendar("SSE")
    t1 = ChronoTime("2026-03-10T11:29:00", calendar)
    assert t1.is_trading_time()
    assert t1.previous_trading_time() == t1
    t2 = ChronoTime("2026-03-10T11:30:00", calendar)
    assert not t2.is_trading_time()
    t2 = t2.previous_trading_time()
    assert t1 == t2

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
    assert not ChronoTime("2025-12-24T16:00:00", calendar).is_trading_time()

    # cme has BTB BTIC on Bitcoin Futures London Close, but it's not in cme
    # London Boxing Day will make closed on 2025-12-26T10:00:00, but cme is opening
    assert ChronoTime("2025-12-26T10:01:00", calendar).is_trading_time()


def test_cme_trading_times():
    calendar = Calendar("CME Globex Crypto")
    # CME Globex Crypto usually closes on Fridays at 16:00 and opens on Sundays at 17:00 (Chicago time)
    # 2025-12-26 is Friday. 16:00 is the close. 2025-12-27 and 2025-12-28 are weekdays.
    start = "2025-12-26T15:58:00"
    end = "2025-12-28T17:02:00"
    tts = ChronoTime(start, calendar).trading_times_until(end)

    # Expected: 15:58, 15:59 (Friday) and 17:00, 17:01 (Sunday)
    assert len(tts) == 4
    assert tts.iloc[0].strftime("%Y-%m-%dT%H:%M") == "2025-12-26T15:58"
    assert tts.iloc[-1].strftime("%Y-%m-%dT%H:%M") == "2025-12-28T17:01"
