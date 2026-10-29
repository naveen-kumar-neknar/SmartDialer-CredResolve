from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import (
    agents,
    borrowers,
    calls,
    dialer,
    safety,
    providers,
    demo,
    auth,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database tables on startup
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="SmartDialer Telephony API",
    description=(
        "Production-grade Telephony Progressive & Predictive Dialer engine with "
        "autonomous Safety Controller, state machine validation, and fault-tolerant event processing."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoint
@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "app": "SmartDialer",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# Include functional domain routers
app.include_router(agents.router)
app.include_router(borrowers.router)
app.include_router(calls.router)
app.include_router(dialer.router)
app.include_router(safety.router)
app.include_router(providers.router)
app.include_router(demo.router)
app.include_router(auth.router)
