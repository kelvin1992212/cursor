from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Agent, Customer, LeadReport
from app.schemas import (
    AIStatus,
    AIScheduleUpdate,
    AIStatusUpdate,
    AgentCreate,
    AgentRead,
    LeadReportRead,
    PropertySyncResponse,
    PropertyUpsert,
)
from app.services.knowledge_base import KnowledgeBaseService
from app.services.settings_service import (
    AI_ENABLED_KEY,
    AI_SCHEDULE_KEY,
    get_setting,
    set_setting,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _ai_status(db: Session) -> AIStatus:
    settings = get_settings()
    schedule_default = {
        "start": settings.default_ai_schedule_start,
        "end": settings.default_ai_schedule_end,
        "timezone": settings.default_timezone,
    }
    schedule = get_setting(db, AI_SCHEDULE_KEY, schedule_default)
    enabled = bool(get_setting(db, AI_ENABLED_KEY, settings.default_ai_enabled))
    if not isinstance(schedule, dict):
        schedule = schedule_default
    return AIStatus(
        enabled=enabled,
        schedule_start=str(schedule.get("start", settings.default_ai_schedule_start)),
        schedule_end=str(schedule.get("end", settings.default_ai_schedule_end)),
        timezone=str(schedule.get("timezone", settings.default_timezone)),
    )


@router.get("/ai/status", response_model=AIStatus)
def get_ai_status(db: Session = Depends(get_db)) -> AIStatus:
    return _ai_status(db)


@router.put("/ai/status", response_model=AIStatus)
def update_ai_status(payload: AIStatusUpdate, db: Session = Depends(get_db)) -> AIStatus:
    set_setting(db, AI_ENABLED_KEY, payload.enabled)
    db.commit()
    return _ai_status(db)


@router.post("/ai/pause", response_model=AIStatus)
def pause_ai(db: Session = Depends(get_db)) -> AIStatus:
    set_setting(db, AI_ENABLED_KEY, False)
    db.commit()
    return _ai_status(db)


@router.put("/ai/schedule", response_model=AIStatus)
def update_ai_schedule(payload: AIScheduleUpdate, db: Session = Depends(get_db)) -> AIStatus:
    set_setting(
        db,
        AI_SCHEDULE_KEY,
        {
            "start": payload.schedule_start,
            "end": payload.schedule_end,
            "timezone": payload.timezone,
        },
    )
    db.commit()
    return _ai_status(db)


@router.post("/agents", response_model=AgentRead)
def create_agent(payload: AgentCreate, db: Session = Depends(get_db)) -> Agent:
    existing = db.query(Agent).filter(Agent.phone == payload.phone).one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Agent phone already exists.")
    row = Agent(
        name=payload.name,
        phone=payload.phone,
        specialties=payload.specialties,
        is_active=payload.is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/agents", response_model=list[AgentRead])
def list_agents(db: Session = Depends(get_db)) -> list[Agent]:
    return db.query(Agent).order_by(Agent.id.asc()).all()


@router.post("/properties/sync", response_model=PropertySyncResponse)
def sync_properties(payload: list[PropertyUpsert], db: Session = Depends(get_db)) -> PropertySyncResponse:
    synced = KnowledgeBaseService(db).sync_properties(payload)
    return PropertySyncResponse(synced=synced)


@router.get("/reports/{phone}", response_model=list[LeadReportRead])
def customer_reports(phone: str, db: Session = Depends(get_db)) -> list[LeadReportRead]:
    customer = db.query(Customer).filter(Customer.phone == phone).one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")

    rows = (
        db.query(LeadReport)
        .filter(LeadReport.customer_id == customer.id)
        .order_by(LeadReport.created_at.desc())
        .all()
    )
    result: list[LeadReportRead] = []
    for row in rows:
        result.append(
            LeadReportRead(
                id=row.id,
                created_at=row.created_at,
                summary_json=row.summary_json,
                agent_name=row.agent.name if row.agent else None,
            )
        )
    return result
