from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app import database
from app.database import Base, SessionLocal
from app.models import Agent, PropertyListing  # noqa: F401 - ensure model registration
from app.routers.admin import router as admin_router
from app.routers.crm import router as crm_router
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


def create_app(database_url: str | None = None) -> FastAPI:
    settings = get_settings()
    if database_url:
        database.reconfigure_engine(database_url)
    Base.metadata.create_all(bind=database.engine)
    _seed_initial_data()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="House 88 WhatsApp/WeChat AI Lead Engine - First Phase MVP",
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
    app.include_router(admin_router)
    app.include_router(crm_router)
    return app


app = create_app()
