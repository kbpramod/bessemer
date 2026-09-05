import sys
import logging
from contextlib import asynccontextmanager
from pathlib import Path

# Add src to sys.path to enable direct imports across backend modules
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.website import route as website_router
from api.cron import router as cron_router
from api.onboarding import router as onboarding_router
from db.migrations import init_db

logger = logging.getLogger("forge.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run database migrations automatically on server boot
    try:
        applied = init_db()
        if applied:
            logger.info(f"Database migrations applied on startup: {applied}")
        else:
            logger.info("Database schema is up to date.")
    except Exception as e:
        logger.error(f"Failed to run database migrations on startup: {e}")
    yield


app = FastAPI(title="Bessemer Backend API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(website_router, prefix="/api")
app.include_router(website_router)
app.include_router(onboarding_router, prefix="/api")
app.include_router(onboarding_router)
app.include_router(cron_router, prefix="/api")




@app.get("/")
def read_root():
    return {"message": "Hello World"}


@app.get("/health")
def health_check():
    return {"status": "ok"}