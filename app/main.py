from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app import database
from app.database import Base, SessionLocal
from app.models import Agent, OmniChatroom, PropertyListing  # noqa: F401 - ensure model registration
from app.routers.admin import router as admin_router
from app.routers.crm import router as crm_router
from app.routers.omni import router as omni_router
from app.routers.webhooks import router as webhooks_router
from app.services.settings_service import ensure_default_settings


def _seed_initial_data() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        ensure_default_settings(db, settings)
        has_agent = db.query(Agent).first()
        if not has_agent:
            db.add(
                Agent(
                    name="House 88 Duty Agent",
                    phone="+85200000000",
                    specialties="default",
                    is_active=True,
                )
            )
            db.commit()

        default_rooms = [
            ("whatsapp", "house88-whatsapp", "WhatsApp Main"),
            ("wechat", "house88-wechat", "WeChat Official"),
            ("facebook", "house88-facebook", "Facebook Page Inbox"),
            ("instagram", "house88-instagram", "Instagram DM Inbox"),
        ]
        changed = False
        for channel, external_room_id, name in default_rooms:
            exists = (
                db.query(OmniChatroom)
                .filter(
                    OmniChatroom.channel == channel,
                    OmniChatroom.external_room_id == external_room_id,
                )
                .one_or_none()
            )
            if exists is None:
                db.add(
                    OmniChatroom(
                        name=name,
                        channel=channel,
                        external_room_id=external_room_id,
                        ai_enabled=True,
                        ai_schedule_start="00:00",
                        ai_schedule_end="00:00",
                        timezone=settings.default_timezone,
                    )
                )
                changed = True
        if changed:
            db.commit()


def create_app(database_url: str | None = None) -> FastAPI:
    settings = get_settings()
    if database_url:
        database.reconfigure_engine(database_url)
    Base.metadata.create_all(bind=database.engine)
    _seed_initial_data()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="House 88 Omnichannel Chatroom (WhatsApp/WeChat/Facebook/IG) with per-chatroom AI controls",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    app.include_router(webhooks_router)
    app.include_router(omni_router)
    app.include_router(admin_router)
    app.include_router(crm_router)
    return app


app = create_app()
