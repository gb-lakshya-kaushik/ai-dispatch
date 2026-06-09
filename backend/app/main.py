"""FastAPI application entry point."""
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables and seed if DB is empty
    Base.metadata.create_all(bind=engine)
    _auto_seed_if_empty()
    yield


def _auto_seed_if_empty():
    from app.database import SessionLocal
    from app.models.personnel import Personnel
    db = SessionLocal()
    try:
        count = db.query(Personnel).count()
        if count == 0:
            db.close()
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from data.seed import seed_database
            seed_database()
        else:
            db.close()
    except Exception:
        db.close()


app = FastAPI(
    title="AI Dispatch - Traffic Management Workforce Optimization",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root():
    return {"status": "ok", "service": "AI Dispatch Backend"}


@app.post("/api/data/reset")
def reset_data():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    from data.seed import seed_database
    seed_database()
    return {"status": "reset", "message": "Database re-seeded successfully"}
