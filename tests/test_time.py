import pytest
from chronosx_quant.time import ChronoTime
from chronosx_quant.scheduler import StaticMinuteScheduler, SchedulerManager


def test_init():
    t1 = ChronoTime("2024-01-01T00:00:00")
    assert t1.isoformat() == "2024-01-01T00:00:00+08:00"

    with SchedulerManager.use_scheduler(StaticMinuteScheduler("SSE")):
        t1 = ChronoTime("2024-01-01T09:30:00")
        assert t1.isoformat() == "2024-01-01T09:30:00+08:00"


def test_time_shift():
    with pytest.raises(KeyError):
        # left is not a trading time
        ChronoTime("2026-01-01T00:00:00").shift(1, step="1min")

    t = ChronoTime("2026-03-10T09:30:00").shift(1, step="1min")
    assert t.isoformat() == "2026-03-10T09:31:00+08:00"

    t = ChronoTime("2026-03-10T11:29:00").shift(3, step="1min")
    assert t.isoformat() == "2026-03-10T13:02:00+08:00"
    t = ChronoTime("2026-03-10T11:29:00").shift(3)  # default step is 1min
    assert t.isoformat() == "2026-03-10T13:02:00+08:00"

    # if step is 3, t may not be a valid time in 3min step trading time series NOTE: don't support it
    with pytest.raises(ValueError):
        t = ChronoTime("2026-03-10T11:29:00").shift(1, step="3min")
        assert t.isoformat() == "2026-03-10T13:02:00+08:00"

    t = ChronoTime("2026-03-10T11:29:03.1234").shift(-1, step="1min")
    assert t.isoformat() == "2026-03-10T11:28:03.123400+08:00"
    t = ChronoTime("2026-03-10T11:29:03.1234").shift(1, step="1min")
    assert t.isoformat() == "2026-03-10T13:00:03.123400+08:00"


def test_is_trading():
    assert ChronoTime("2026-03-10T11:29:00").is_trading()
    assert not ChronoTime("2026-03-10T11:30:00").is_trading()
    assert not ChronoTime("2026-03-10T12:59:59").is_trading()
    assert ChronoTime("2026-03-10T13:00:00").is_trading()
    assert not ChronoTime("2026-03-10T15:00:00").is_trading()

    assert ChronoTime("2026-03-10T00:30:00").is_trading_day()
    assert ChronoTime("2026-03-10T20:30:00").is_trading_day()
    assert not ChronoTime("2026-03-15T09:30:00").is_trading_day()


def test_trading_times():
    # [start, end)
    tts = ChronoTime("2026-03-10T11:29:00").trading_times("2026-03-10T13:00:00")
    assert len(tts) == 1

    tts = ChronoTime("2026-03-10T09:30:00").trading_times("2026-03-10T15:00:00")
    assert len(tts) == 240
    tts = ChronoTime("2026-03-10T09:30:00").trading_times("2026-03-10T14:59:00")
    assert len(tts) == 239

    days = tts.resample("D").first().dt.date
    assert len(days) == 1


def test_trading_day_delta():
    # Intraday time does not matter within the same trading date.
    assert (
        ChronoTime("2026-03-10T09:30:00").trading_day_delta("2026-03-10T14:59:00")
        == 1
    )
    assert (
        ChronoTime("2026-03-10T00:01:00").trading_day_delta("2026-03-10T23:59:00")
        == 1
    )

    # Crossing consecutive trading dates counts each endpoint date inclusively.
    assert (
        ChronoTime("2026-03-10T11:29:00").trading_day_delta("2026-03-12T13:00:00")
        == 3
    )
    assert (
        ChronoTime("2026-03-10T08:00:00").trading_day_delta("2026-03-12T20:00:00")
        == 3
    )

    # Weekend dates are skipped, so Friday to Monday spans two trading days.
    assert (
        ChronoTime("2026-03-13T14:59:00").trading_day_delta("2026-03-16T09:30:00")
        == 2
    )
    assert (
        ChronoTime("2026-03-13T20:00:00").trading_day_delta("2026-03-16T08:00:00")
        == 2
    )

    # Reversing direction keeps the magnitude and flips the sign.
    assert (
        ChronoTime("2026-03-16T09:30:00").trading_day_delta("2026-03-13T14:59:00")
        == -2
    )
    assert (
        ChronoTime("2026-03-16T20:00:00").trading_day_delta("2026-03-13T08:00:00")
        == -2
    )

    # Non-trading dates contribute zero unless the interval also includes a trading date.
    assert (
        ChronoTime("2026-03-15T09:30:00").trading_day_delta("2026-03-15T14:59:00")
        == 0
    )
    assert (
        ChronoTime("2026-03-15T00:01:00").trading_day_delta("2026-03-16T00:01:00")
        == 1
    )
    assert (
        ChronoTime("2026-03-14T12:00:00").trading_day_delta("2026-03-15T12:00:00")
        == 0
    )


def test_previous_and_next():
    t1 = ChronoTime("2026-03-10T11:29:00")
    assert t1.is_trading()
    assert t1.previous_trading_time() == t1
    t2 = ChronoTime("2026-03-10T11:30:00")
    assert not t2.is_trading()
    t2 = t2.previous_trading_time()
    assert t1 == t2


def test_session_start_and_end():
    t1 = ChronoTime("2026-03-10T11:29:00")
    assert t1.is_trading()
    t2 = t1.to_session_end()
    # session_end is not in trading time, to avoid 24 hour trading
    assert not t2.is_trading()
    assert t2.isoformat() == "2026-03-10T15:00:00+08:00"
    t3 = t1.to_session_start()
    assert t3.is_trading()
    assert t3.isoformat() == "2026-03-10T09:30:00+08:00"

    assert str(t1) == "2026-03-10 11:29:00+08:00"


def test_operator():
    t1 = ChronoTime("2026-03-10T11:29:00")
    t2 = ChronoTime("2026-03-10T11:30:00")
    assert t1 < t2
    assert t1 <= t2
    assert t2 > t1
    assert t2 >= t1
    assert t1 != t2
    assert t1 == ChronoTime("2026-03-10T11:29:00")
    assert (t1 - t2).total_seconds() == -60


def test_cme_specials():
    with SchedulerManager.use_scheduler(StaticMinuteScheduler("CME Globex Crypto")):
        t1 = ChronoTime("2025-10-24T00:00:00")
        assert t1.isoformat() == "2025-10-24T00:00:00-05:00"
        t1 = ChronoTime("2025-12-24T00:00:00")
        assert t1.isoformat() == "2025-12-24T00:00:00-06:00"
        t1 = ChronoTime("2025-12-24T16:00:00")
        assert t1.isoformat() == "2025-12-24T16:00:00-06:00"

        assert not ChronoTime("2025-12-24T16:00:00").is_trading()
        assert not ChronoTime("2025-12-24 21:00:00+00:00").is_trading()
        assert ChronoTime("2025-12-25 17:00:00-06:00").is_trading()
        assert ChronoTime("2025-12-25 23:00:00+00:00").is_trading()

        # cme has BTB BTIC on Bitcoin Futures London Close, but it's not in cme
        # London Boxing Day will make closed on 2025-12-26T10:00:00, but cme is opening
        assert ChronoTime("2025-12-26T10:01:00").is_trading()

        # sunday will open for monday trading day
        assert ChronoTime("2025-12-07T15:58:00").is_trading_day()
        # date is in trading
        assert ChronoTime("2025-12-08T16:30:00").is_trading_day()

        # CME Globex Crypto usually closes on Fridays at 16:00 and opens on Sundays at 17:00 (Chicago time)
        # 2025-12-26 is Friday. 16:00 is the close. 2025-12-27 and 2025-12-28 are weekdays.
        start = "2025-12-26T15:58:00"
        end = "2025-12-28T17:02:00"
        tts = ChronoTime(start).trading_times(end)

        # Expected: 15:58, 15:59 (Friday) and 17:00, 17:01 (Sunday)
        assert len(tts) == 4
        assert tts.iloc[0].strftime("%Y-%m-%dT%H:%M") == "2025-12-26T15:58"
        assert tts.iloc[-1].strftime("%Y-%m-%dT%H:%M") == "2025-12-28T17:01"

        # not a normal market close
        t1 = ChronoTime("2025-12-24T00:00:00").to_session_end()
        assert t1.isoformat() == "2025-12-24T12:15:00-06:00"

        # Sunday afternoon belongs to the Monday trading day for CME Globex Crypto,
        # so moving within that reopened session should not change the trading-day delta.
        assert (
            ChronoTime("2025-12-07T15:58:00").trading_day_delta("2025-12-07T18:00:00")
            == 0
        )
        # Crossing from Sunday afternoon into Monday calendar time advances by one
        # trading day because the endpoints land on consecutive trading dates.
        assert (
            ChronoTime("2025-12-07T15:58:00").trading_day_delta("2025-12-08T16:30:00")
            == 1
        )
        # Friday close to Sunday reopen spans the weekend, but only one new trading
        # day appears once the market opens again on Sunday evening.
        assert (
            ChronoTime("2025-12-26T15:58:00").trading_day_delta("2025-12-28T17:02:00")
            == 1
        )
        # Sunday evening reopen and Monday daytime are consecutive trading dates.
        assert (
            ChronoTime("2025-12-28T17:00:00").trading_day_delta("2025-12-29T16:00:00")
            == 1
        )
        # After Monday's close, Tuesday's trading day is the second inclusive date
        # in the interval, so the signed delta is 2.
        assert (
            ChronoTime("2025-12-29T16:30:00").trading_day_delta("2025-12-30T10:00:00")
            == 2
        )
        # Reverse direction keeps the same magnitude and flips the sign.
        assert (
            ChronoTime("2025-12-30T10:00:00").trading_day_delta("2025-12-29T16:30:00")
            == -2
        )
