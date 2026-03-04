from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CustomerTag(Base):
    __tablename__ = "customer_tags"

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    preferred_channel: Mapped[str] = mapped_column(String(20), default="whatsapp", nullable=False)
    intent_stage: Mapped[str] = mapped_column(String(50), default="new", nullable=False)
    follow_up_status: Mapped[str] = mapped_column(String(50), default="new", nullable=False)
    budget_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    budget_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
    )

    messages: Mapped[list["ConversationMessage"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    tags: Mapped[list["Tag"]] = relationship(
        secondary="customer_tags",
        back_populates="customers",
    )
    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    assignments: Mapped[list["LeadAssignment"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    reports: Mapped[list["LeadReport"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    feedback: Mapped[list["AIFeedback"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    customers: Mapped[list[Customer]] = relationship(
        secondary="customer_tags",
        back_populates="tags",
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"))
    direction: Mapped[str] = mapped_column(String(20), nullable=False)  # inbound/outbound
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # whatsapp/wechat
    content: Mapped[str] = mapped_column(Text, nullable=False)
    interactive_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    handled_by: Mapped[str] = mapped_column(String(20), default="ai", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    customer: Mapped[Customer] = relationship(back_populates="messages")
    feedback: Mapped[list["AIFeedback"]] = relationship(back_populates="message")


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    specialties: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    assignments: Mapped[list["LeadAssignment"]] = relationship(back_populates="agent")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="agent")
    reports: Mapped[list["LeadReport"]] = relationship(back_populates="agent")


class LeadAssignment(Base):
    __tablename__ = "lead_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"))
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"))
    reason: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    customer: Mapped[Customer] = relationship(back_populates="assignments")
    agent: Mapped[Agent] = relationship(back_populates="assignments")


class PropertyListing(Base):
    __tablename__ = "property_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    district: Mapped[str] = mapped_column(String(120), nullable=False)
    price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="HKD", nullable=False)
    facilities: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_for_rent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
    )

    bookings: Mapped[list["Booking"]] = relationship(back_populates="property")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"))
    property_id: Mapped[int | None] = mapped_column(
        ForeignKey("property_listings.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_id: Mapped[int | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    channel: Mapped[str] = mapped_column(String(20), default="whatsapp", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    customer: Mapped[Customer] = relationship(back_populates="bookings")
    property: Mapped[PropertyListing | None] = relationship(back_populates="bookings")
    agent: Mapped[Agent | None] = relationship(back_populates="bookings")


class LeadReport(Base):
    __tablename__ = "lead_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"))
    agent_id: Mapped[int | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    customer: Mapped[Customer] = relationship(back_populates="reports")
    agent: Mapped[Agent | None] = relationship(back_populates="reports")


class AIFeedback(Base):
    __tablename__ = "ai_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"))
    message_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversation_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    label: Mapped[str] = mapped_column(String(40), nullable=False)  # correct / improve
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    customer: Mapped[Customer] = relationship(back_populates="feedback")
    message: Mapped[ConversationMessage | None] = relationship(back_populates="feedback")


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
    )


class OmniChatroom(Base):
    __tablename__ = "omni_chatrooms"
    __table_args__ = (UniqueConstraint("channel", "external_room_id", name="uq_omni_chatroom_channel_external"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    external_room_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ai_schedule_start: Mapped[str] = mapped_column(String(5), default="00:00", nullable=False)
    ai_schedule_end: Mapped[str] = mapped_column(String(5), default="00:00", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Hong_Kong", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    threads: Mapped[list["OmniThread"]] = relationship(
        back_populates="chatroom",
        cascade="all, delete-orphan",
    )


class OmniContact(Base):
    __tablename__ = "omni_contacts"
    __table_args__ = (UniqueConstraint("channel", "external_user_id", name="uq_omni_contact_channel_external"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    external_user_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    threads: Mapped[list["OmniThread"]] = relationship(
        back_populates="contact",
        cascade="all, delete-orphan",
    )


class OmniThread(Base):
    __tablename__ = "omni_threads"
    __table_args__ = (UniqueConstraint("chatroom_id", "contact_id", name="uq_omni_thread_room_contact"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chatroom_id: Mapped[int] = mapped_column(ForeignKey("omni_chatrooms.id", ondelete="CASCADE"), index=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("omni_contacts.id", ondelete="CASCADE"), index=True)
    assigned_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    chatroom: Mapped[OmniChatroom] = relationship(back_populates="threads")
    contact: Mapped[OmniContact] = relationship(back_populates="threads")
    assigned_agent: Mapped[Agent | None] = relationship()
    messages: Mapped[list["OmniMessage"]] = relationship(
        back_populates="thread",
        cascade="all, delete-orphan",
    )


class OmniMessage(Base):
    __tablename__ = "omni_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("omni_threads.id", ondelete="CASCADE"), index=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)  # inbound / outbound
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)  # customer / ai / agent / system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)

    thread: Mapped[OmniThread] = relationship(back_populates="messages")
