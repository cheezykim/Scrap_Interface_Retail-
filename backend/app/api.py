"""FastAPI application for submitting and monitoring scraping jobs."""

from contextlib import asynccontextmanager
from datetime import datetime
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from .config import ConfigurationError, Settings
from .jobs import JobManager, JobNotFoundError
from .scraper.sheets import GoogleSheetsWriter
from .scraper.telegram import TelegramScraper
from .scraper.validation import ScrapeInputError


def remove_dead_local_proxy() -> None:
    """Ignore Codex/local dead-end proxy values inherited by network clients."""
    dead_proxy_values = {"http://127.0.0.1:9", "https://127.0.0.1:9"}
    proxy_names = (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    )
    for name in proxy_names:
        if os.environ.get(name, "").strip().lower() in dead_proxy_values:
            os.environ.pop(name, None)


def allowed_cors_origins() -> list[str]:
    """Read allowed browser origins from env, keeping localhost for development."""
    configured = os.environ.get("BACKEND_CORS_ORIGINS", "")
    origins = [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]
    return origins or ["http://localhost:5173"]


class JobCreateRequest(BaseModel):
    links: list[str] = Field(min_length=1)
    start_date: datetime
    end_date: datetime


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    links: list[str]
    start_date: datetime
    end_date: datetime
    status: str
    progress: int
    status_message: str
    records_found: int
    rows_appended: int
    duplicates_skipped: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None
    logs: list[dict[str, Any]]


def create_app(manager: JobManager | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        active_manager = manager
        if active_manager is None:
            remove_dead_local_proxy()
            try:
                settings = Settings.from_env()
            except ConfigurationError as exc:
                raise RuntimeError(f"Backend configuration error: {exc}") from exc
            active_manager = JobManager(
                TelegramScraper(settings),
                GoogleSheetsWriter(settings),
                max_links=settings.max_links,
                timezone_name=settings.timezone,
            )

        app.state.job_manager = active_manager
        await active_manager.start()
        try:
            yield
        finally:
            await active_manager.stop()

    app = FastAPI(
        title="Retail Banking Scraper API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/api/health")
    async def health(request: Request) -> dict[str, str]:
        return {"status": "ok", "worker": "ready"}

    @app.post(
        "/api/jobs",
        response_model=JobResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def create_job(payload: JobCreateRequest, request: Request):
        try:
            job = await request.app.state.job_manager.submit(
                payload.links, payload.start_date, payload.end_date
            )
        except ScrapeInputError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return job.as_dict()

    @app.get("/api/jobs/{job_id}", response_model=JobResponse)
    async def get_job(job_id: str, request: Request):
        try:
            return request.app.state.job_manager.get(job_id).as_dict()
        except JobNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Job not found.") from exc

    return app


app = create_app()
