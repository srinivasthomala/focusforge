from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import logs, dashboard, summary, api_keys
from app.database import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="FocusForge API",
    description="Backend API for FocusForge productivity tool",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(logs.router, tags=["logs"])
app.include_router(dashboard.router, tags=["dashboard"])
app.include_router(summary.router, tags=["summary"])
app.include_router(api_keys.router)


@app.get("/")
async def root():
    return {
        "message": "FocusForge API",
        "version": "0.1.0",
        "docs": "/docs",
    }


