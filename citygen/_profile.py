import contextlib
import os
import time

_ENABLED = os.environ.get("CITYGEN_PROFILE") == "1"
_STAGES: dict[str, float] = {}

@contextlib.contextmanager
def stage(name: str):
    if not _ENABLED:
        yield
        return
    t0 = time.perf_counter()
    try:
        yield
    finally:
        _STAGES[name] = _STAGES.get(name, 0.0) + (time.perf_counter() - t0)

def results() -> dict[str, float]:
    return dict(_STAGES)

def reset() -> None:
    _STAGES.clear()
