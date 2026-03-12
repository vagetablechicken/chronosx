import time

from chronosx.performance import PerformanceRegistry, performance
from chronosx.mock import travel


def test_single_function():
    @performance()
    def f1():
        time.sleep(0.001)

    @performance()
    def f2():
        time.sleep(0.001)

    times = 1000
    for _ in range(times):
        f1()
        f2()

    print(PerformanceRegistry.full_report())


def test_in_travel():
    with travel("2026-03-10T09:30:00"):

        @performance("f1")
        def f1():
            time.sleep(0.001)

        times = 1000
        for _ in range(times):
            f1()
        assert PerformanceRegistry.get_count("f1") == times
        # travel won't effect perf_counter
        assert PerformanceRegistry.get_percentile("f1", 0.5) > 0

    print(PerformanceRegistry.full_report())
