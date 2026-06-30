import asyncio
from datetime import datetime
import unittest

from app.jobs import JobManager, JobStatus
from app.scraper.sheets import SheetWriteResult


class FakeScraper:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.active = 0
        self.max_active = 0

    async def scrape(self, links, start, end, progress=None):
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            if progress:
                progress(
                    {
                        "type": "channel_started",
                        "channel_index": 1,
                        "total_links": len(links),
                    }
                )
            await asyncio.sleep(0)
            if self.should_fail:
                raise RuntimeError("Telegram unavailable")
            return [{"Type": "Visit", "Raw_Text": "Type: Visit"}]
        finally:
            self.active -= 1


class FakeWriter:
    def write(self, records):
        return SheetWriteResult(
            submitted=len(records),
            appended=len(records),
            duplicates=0,
            worksheet_name="Retail_Banking",
        )


class JobManagerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.scraper = FakeScraper()
        self.manager = JobManager(self.scraper, FakeWriter())
        await self.manager.start()

    async def asyncTearDown(self):
        await self.manager.stop()

    async def test_completes_scrape_and_sheet_write(self):
        job = await self.manager.submit(
            ["https://t.me/example"],
            datetime(2026, 6, 1),
            datetime(2026, 6, 2),
        )
        await self.manager._queue.join()

        self.assertEqual(job.status, JobStatus.COMPLETED)
        self.assertEqual(job.progress, 100)
        self.assertEqual(job.records_found, 1)
        self.assertEqual(job.rows_appended, 1)

    async def test_worker_executes_multiple_jobs_sequentially(self):
        await self.manager.submit(
            ["https://t.me/one"], datetime(2026, 6, 1), datetime(2026, 6, 2)
        )
        await self.manager.submit(
            ["https://t.me/two"], datetime(2026, 6, 1), datetime(2026, 6, 2)
        )
        await self.manager._queue.join()

        self.assertEqual(self.scraper.max_active, 1)

    async def test_can_run_job_immediately_for_serverless(self):
        job = await self.manager.submit(
            ["https://t.me/example"],
            datetime(2026, 6, 1),
            datetime(2026, 6, 2),
            run_immediately=True,
        )

        self.assertEqual(job.status, JobStatus.COMPLETED)
        self.assertEqual(job.rows_appended, 1)

    async def test_records_service_failure_for_status_polling(self):
        await self.manager.stop()
        manager = JobManager(FakeScraper(should_fail=True), FakeWriter())
        await manager.start()
        try:
            job = await manager.submit(
                ["https://t.me/example"],
                datetime(2026, 6, 1),
                datetime(2026, 6, 2),
            )
            await manager._queue.join()

            self.assertEqual(job.status, JobStatus.FAILED)
            self.assertEqual(job.error, "Telegram unavailable")
        finally:
            await manager.stop()


if __name__ == "__main__":
    unittest.main()
