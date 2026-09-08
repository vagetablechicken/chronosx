from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import tzinfo
from functools import lru_cache
from typing import Any, Callable, Generator

import pandas as pd

from chronosx_quant.scheduler import SchedulerManager, StaticMinuteScheduler

_current_tz: ContextVar[str | tzinfo | None] = ContextVar("current_tz", default=None)


def _resolve_tz(target: Any) -> str | tzinfo | None:
    if target is None or isinstance(target, (str, tzinfo)):
        return target
    tz = getattr(target, "tz", getattr(getattr(target, "calendar", None), "tz", None))
    tz = tz() if callable(tz) else tz
    return tz if isinstance(tz, (str, tzinfo)) else None


def _get_effective_tz() -> str | tzinfo | None:
    if (tz := _current_tz.get()) is not None:
        return tz
    schedule = getattr(SchedulerManager._storage, "schedule", None)
    return getattr(schedule, "tz", None)


@lru_cache(maxsize=None)
def get_scheduler(calendar_name: str) -> StaticMinuteScheduler:
    return StaticMinuteScheduler(calendar_name)


@contextmanager
def use_tz(tz_or_target: Any) -> Generator[None, None, None]:
    token = _current_tz.set(_resolve_tz(tz_or_target))
    try:
        yield
    finally:
        _current_tz.reset(token)


def ts(value: Any, tz: str | tzinfo | None = None) -> pd.Timestamp:
    res = pd.Timestamp(value, tz=tz or _get_effective_tz())
    assert isinstance(res, pd.Timestamp)
    return res


def make_ts(tz_or_target: Any = None) -> Callable[[Any], pd.Timestamp]:
    target_tz = _resolve_tz(tz_or_target)
    return lambda val, override_tz=None: ts(val, tz=override_tz or target_tz)
