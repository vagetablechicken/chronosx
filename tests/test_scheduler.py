from chronosx.scheduler import StaticMinuteScheduler


def test_init():
    # use local calendar for testing
    StaticMinuteScheduler("SSE")
    StaticMinuteScheduler("CME Globex Crypto")
