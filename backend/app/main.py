from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.infrastructure.database import engine, Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Energy Revenue Settlement API")

from app.adapters.controllers.routes import router

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.on_event("startup")
async def startup():
    logger.info("Starting up FastAPI application...")
    # Normally we'd use Alembic, but since it's hard to run migrations locally without MS SQL,
    # we can try to do a create_all as a fallback if desired. However, the plan states
    # alembic handles migrations. We leave this as is.
    pass

@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok"}
