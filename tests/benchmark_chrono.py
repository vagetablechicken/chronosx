import pytest
from chronosx.calendar import Calendar
from chronosx.time import ChronoTime


@pytest.fixture(scope="module")
def calendar():
    return Calendar("SSE")


@pytest.fixture
def t_start(calendar):
    return ChronoTime("2026-03-10T09:30:00", calendar)


def test_perf_init(benchmark, calendar):
    benchmark(ChronoTime, "2026-03-10T09:30:00", calendar)


def test_perf_jump(benchmark, t_start):
    # This triggers full schedule expansion in current implementation
    benchmark(t_start.jump, 1)


def test_perf_is_trading_time(benchmark, t_start):
    benchmark(t_start.is_trading_time)


def test_perf_trading_times_until(benchmark, t_start):
    t_end = "2026-03-10T10:30:00"
    benchmark(t_start.trading_times_until, t_end)


def test_perf_next_trading_time(benchmark, t_start):
    benchmark(t_start.next_trading_time)


def test_perf_previous_trading_time(benchmark, t_start):
    benchmark(t_start.previous_trading_time)


def test_perf_to_session_end(benchmark, t_start):
    benchmark(t_start.to_session_end)
