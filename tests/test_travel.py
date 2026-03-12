from chronosx.time import ChronoTime
from chronosx.mock import travel


def test_travel():
    with travel(ChronoTime("2026-03-10T09:30:00")):
        assert ChronoTime.now().raw_time.isoformat() == "2026-03-10T09:30:00+08:00"
        assert ChronoTime.now().is_trading_time()

    with travel("2026-03-10T09:30:00"):
        assert ChronoTime.now().raw_time.isoformat() == "2026-03-10T09:30:00+08:00"
    
    with travel("2026-03-10T09:30:00-05:00"):
        assert ChronoTime.now().raw_time.isoformat() == "2026-03-10T09:30:00-05:00"
