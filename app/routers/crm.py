from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import AIFeedback, Agent, Booking, ConversationMessage, Customer, PropertyListing, Tag
from app.schemas import (
    AIFeedbackCreate,
    BookingCreate,
    BookingRead,
    CustomerDetail,
    LeadListItem,
    TagUpdate,
)
from app.services.calendar_service import CalendarService
from app.services.channel import ChannelGateway

router = APIRouter(prefix="/crm", tags=["crm"])


def _start_of_day(d: date) -> datetime:
    return datetime.combine(d, time.min)


def _end_of_day(d: date) -> datetime:
    return datetime.combine(d + timedelta(days=1), time.min)


def _customer_or_404(db: Session, phone: str) -> Customer:
    row = db.query(Customer).filter(Customer.phone == phone).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Customer not found.")
    return row


@router.get("/leads", response_model=list[LeadListItem])
def list_leads(
    tag: str | None = Query(default=None),
    property_code: str | None = Query(default=None),
    intent_stage: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[LeadListItem]:
    query = db.query(Customer)
    if tag:
        query = query.join(Customer.tags).filter(Tag.name == tag)
    if property_code:
        query = (
            query.join(Customer.bookings)
            .join(Booking.property)
            .filter(PropertyListing.listing_code == property_code)
        )
    if intent_stage:
        query = query.filter(Customer.intent_stage == intent_stage)
    if from_date:
        query = query.filter(Customer.created_at >= _start_of_day(from_date))
    if to_date:
        query = query.filter(Customer.created_at < _end_of_day(to_date))

    customers = query.distinct().order_by(Customer.updated_at.desc()).all()
    results: list[LeadListItem] = []
    for customer in customers:
        last_message = (
            db.query(ConversationMessage)
            .filter(ConversationMessage.customer_id == customer.id)
            .order_by(ConversationMessage.created_at.desc())
            .first()
        )
        results.append(
            LeadListItem(
                phone=customer.phone,
                name=customer.name,
                intent_stage=customer.intent_stage,
                follow_up_status=customer.follow_up_status,
                tags=sorted(tag.name for tag in customer.tags),
                last_message=last_message.content if last_message else None,
                last_message_at=last_message.created_at if last_message else None,
            )
        )
    return results


@router.get("/customers/{phone}", response_model=CustomerDetail)
def customer_detail(phone: str, db: Session = Depends(get_db)) -> CustomerDetail:
    customer = _customer_or_404(db, phone)
    return CustomerDetail(
        phone=customer.phone,
        name=customer.name,
        intent_stage=customer.intent_stage,
        follow_up_status=customer.follow_up_status,
        budget_min=customer.budget_min,
        budget_max=customer.budget_max,
        tags=sorted(tag.name for tag in customer.tags),
    )


@router.post("/customers/{phone}/tags", response_model=CustomerDetail)
def add_customer_tags(phone: str, payload: TagUpdate, db: Session = Depends(get_db)) -> CustomerDetail:
    customer = _customer_or_404(db, phone)
    existing_tags = {
        row.name: row
        for row in db.query(Tag).filter(Tag.name.in_(payload.tags)).all()
    }
    for tag_name in payload.tags:
        tag = existing_tags.get(tag_name)
        if tag is None:
            tag = Tag(name=tag_name)
            db.add(tag)
            db.flush()
        if tag not in customer.tags:
            customer.tags.append(tag)
    db.commit()
    db.refresh(customer)
    return customer_detail(phone, db)


@router.delete("/customers/{phone}/tags/{tag_name}", response_model=CustomerDetail)
def remove_customer_tag(phone: str, tag_name: str, db: Session = Depends(get_db)) -> CustomerDetail:
    customer = _customer_or_404(db, phone)
    customer.tags = [tag for tag in customer.tags if tag.name != tag_name]
    db.commit()
    db.refresh(customer)
    return customer_detail(phone, db)


@router.post("/bookings", response_model=BookingRead)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)) -> BookingRead:
    customer = db.query(Customer).filter(Customer.phone == payload.phone).one_or_none()
    if customer is None:
        customer = Customer(phone=payload.phone, preferred_channel=payload.channel)
        db.add(customer)
        db.flush()

    property_row = None
    if payload.property_code:
        property_row = (
            db.query(PropertyListing)
            .filter(PropertyListing.listing_code == payload.property_code)
            .one_or_none()
        )

    agent = db.query(Agent).filter(Agent.is_active.is_(True)).order_by(Agent.id.asc()).first()
    booking = CalendarService(db).create_booking(
        customer=customer,
        scheduled_at=payload.scheduled_at,
        channel=payload.channel,
        property_row=property_row,
        agent=agent,
        notes=payload.notes,
    )

    confirmation = (
        f"預約已確認：{payload.scheduled_at.strftime('%Y-%m-%d %H:%M')}。"
        "如需更改時段，請直接回覆此訊息。"
    )
    db.add(
        ConversationMessage(
            customer_id=customer.id,
            direction="outbound",
            channel=payload.channel,
            content=confirmation,
            handled_by="system",
        )
    )
    ChannelGateway(get_settings()).send_text(payload.channel, customer.phone, confirmation)
    db.commit()
    db.refresh(booking)

    return BookingRead(
        id=booking.id,
        customer_phone=customer.phone,
        scheduled_at=booking.scheduled_at,
        status=booking.status,
        channel=booking.channel,
        notes=booking.notes,
        agent_name=booking.agent.name if booking.agent else None,
        property_code=booking.property.listing_code if booking.property else None,
    )


@router.get("/bookings", response_model=list[BookingRead])
def list_bookings(db: Session = Depends(get_db)) -> list[BookingRead]:
    rows = db.query(Booking).order_by(Booking.created_at.desc()).all()
    result: list[BookingRead] = []
    for row in rows:
        result.append(
            BookingRead(
                id=row.id,
                customer_phone=row.customer.phone,
                scheduled_at=row.scheduled_at,
                status=row.status,
                channel=row.channel,
                notes=row.notes,
                agent_name=row.agent.name if row.agent else None,
                property_code=row.property.listing_code if row.property else None,
            )
        )
    return result


@router.post("/feedback")
def add_feedback(payload: AIFeedbackCreate, db: Session = Depends(get_db)) -> dict:
    customer = _customer_or_404(db, payload.phone)
    row = AIFeedback(
        customer_id=customer.id,
        message_id=payload.message_id,
        label=payload.label,
        note=payload.note,
    )
    db.add(row)
    db.commit()
    return {"status": "ok", "feedback_id": row.id}
