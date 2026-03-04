from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import PropertyListing
from app.schemas import PropertyUpsert


class KnowledgeBaseService:
    def __init__(self, db: Session):
        self.db = db

    def sync_properties(self, properties: list[PropertyUpsert]) -> int:
        synced = 0
        for item in properties:
            row = (
                self.db.query(PropertyListing)
                .filter(PropertyListing.listing_code == item.listing_code)
                .one_or_none()
            )
            if row is None:
                row = PropertyListing(listing_code=item.listing_code)
                self.db.add(row)
            row.title = item.title
            row.district = item.district
            row.price = item.price
            row.currency = item.currency
            row.facilities = item.facilities
            row.link = item.link
            row.image_url = item.image_url
            row.is_for_rent = item.is_for_rent
            synced += 1
        self.db.commit()
        return synced

    def search_properties(self, query: str, limit: int = 3) -> list[PropertyListing]:
        cleaned = query.strip()
        if not cleaned:
            return []
        like = f"%{cleaned}%"
        return (
            self.db.query(PropertyListing)
            .filter(
                or_(
                    PropertyListing.title.ilike(like),
                    PropertyListing.district.ilike(like),
                    PropertyListing.listing_code.ilike(like),
                )
            )
            .order_by(PropertyListing.updated_at.desc())
            .limit(limit)
            .all()
        )

    def find_by_code(self, code: str) -> PropertyListing | None:
        return (
            self.db.query(PropertyListing)
            .filter(PropertyListing.listing_code == code.strip())
            .one_or_none()
        )

    @staticmethod
    def property_cards(items: list[PropertyListing]) -> list[dict]:
        cards: list[dict] = []
        for item in items:
            cards.append(
                {
                    "listing_code": item.listing_code,
                    "title": item.title,
                    "district": item.district,
                    "price": item.price,
                    "currency": item.currency,
                    "link": item.link,
                    "image_url": item.image_url,
                }
            )
        return cards

    @staticmethod
    def faq_answer(intent: str) -> str | None:
        answers = {
            "mortgage": "按揭方面可按你的首期、收入及供款比率初步估算。你可提供預算與入息，我哋即刻幫你計。",
            "facilities": "如你提供心儀屋苑，我可即時發送會所、交通及校網等重點設施資訊。",
            "pricing": "我可即時提供最新放盤叫價與成交參考，亦可幫你對比同區樓盤。",
        }
        return answers.get(intent)
