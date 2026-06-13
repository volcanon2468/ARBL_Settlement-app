from app.api.auth import router as auth_router
from app.adapters.controllers.routes import router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.infrastructure.database import engine, Base
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI(title="Energy Revenue Settlement API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(router)


@app.on_event("startup")
async def startup():
    logger.info("Starting up FastAPI application...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized successfully.")


@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok"}
