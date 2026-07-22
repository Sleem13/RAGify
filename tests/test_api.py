from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import create_app
from services.app_state import ApiKeyStore, FileRegistry
from services.exporter import export_analytics


class ApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(create_app())

    def test_application_exposes_expected_routes(self) -> None:
        paths = set(self.client.get("/openapi.json").json()["paths"])
        self.assertTrue(
            {
                "/",
                "/chat",
                "/export",
                "/files",
                "/files/{filename}",
                "/generate-api-key",
                "/jobs/{job_id}",
                "/list-api-keys",
                "/reset",
                "/revoke-api-key",
                "/upload",
            }.issubset(paths)
        )

    def test_health_and_registry_are_available(self) -> None:
        health = self.client.get("/")
        files = self.client.get("/files")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "healthy")
        self.assertEqual(files.status_code, 200)
        self.assertIn("files", files.json())

    def test_json_export_round_trip(self) -> None:
        payload = {
            "summary": {"rows_count": 2, "columns": ["name", "score"]},
            "insights": "Scores are stable.",
        }
        response = self.client.post(
            "/export",
            data={"format": "json", "data": json.dumps(payload)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), payload)
        self.assertIn("ragify_export.json", response.headers["content-disposition"])

    def test_upload_returns_an_ingestion_job(self) -> None:
        queued = {
            "id": "job-123",
            "status": "queued",
            "stage": "queued",
            "progress": 5,
        }
        def fake_enqueue(path: Path, filename: str):
            self.assertEqual(filename, "notes.txt")
            path.unlink(missing_ok=True)
            return queued

        with patch("api.routers.documents.ingestion_service.enqueue", side_effect=fake_enqueue):
            response = self.client.post(
                "/upload",
                files={"file": ("notes.txt", b"Ancient archive notes", "text/plain")},
            )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["job_id"], "job-123")

    def test_export_rejects_unknown_format(self) -> None:
        response = self.client.post(
            "/export",
            data={"format": "zip", "data": "{}"},
        )
        self.assertEqual(response.status_code, 400)


class ApiKeyStoreTests(unittest.TestCase):
    def test_store_is_open_until_a_key_is_generated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "keys.json"
            store = ApiKeyStore(path)
            self.assertTrue(store.verify(None))
            key = store.generate()
            self.assertFalse(store.verify(None))
            self.assertTrue(store.verify(key))
            self.assertFalse(key in path.read_text(encoding="utf-8"))
            self.assertTrue(ApiKeyStore(path).verify(key))
            self.assertTrue(store.revoke(key))
            self.assertTrue(store.verify(None))


class ExtractedServiceTests(unittest.TestCase):
    def test_file_registry_persists_updates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "registry.json"
            registry = FileRegistry(path)
            registry.set("notes.txt", {"type": "document", "chunks": 2})
            self.assertEqual(FileRegistry(path).snapshot()["notes.txt"]["chunks"], 2)
            registry.remove("notes.txt")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {})

    def test_all_export_formats_produce_content(self) -> None:
        payload = {
            "summary": {"rows_count": 2, "columns": ["name", "score"]},
            "insights": "Scores are stable.",
            "chart_data": {
                "labels": ["A", "B"],
                "datasets": [{"label": "Score", "data": [8, 9]}],
            },
        }
        for format_name in ("json", "csv", "xlsx", "pdf"):
            with self.subTest(format=format_name):
                content, media_type, filename = export_analytics(format_name, payload)
                self.assertTrue(content)
                self.assertTrue(media_type)
                self.assertTrue(filename.endswith(f".{format_name}"))


if __name__ == "__main__":
    unittest.main()
