import pandas as pd
from chronosx.calendar import Calendar


def calendar_preview(calendar_name):
    cal = Calendar(calendar_name)
    print(f"---{cal.calendar.full_name}---")
    holidays = cal.calendar.holidays()
    print(f"latest holidays {holidays.kwds['holidays'][-5:]}")

    today = pd.Timestamp.now().date()
    next_month = today + pd.Timedelta(days=32)
    holidays_in_range = [
        h for h in holidays.kwds["holidays"] if h >= today and h < next_month
    ]
    print(f"next 32 days [{today}, {next_month}) have holidays: {holidays_in_range}")


def main():
    calendar_preview("SSE")
    calendar_preview("CME Globex Crypto")


if __name__ == "__main__":
    main()
