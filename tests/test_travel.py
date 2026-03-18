from zoneinfo import ZoneInfo

from chronosx.time import ChronoTime
from chronosx.mock import travel


def test_travel():
    with travel(ChronoTime("2026-03-10T09:30:00")):
        assert ChronoTime.now().isoformat() == "2026-03-10T09:30:00+08:00"
        assert ChronoTime.now().is_trading()

    with travel("2026-03-10T09:30:00"):
        assert ChronoTime.now().isoformat() == "2026-03-10T09:30:00+08:00"

    with travel("2026-03-10T09:30:00-05:00"):
        # tz will change to default named tz
        assert ChronoTime.now().isoformat() == "2026-03-10T22:30:00+08:00"
        assert ChronoTime.now().tz == ZoneInfo("Asia/Shanghai")
