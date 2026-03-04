from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class IncomingMessage(BaseModel):
    channel: str = "whatsapp"
    phone: str
    name: str | None = None
    text: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime | None = None


class WebhookProcessResponse(BaseModel):
    mode: str
    customer_phone: str
    ai_replied: bool
    handover: bool = False
    assigned_agent: str | None = None
    reply_text: str | None = None
    tags: list[str] = Field(default_factory=list)


class AIStatus(BaseModel):
    enabled: bool
    schedule_start: str
    schedule_end: str
    timezone: str


class AIStatusUpdate(BaseModel):
    enabled: bool


class AIScheduleUpdate(BaseModel):
    schedule_start: str = Field(pattern=r"^\d{2}:\d{2}$")
    schedule_end: str = Field(pattern=r"^\d{2}:\d{2}$")
    timezone: str = "Asia/Hong_Kong"


class AgentCreate(BaseModel):
    name: str
    phone: str
    specialties: str | None = None
    is_active: bool = True


class AgentRead(BaseModel):
    id: int
    name: str
    phone: str
    specialties: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class PropertyUpsert(BaseModel):
    listing_code: str
    title: str
    district: str
    price: int | None = None
    currency: str = "HKD"
    facilities: list[str] | None = None
    link: str | None = None
    image_url: str | None = None
    is_for_rent: bool = False


class PropertySyncResponse(BaseModel):
    synced: int


class TagUpdate(BaseModel):
    tags: list[str]


class BookingCreate(BaseModel):
    phone: str
    scheduled_at: datetime
    property_code: str | None = None
    notes: str | None = None
    channel: str = "whatsapp"


class BookingRead(BaseModel):
    id: int
    customer_phone: str
    scheduled_at: datetime
    status: str
    channel: str
    notes: str | None = None
    agent_name: str | None = None
    property_code: str | None = None


class LeadReportRead(BaseModel):
    id: int
    created_at: datetime
    summary_json: dict[str, Any]
    agent_name: str | None = None


class CustomerDetail(BaseModel):
    phone: str
    name: str | None = None
    intent_stage: str
    follow_up_status: str
    budget_min: int | None = None
    budget_max: int | None = None
    tags: list[str]


class LeadListItem(BaseModel):
    phone: str
    name: str | None = None
    intent_stage: str
    follow_up_status: str
    tags: list[str] = Field(default_factory=list)
    last_message: str | None = None
    last_message_at: datetime | None = None


class AIFeedbackCreate(BaseModel):
    phone: str
    label: str = Field(pattern=r"^(correct|improve)$")
    note: str | None = None
    message_id: int | None = None
