from fastapi.testclient import TestClient
from unittest.mock import patch
import unittest

from app.api import allowed_cors_origins, create_app, run_jobs_immediately
from app.jobs import JobManager
from app.scraper.sheets import SheetWriteResult


class FakeScraper:
    async def scrape(self, links, start, end, progress=None):
        return []


class FakeWriter:
    def write(self, records):
        return SheetWriteResult(0, 0, 0, "Retail_Banking")


class ApiTests(unittest.TestCase):
    def setUp(self):
        manager = JobManager(FakeScraper(), FakeWriter())
        self.client_context = TestClient(create_app(manager))
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)

    def test_health(self):
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["worker"], "ready")

    def test_submits_valid_job(self):
        response = self.client.post(
            "/api/jobs",
            json={
                "links": ["https://t.me/example"],
                "start_date": "2026-06-01T00:00:00",
                "end_date": "2026-06-02T00:00:00",
            },
        )

        self.assertEqual(response.status_code, 202)
        self.assertIn(response.json()["status"], ("queued", "running", "completed"))
        self.assertEqual(response.json()["links"], ["https://t.me/example"])

    def test_submits_job_on_vercel_stripped_paths(self):
        payload = {
            "links": ["https://t.me/example"],
            "start_date": "2026-06-01T00:00:00",
            "end_date": "2026-06-02T00:00:00",
        }

        root_response = self.client.post("/", json=payload)
        jobs_response = self.client.post("/jobs", json=payload)
        health_post_response = self.client.post("/api/health", json=payload)

        self.assertEqual(root_response.status_code, 202)
        self.assertEqual(jobs_response.status_code, 202)
        self.assertEqual(health_post_response.status_code, 202)

    def test_reads_health_on_vercel_stripped_path(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["worker"], "ready")

    def test_rejects_invalid_link(self):
        response = self.client.post(
            "/api/jobs",
            json={
                "links": ["https://example.com/channel"],
                "start_date": "2026-06-01T00:00:00",
                "end_date": "2026-06-02T00:00:00",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("Invalid Telegram link", response.json()["detail"])

    def test_returns_not_found_for_unknown_job(self):
        response = self.client.get("/api/jobs/missing")

        self.assertEqual(response.status_code, 404)

    def test_reads_cors_origins_from_env(self):
        with patch.dict(
            "os.environ",
            {"BACKEND_CORS_ORIGINS": "https://portal.vercel.app, http://localhost:5173/"},
        ):
            self.assertEqual(
                allowed_cors_origins(),
                ["https://portal.vercel.app", "http://localhost:5173"],
            )

    def test_reads_serverless_job_mode_from_env(self):
        with patch.dict("os.environ", {"SERVERLESS_SYNC_JOBS": "true"}):
            self.assertTrue(run_jobs_immediately())

    def test_reports_configuration_error_as_json(self):
        with patch.dict("os.environ", {}, clear=True):
            with TestClient(create_app()) as client:
                response = client.post(
                    "/api/jobs",
                    json={
                        "links": ["https://t.me/example"],
                        "start_date": "2026-06-01T00:00:00",
                        "end_date": "2026-06-02T00:00:00",
                    },
                )

        self.assertEqual(response.status_code, 500)
        self.assertIn("Backend configuration error", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
