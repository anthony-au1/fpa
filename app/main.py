from collections.abc import Generator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.api import routes
from app.config import Settings, get_settings
from app.persistence import tables
from app.persistence.database import create_database_engine, create_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    engine = create_database_engine(active_settings.database_url)
    session_factory = create_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        tables.Base.metadata.create_all(engine)
        yield
        engine.dispose()

    application = FastAPI(
        title="Financial Processing Agent",
        version="0.1.0",
        lifespan=lifespan,
    )

    def get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    application.dependency_overrides[routes.get_session] = get_session
    application.include_router(routes.router)
    return application


app = create_app()
