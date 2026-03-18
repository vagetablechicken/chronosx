# Chronosx

A Python library for working with time intervals and chronological data.

## Installation

```bash
uv build
pip install dist/chronosx-0.2.0-py3-none-any.whl
# haven't upload to pypi
# pip install chronosx
```

## Usage

```python
from chronosx.time import ChronoTime
# use CALENDAR_NAME to select default calendar, e.g. SSE
time = ChronoTime.now()
time = ChronoTime("2026-03-08 11:29:00+08:00")

# time about trading, only support 1min step now
time.is_trading()
# move 2 steps forward(2min), auto skip breaks and weekends
# e.g. 2026-03-08 11:29:00+08:00" -> "2026-03-08 13:01:00+08:00"
time.shift(2)
# select valid trading times from self to end
# return series of 2 items, 11:29:00 and 13:00:00
time.trading_times(end=pd.Timestamp("2026-03-08 13:01:00+08:00"))
# move to the beginning of trading session which the time belongs to
# e.g. SSE "2026-03-08 11:29:00+08:00" belongs to session '2026-03-08', so the session start is '2026-03-08 09:30:00+08:00'
# e.g. CME session '2026-03-08' starts from '2026-03-07 17:00:00-06:00', so the session start is '2026-03-07 17:00:00-06:00', not '2026-03-08 00:00:00+00:00'
time.to_session_start()
```

### Add calendar

Chronosx based on pandas_market_calendars, so it can use all calendars in the project, and support to add custom calendars.

### Add scheduler

I use static minute scheduler for speed, don't support multi step in the same time, and don't support extend schedule time range. It's ok to add new scheduler to support multi step or dynamic time range.
