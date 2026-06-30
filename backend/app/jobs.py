"""Sequential scraping job lifecycle and orchestration."""

import asyncio
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol, Sequence
from uuid import uuid4

from .scraper.sheets import SheetWriteResult
from .scraper.validation import localize_date_window, normalize_telegram_links


class ScraperService(Protocol):
    async def scrape(
        self,
        links: Sequence[str],
        start: datetime,
        end: datetime,
        progress: Any = None,
    ) -> list[dict[str, Any]]: ...


class SheetWriterService(Protocol):
    def write(self, records: Sequence[dict[str, Any]]) -> SheetWriteResult: ...


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class JobLog:
    timestamp: datetime
    level: str
    message: str


@dataclass
class ScrapeJob:
    id: str
    links: list[str]
    start_date: datetime
    end_date: datetime
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    status_message: str = "Waiting for an available worker"
    records_found: int = 0
    rows_appended: int = 0
    duplicates_skipped: int = 0
    created_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    logs: list[JobLog] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class JobNotFoundError(KeyError):
    pass


class JobManager:
    """Own one FIFO worker so the shared Telegram session is never concurrent."""

    def __init__(
        self,
        scraper: ScraperService,
        writer: SheetWriterService,
        max_links: int = 100,
        timezone_name: str = "Asia/Phnom_Penh",
    ) -> None:
        self.scraper = scraper
        self.writer = writer
        self.max_links = max_links
        self.timezone_name = timezone_name
        self.jobs: dict[str, ScrapeJob] = {}
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._worker_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker(), name="scrape-worker")

    async def stop(self) -> None:
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        self._worker_task = None

    async def submit(
        self, links: Sequence[str], start_date: datetime, end_date: datetime
    ) -> ScrapeJob:
        normalized_links = normalize_telegram_links(links, self.max_links)
        start_local, end_local = localize_date_window(
            start_date, end_date, self.timezone_name
        )
        job = ScrapeJob(
            id=uuid4().hex,
            links=normalized_links,
            start_date=start_local,
            end_date=end_local,
        )
        self._log(job, "info", f"Job queued with {len(normalized_links)} link(s).")
        self.jobs[job.id] = job
        await self._queue.put(job.id)
        return job

    def get(self, job_id: str) -> ScrapeJob:
        try:
            return self.jobs[job_id]
        except KeyError as exc:
            raise JobNotFoundError(job_id) from exc

    @staticmethod
    def _log(job: ScrapeJob, level: str, message: str) -> None:
        job.logs.append(JobLog(timestamp=utc_now(), level=level, message=message))
        if len(job.logs) > 200:
            del job.logs[:-200]

    def _on_progress(self, job: ScrapeJob, event: dict[str, Any]) -> None:
        event_type = event.get("type")
        if event_type == "channel_started":
            index = int(event["channel_index"])
            total = max(int(event["total_links"]), 1)
            job.progress = 5 + int(((index - 1) / total) * 75)
            job.status_message = f"Scraping link {index} of {total}"
            self._log(job, "info", job.status_message)
        elif event_type == "batch_completed":
            job.records_found = int(event.get("records", job.records_found))
            job.status_message = (
                f"Reading {event.get('channel', 'Telegram channel')} "
                f"(batch {event.get('batch', 0)})"
            )
        elif event_type == "channel_completed":
            index = int(event["channel_index"])
            total = max(int(event["total_links"]), 1)
            job.progress = 5 + int((index / total) * 75)
            job.records_found = int(event.get("total_records", job.records_found))
            self._log(
                job,
                "info",
                f"Completed link {index} of {total}: {event.get('records', 0)} record(s).",
            )
        elif event_type == "flood_wait":
            self._log(
                job,
                "warning",
                f"Telegram requested a {event.get('seconds', 0)} second wait.",
            )
        elif event_type == "telegram_retry":
            self._log(job, "warning", "Telegram request failed; retrying.")

    async def _worker(self) -> None:
        while True:
            job_id = await self._queue.get()
            job = self.jobs[job_id]
            try:
                await self._execute(job)
            finally:
                self._queue.task_done()

    async def _execute(self, job: ScrapeJob) -> None:
        job.status = JobStatus.RUNNING
        job.started_at = utc_now()
        job.progress = 5
        job.status_message = "Connecting to Telegram"
        self._log(job, "info", "Scraping started.")

        try:
            records = await self.scraper.scrape(
                job.links,
                job.start_date,
                job.end_date,
                lambda event: self._on_progress(job, event),
            )
            job.records_found = len(records)
            job.progress = 85
            job.status_message = "Updating Google Sheets"
            self._log(job, "info", f"Found {len(records)} structured record(s).")

            result = await asyncio.to_thread(self.writer.write, records)
            job.rows_appended = result.appended
            job.duplicates_skipped = result.duplicates
            job.progress = 100
            job.status = JobStatus.COMPLETED
            job.status_message = "Scraping and Google Sheets update completed"
            self._log(
                job,
                "success",
                f"Added {result.appended} row(s) to {result.worksheet_name}.",
            )
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.status_message = "Job failed"
            job.error = str(exc) or exc.__class__.__name__
            self._log(job, "error", job.error)
        finally:
            job.completed_at = utc_now()
