import time

from chronosx_quant.performance import performance, PerformanceRegistry


def test_performance():
    assert len(PerformanceRegistry._metrics) == 0

    @performance("test")
    def f1():
        time.sleep(0.1)

    for _ in range(10):
        f1()
    assert PerformanceRegistry.get_count("test") == 10
    assert 100 <= PerformanceRegistry.get_percentile("test", 0.9)
    report = PerformanceRegistry.get_report("test")
    assert "test" in report
    assert "count=10" in report

    report = PerformanceRegistry.full_report()
    # one line
    assert len(report.splitlines()) == 1
    assert "test" in report
    assert "count=10" in report
