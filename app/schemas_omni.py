from datetime import datetime

from pydantic import BaseModel, Field


CHANNEL_PATTERN = r"^(whatsapp|wechat|facebook|instagram)$"


class OmniChatroomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    channel: str = Field(pattern=CHANNEL_PATTERN)
    external_room_id: str = Field(min_length=1, max_length=120)
    ai_enabled: bool = True
    ai_schedule_start: str = Field(default="00:00", pattern=r"^\d{2}:\d{2}$")
    ai_schedule_end: str = Field(default="00:00", pattern=r"^\d{2}:\d{2}$")
    timezone: str = "Asia/Hong_Kong"


class OmniChatroomRead(BaseModel):
    id: int
    name: str
    channel: str
    external_room_id: str
    ai_enabled: bool
    ai_schedule_start: str
    ai_schedule_end: str
    timezone: str
    thread_count: int = 0
    updated_at: datetime


class OmniChatroomAIStatusUpdate(BaseModel):
    enabled: bool


class OmniChatroomAIScheduleUpdate(BaseModel):
    ai_schedule_start: str = Field(pattern=r"^\d{2}:\d{2}$")
    ai_schedule_end: str = Field(pattern=r"^\d{2}:\d{2}$")
    timezone: str = "Asia/Hong_Kong"


class OmniChatroomAIStatusRead(BaseModel):
    chatroom_id: int
    ai_enabled: bool
    ai_schedule_start: str
    ai_schedule_end: str
    timezone: str


class OmniThreadRead(BaseModel):
    id: int
    chatroom_id: int
    contact_channel: str
    contact_external_user_id: str
    contact_display_name: str | None = None
    status: str
    assigned_agent_name: str | None = None
    last_message_at: datetime
    last_message_preview: str | None = None


class OmniMessageRead(BaseModel):
    id: int
    thread_id: int
    direction: str
    sender_type: str
    content: str
    created_at: datetime


class OmniSendMessage(BaseModel):
    content: str = Field(min_length=1)
    sender_type: str = Field(default="agent", pattern=r"^(agent|system)$")


class OmniIncomingMessage(BaseModel):
    channel: str = Field(pattern=CHANNEL_PATTERN)
    chatroom_external_id: str = Field(min_length=1, max_length=120)
    contact_id: str = Field(min_length=1, max_length=120)
    contact_name: str | None = None
    text: str = Field(min_length=1)
    metadata: dict = Field(default_factory=dict)


class OmniInboundResult(BaseModel):
    chatroom_id: int
    chatroom_name: str
    channel: str
    thread_id: int
    contact_id: str
    ai_replied: bool
    reply_text: str | None = None


class OmniIntegrationRead(BaseModel):
    chatroom_id: int
    phone_number_id: str | None = None
    webhook_verify_token_set: bool
    whatsapp_access_token_set: bool
    openai_api_key_set: bool
    openai_model: str = "gpt-4o-mini"
    ai_provider: str = "rule_based"


class OmniIntegrationUpdate(BaseModel):
    phone_number_id: str | None = None
    webhook_verify_token: str | None = None
    whatsapp_access_token: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    ai_provider: str | None = Field(default=None, pattern=r"^(rule_based|openai)$")
