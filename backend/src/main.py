import sys
from pathlib import Path

# Add src to sys.path to enable direct imports across backend modules
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fastapi import FastAPI
from api.website import route as website_router

app = FastAPI(title="Bessemer Backend API")

# Include routers
app.include_router(website_router, prefix="/api")
app.include_router(website_router)

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/health")
def health_check():
    return {"status": "ok"}