import pandas as pd
import pandas_market_calendars as mcal
from chronosx_quant.scheduler import SchedulerManager, StaticMinuteScheduler


def calendar_preview(calendar_name):
    with SchedulerManager.use_scheduler(StaticMinuteScheduler(calendar_name)):
        cal = SchedulerManager.get_scheduler().calendar
        print(f"---{cal.full_name}---")
        holidays = cal.holidays()
        print(f"latest holidays {holidays.kwds['holidays'][-5:]}")

        today = pd.Timestamp.now().date()
        next_month = today + pd.Timedelta(days=32)
        holidays_in_range = [
            h for h in holidays.kwds["holidays"] if h >= today and h < next_month
        ]
        print(
            f"next 32 days [{today}, {next_month}) have holidays: {holidays_in_range}"
        )


def main():
    print(
        f"dependency: pandas={pd.__version__}, pandas_market_calendars={mcal.__version__}"
    )
    calendar_preview("SSE")
    calendar_preview("CME Globex Crypto")


if __name__ == "__main__":
    main()
