from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from app.core.dependencies import get_current_user
from app.main import app
from app.models.auth import UserInfo
from app.services.chat_service import SYSTEM_PROMPT_DE, SYSTEM_PROMPT_EN, ChatService


def _sample_results(count: int = 2) -> list[dict]:
    results = []
    for i in range(count):
        results.append(
            {
                "id": f"id-{i}",
                "employee_name": f"Employee {i}",
                "employee_alias": f"emp{i}",
                "content": f"Profile content for employee {i}",
                "skills": ["Python", "FastAPI"],
                "tools": ["VS Code", "Docker"],
                "title": f"Engineer {i}",
                "location": "Berlin",
                "score": 0.95 - i * 0.1,
            }
        )
    return results


class TestGetSystemPrompt:
    def test_returns_german_prompt(self):
        service = ChatService()
        assert service.get_system_prompt("de") == SYSTEM_PROMPT_DE
        assert "HR-Fachleute" in service.get_system_prompt("de")

    def test_returns_english_prompt(self):
        service = ChatService()
        assert service.get_system_prompt("en") == SYSTEM_PROMPT_EN
        assert "HR professionals" in service.get_system_prompt("en")

    def test_defaults_to_english_for_unknown_language(self):
        service = ChatService()
        assert service.get_system_prompt("fr") == SYSTEM_PROMPT_EN


class TestAssembleContext:
    def test_empty_results_german(self):
        service = ChatService()
        result = service.assemble_context([], "de")
        assert "Keine passenden Mitarbeiter" in result

    def test_empty_results_english(self):
        service = ChatService()
        result = service.assemble_context([], "en")
        assert "No matching employees" in result

    def test_includes_employee_names(self):
        service = ChatService()
        results = _sample_results(2)
        context = service.assemble_context(results, "en")
        assert "Employee 0" in context
        assert "Employee 1" in context

    def test_includes_skills_and_title(self):
        service = ChatService()
        results = _sample_results(1)
        context = service.assemble_context(results, "en")
        assert "Python" in context
        assert "FastAPI" in context
        assert "Engineer 0" in context

    def test_german_labels(self):
        service = ChatService()
        results = _sample_results(1)
        context = service.assemble_context(results, "de")
        assert "Fähigkeiten" in context
        assert "Position" in context
        assert "Standort" in context

    def test_limits_to_10_results(self):
        service = ChatService()
        results = _sample_results(15)
        context = service.assemble_context(results, "en")
        assert "Employee 9" in context
        assert "Employee 10" not in context
        assert "5 more results" in context

    def test_truncates_content_to_300_chars(self):
        service = ChatService()
        results = [{"employee_name": "Long", "content": "x" * 500}]
        context = service.assemble_context(results, "en")
        profile_line = [line for line in context.split("\n") if "Profile:" in line]
        assert len(profile_line) == 1
        assert len(profile_line[0]) < 350


class TestStreamChat:
    @pytest.mark.anyio
    async def test_not_initialized_raises(self):
        service = ChatService()
        with pytest.raises(RuntimeError, match="not initialized"):
            async for _ in service.stream_chat("test"):
                pass

    @pytest.mark.anyio
    async def test_yields_start_event_first(self):
        service = ChatService()
        service.initialized = True
        service.client = MagicMock()
        service.model = "gpt-4o"

        mock_embedding = [0.1] * 3072
        mock_results = _sample_results(1)

        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta.content = "Hello"

        async def mock_stream():
            yield mock_chunk

        with (
            patch("app.services.chat_service.embedding_service") as mock_emb,
            patch("app.services.chat_service.search_service") as mock_search,
        ):
            mock_emb.get_embedding = AsyncMock(return_value=mock_embedding)
            mock_search.hybrid_search = AsyncMock(return_value=mock_results)
            service.client.chat.completions.create = AsyncMock(return_value=mock_stream())

            events = []
            async for event in service.stream_chat("find Python devs", "en"):
                events.append(event)

        assert events[0].startswith("event: start\n")
        data = json.loads(events[0].split("data: ")[1].strip())
        assert data["status"] == "started"

    @pytest.mark.anyio
    async def test_full_pipeline_event_order(self):
        service = ChatService()
        service.initialized = True
        service.client = MagicMock()
        service.model = "gpt-4o"

        mock_embedding = [0.1] * 3072
        mock_results = _sample_results(2)

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[0].delta.content = "First"

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock()]
        mock_chunk2.choices[0].delta.content = " token"

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        with (
            patch("app.services.chat_service.embedding_service") as mock_emb,
            patch("app.services.chat_service.search_service") as mock_search,
        ):
            mock_emb.get_embedding = AsyncMock(return_value=mock_embedding)
            mock_search.hybrid_search = AsyncMock(return_value=mock_results)
            service.client.chat.completions.create = AsyncMock(return_value=mock_stream())

            events = []
            async for event in service.stream_chat("find devs", "de"):
                events.append(event)

        event_types = [e.split("\n")[0].replace("event: ", "") for e in events]
        assert event_types == ["start", "search_complete", "token", "token", "complete"]

    @pytest.mark.anyio
    async def test_search_complete_contains_employees(self):
        service = ChatService()
        service.initialized = True
        service.client = MagicMock()
        service.model = "gpt-4o"

        mock_results = _sample_results(2)

        async def mock_stream():
            return
            yield  # noqa: RET504 — make this an async generator

        with (
            patch("app.services.chat_service.embedding_service") as mock_emb,
            patch("app.services.chat_service.search_service") as mock_search,
        ):
            mock_emb.get_embedding = AsyncMock(return_value=[0.1] * 3072)
            mock_search.hybrid_search = AsyncMock(return_value=mock_results)
            service.client.chat.completions.create = AsyncMock(return_value=mock_stream())

            events = []
            async for event in service.stream_chat("test", "en"):
                events.append(event)

        search_event = events[1]
        data = json.loads(search_event.split("data: ")[1].strip())
        assert data["results_count"] == 2
        assert len(data["employees"]) == 2
        assert data["employees"][0]["name"] == "Employee 0"
        assert data["employees"][0]["alias"] == "emp0"

    @pytest.mark.anyio
    async def test_handles_embedding_error(self):
        service = ChatService()
        service.initialized = True
        service.client = MagicMock()
        service.model = "gpt-4o"

        with patch("app.services.chat_service.embedding_service") as mock_emb:
            mock_emb.get_embedding = AsyncMock(side_effect=RuntimeError("Embedding failed"))

            events = []
            async for event in service.stream_chat("test", "en"):
                events.append(event)

        assert events[0].startswith("event: start\n")
        assert events[1].startswith("event: error\n")
        error_data = json.loads(events[1].split("data: ")[1].strip())
        assert "Embedding failed" in error_data["error"]

    @pytest.mark.anyio
    async def test_handles_search_error(self):
        service = ChatService()
        service.initialized = True
        service.client = MagicMock()
        service.model = "gpt-4o"

        with (
            patch("app.services.chat_service.embedding_service") as mock_emb,
            patch("app.services.chat_service.search_service") as mock_search,
        ):
            mock_emb.get_embedding = AsyncMock(return_value=[0.1] * 3072)
            mock_search.hybrid_search = AsyncMock(side_effect=RuntimeError("Search unavailable"))

            events = []
            async for event in service.stream_chat("test", "de"):
                events.append(event)

        error_event = [e for e in events if e.startswith("event: error")]
        assert len(error_event) == 1
        error_data = json.loads(error_event[0].split("data: ")[1].strip())
        assert "Search unavailable" in error_data["error"]

    @pytest.mark.anyio
    async def test_handles_openai_stream_error(self):
        service = ChatService()
        service.initialized = True
        service.client = MagicMock()
        service.model = "gpt-4o"

        with (
            patch("app.services.chat_service.embedding_service") as mock_emb,
            patch("app.services.chat_service.search_service") as mock_search,
        ):
            mock_emb.get_embedding = AsyncMock(return_value=[0.1] * 3072)
            mock_search.hybrid_search = AsyncMock(return_value=_sample_results(1))
            service.client.chat.completions.create = AsyncMock(side_effect=Exception("OpenAI rate limit"))

            events = []
            async for event in service.stream_chat("test", "en"):
                events.append(event)

        event_types = [e.split("\n")[0].replace("event: ", "") for e in events]
        assert "start" in event_types
        assert "error" in event_types
        assert "complete" not in event_types


class TestSSEFormat:
    @pytest.mark.anyio
    async def test_all_events_follow_sse_format(self):
        service = ChatService()
        service.initialized = True
        service.client = MagicMock()
        service.model = "gpt-4o"

        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta.content = "Hi"

        async def mock_stream():
            yield mock_chunk

        with (
            patch("app.services.chat_service.embedding_service") as mock_emb,
            patch("app.services.chat_service.search_service") as mock_search,
        ):
            mock_emb.get_embedding = AsyncMock(return_value=[0.1] * 3072)
            mock_search.hybrid_search = AsyncMock(return_value=_sample_results(1))
            service.client.chat.completions.create = AsyncMock(return_value=mock_stream())

            async for event in service.stream_chat("test", "en"):
                assert event.startswith("event: ")
                assert "\ndata: " in event
                assert event.endswith("\n\n")
                data_str = event.split("data: ", 1)[1].rstrip("\n")
                json.loads(data_str)


class TestChatEndpoint:
    def test_requires_auth(self):
        app.dependency_overrides.clear()
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chat/stream",
                json={"query": "find Python devs", "language": "en"},
            )
        assert response.status_code == 401

    def test_streams_response_with_auth(self):
        mock_user = UserInfo(id="u1", name="Test", email="t@emposo.de", roles=["viewer"])
        app.dependency_overrides[get_current_user] = lambda: mock_user

        async def fake_stream(query: str, language: str):
            yield 'event: start\ndata: {"status":"started"}\n\n'
            yield 'event: complete\ndata: {"status":"complete"}\n\n'

        with patch("app.api.v1.endpoints.chat.chat_service") as mock_svc:
            mock_svc.stream_chat = fake_stream
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/chat/stream",
                    json={"query": "find Python devs", "language": "en"},
                )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        assert "event: start" in response.text
        assert "event: complete" in response.text
        app.dependency_overrides.clear()

    def test_rejects_empty_query(self):
        mock_user = UserInfo(id="u1", name="Test", email="t@emposo.de", roles=["viewer"])
        app.dependency_overrides[get_current_user] = lambda: mock_user
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chat/stream",
                json={"query": "", "language": "en"},
            )
        assert response.status_code == 422
        app.dependency_overrides.clear()

    def test_rejects_invalid_language(self):
        mock_user = UserInfo(id="u1", name="Test", email="t@emposo.de", roles=["viewer"])
        app.dependency_overrides[get_current_user] = lambda: mock_user
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chat/stream",
                json={"query": "test", "language": "fr"},
            )
        assert response.status_code == 422
        app.dependency_overrides.clear()
