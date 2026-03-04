from sqlalchemy.orm import Session

from app.models import SystemSetting

INTEGRATION_PREFIX = "omni_chatroom_integration"


def _integration_key(chatroom_id: int) -> str:
    return f"{INTEGRATION_PREFIX}_{chatroom_id}"


def get_chatroom_integration(db: Session, chatroom_id: int) -> dict:
    key = _integration_key(chatroom_id)
    row = db.query(SystemSetting).filter(SystemSetting.key == key).one_or_none()
    if row is None:
        return {}
    return row.value.get("value", {})


def set_chatroom_integration(db: Session, chatroom_id: int, payload: dict) -> None:
    key = _integration_key(chatroom_id)
    row = db.query(SystemSetting).filter(SystemSetting.key == key).one_or_none()
    wrapped = {"value": payload}
    if row is None:
        db.add(SystemSetting(key=key, value=wrapped))
    else:
        row.value = wrapped
    db.flush()
