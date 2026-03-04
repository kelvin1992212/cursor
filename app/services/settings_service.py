from datetime import datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import SystemSetting

AI_ENABLED_KEY = "ai_enabled"
AI_SCHEDULE_KEY = "ai_schedule"
RR_COUNTER_KEY = "round_robin_agent_index"


def _time_from_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(hour=int(hour), minute=int(minute))


def get_setting(db: Session, key: str, default: dict | bool | int) -> dict | bool | int:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).one_or_none()
    if row is None:
        return default
    return row.value.get("value", default)


def set_setting(db: Session, key: str, value: dict | bool | int) -> None:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).one_or_none()
    payload = {"value": value}
    if row is None:
        row = SystemSetting(key=key, value=payload)
        db.add(row)
    else:
        row.value = payload
    db.flush()


def ensure_default_settings(db: Session, settings: Settings) -> None:
    defaults: dict[str, dict | bool | int] = {
        AI_ENABLED_KEY: settings.default_ai_enabled,
        AI_SCHEDULE_KEY: {
            "start": settings.default_ai_schedule_start,
            "end": settings.default_ai_schedule_end,
            "timezone": settings.default_timezone,
        },
        RR_COUNTER_KEY: 0,
    }
    changed = False
    for key, value in defaults.items():
        existing = db.query(SystemSetting).filter(SystemSetting.key == key).one_or_none()
        if existing is None:
            db.add(SystemSetting(key=key, value={"value": value}))
            changed = True
    if changed:
        db.commit()


def is_ai_available_now(db: Session, settings: Settings, now: datetime | None = None) -> bool:
    enabled = bool(get_setting(db, AI_ENABLED_KEY, settings.default_ai_enabled))
    if not enabled:
        return False

    schedule_default = {
        "start": settings.default_ai_schedule_start,
        "end": settings.default_ai_schedule_end,
        "timezone": settings.default_timezone,
    }
    schedule = get_setting(db, AI_SCHEDULE_KEY, schedule_default)
    if not isinstance(schedule, dict):
        return enabled

    start_str = str(schedule.get("start", settings.default_ai_schedule_start))
    end_str = str(schedule.get("end", settings.default_ai_schedule_end))
    timezone = str(schedule.get("timezone", settings.default_timezone))

    tz = ZoneInfo(timezone)
    current = now.astimezone(tz) if now else datetime.now(tz)
    current_time = current.time()
    start = _time_from_hhmm(start_str)
    end = _time_from_hhmm(end_str)

    if start == end:
        return True
    if start < end:
        return start <= current_time < end
    return current_time >= start or current_time < end
