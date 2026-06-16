from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.database import engine, Base
from app.api import tasks, pages, analysis, output
from app.config import settings
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.result_dir, exist_ok=True)
    yield


app = FastAPI(
    title="Document Layout Analysis API",
    description="文档布局分析与版面还原服务",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(pages.router, prefix="/api/pages", tags=["pages"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(output.router, prefix="/api/output", tags=["output"])


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
app.mount("/results", StaticFiles(directory=settings.result_dir), name="results")
