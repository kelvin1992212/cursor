from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models import Agent, Booking, Customer, PropertyListing


class CalendarService:
    def __init__(self, db: Session):
        self.db = db

    def suggest_slots(self, timezone: str = "Asia/Hong_Kong", days: int = 3) -> list[datetime]:
        now = datetime.now(ZoneInfo(timezone))
        candidate_hours = (11, 15, 19)
        slots: list[datetime] = []
        for day_offset in range(days):
            day = now + timedelta(days=day_offset)
            for hour in candidate_hours:
                slot = day.replace(hour=hour, minute=0, second=0, microsecond=0)
                if slot > now:
                    slots.append(slot)
        return slots[:6]

    def create_booking(
        self,
        customer: Customer,
        scheduled_at: datetime,
        channel: str = "whatsapp",
        property_row: PropertyListing | None = None,
        agent: Agent | None = None,
        notes: str | None = None,
    ) -> Booking:
        booking = Booking(
            customer=customer,
            property=property_row,
            agent=agent,
            scheduled_at=scheduled_at,
            channel=channel,
            notes=notes,
            status="confirmed",
        )
        self.db.add(booking)
        self.db.flush()
        return booking
