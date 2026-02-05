from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from app.core.dependencies import get_current_user
from app.main import app
from app.models.auth import UserInfo
from app.models.lastenheft import (
    ExtractedSkill,
    LastenheftAnalysisResponse,
    OpenQuestion,
    QualityScore,
)
from app.services.lastenheft_analyzer import (
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    QUALITY_SYSTEM_PROMPT,
    QUESTIONS_SYSTEM_PROMPT,
    SKILLS_SYSTEM_PROMPT,
    LastenheftAnalyzer,
    LastenheftAnalyzerError,
)

SAMPLE_TEXT = (
    "Das Projekt umfasst die Entwicklung einer Web-Applikation mit React und Python. "
    "Der Auftragnehmer muss Erfahrung mit Azure Cloud und CI/CD haben. "
    "Die Umsetzung soll in 6 Monaten erfolgen."
)

QUALITY_RESPONSE = json.dumps(
    {
        "completeness": 60,
        "clarity": 75,
        "specificity": 50,
        "feasibility": 80,
        "overall": 66,
        "summary": "Das Lastenheft deckt grundlegende Anforderungen ab.",
    }
)

QUESTIONS_RESPONSE = json.dumps(
    {
        "questions": [
            {"question": "Welche Browser müssen unterstützt werden?", "category": "technical", "priority": "high"},
            {"question": "Wie groß ist das Projektteam?", "category": "team", "priority": "medium"},
        ]
    }
)

SKILLS_RESPONSE = json.dumps(
    {
        "skills": [
            {"name": "React", "category": "framework", "mandatory": True, "level": "senior"},
            {"name": "Python", "category": "programming", "mandatory": True, "level": None},
            {"name": "Azure", "category": "cloud", "mandatory": True, "level": "mid"},
        ]
    }
)


def _make_llm_response(content: str) -> MagicMock:
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


class TestInitializeAndClose:
    @pytest.mark.anyio
    async def test_initialize_sets_client(self):
        analyzer = LastenheftAnalyzer()
        settings = MagicMock()
        settings.OPENAI_ENDPOINT = "https://test.openai.azure.com"
        settings.OPENAI_API_KEY = "test-key"
        settings.OPENAI_API_VERSION = "2024-10-21"
        settings.OPENAI_CHAT_MODEL = "gpt-4o"

        with patch("app.services.lastenheft_analyzer.AsyncAzureOpenAI"):
            await analyzer.initialize(settings)

        assert analyzer.initialized is True
        assert analyzer.model == "gpt-4o"

    @pytest.mark.anyio
    async def test_initialize_skips_when_already_initialized(self):
        analyzer = LastenheftAnalyzer()
        analyzer.initialized = True
        analyzer.client = MagicMock()
        settings = MagicMock()
        await analyzer.initialize(settings)
        assert analyzer.initialized is True

    @pytest.mark.anyio
    async def test_initialize_warns_without_credentials(self):
        analyzer = LastenheftAnalyzer()
        settings = MagicMock()
        settings.OPENAI_ENDPOINT = ""
        settings.OPENAI_API_KEY = ""
        await analyzer.initialize(settings)
        assert analyzer.initialized is False

    @pytest.mark.anyio
    async def test_close_resets_state(self):
        analyzer = LastenheftAnalyzer()
        analyzer.initialized = True
        analyzer.client = MagicMock()
        await analyzer.close()
        assert analyzer.initialized is False
        assert analyzer.client is None


class TestBuildMessages:
    def test_builds_system_and_user_messages(self):
        analyzer = LastenheftAnalyzer()
        messages = analyzer._build_messages("system prompt", "user text")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "system prompt"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "user text"


class TestQualityPrompt:
    def test_quality_prompt_contains_scoring_criteria(self):
        assert "completeness" in QUALITY_SYSTEM_PROMPT
        assert "clarity" in QUALITY_SYSTEM_PROMPT
        assert "specificity" in QUALITY_SYSTEM_PROMPT
        assert "feasibility" in QUALITY_SYSTEM_PROMPT
        assert "overall" in QUALITY_SYSTEM_PROMPT
        assert "summary" in QUALITY_SYSTEM_PROMPT
        assert "0-100" in QUALITY_SYSTEM_PROMPT


class TestQuestionsPrompt:
    def test_questions_prompt_contains_categories(self):
        assert "technical" in QUESTIONS_SYSTEM_PROMPT
        assert "team" in QUESTIONS_SYSTEM_PROMPT
        assert "timeline" in QUESTIONS_SYSTEM_PROMPT
        assert "budget" in QUESTIONS_SYSTEM_PROMPT
        assert "domain" in QUESTIONS_SYSTEM_PROMPT

    def test_questions_prompt_contains_priorities(self):
        assert "high" in QUESTIONS_SYSTEM_PROMPT
        assert "medium" in QUESTIONS_SYSTEM_PROMPT
        assert "low" in QUESTIONS_SYSTEM_PROMPT


class TestSkillsPrompt:
    def test_skills_prompt_contains_categories(self):
        assert "programming" in SKILLS_SYSTEM_PROMPT
        assert "framework" in SKILLS_SYSTEM_PROMPT
        assert "cloud" in SKILLS_SYSTEM_PROMPT
        assert "database" in SKILLS_SYSTEM_PROMPT
        assert "methodology" in SKILLS_SYSTEM_PROMPT
        assert "soft_skill" in SKILLS_SYSTEM_PROMPT
        assert "domain" in SKILLS_SYSTEM_PROMPT
        assert "other" in SKILLS_SYSTEM_PROMPT

    def test_skills_prompt_contains_levels(self):
        assert "junior" in SKILLS_SYSTEM_PROMPT
        assert "senior" in SKILLS_SYSTEM_PROMPT
        assert "expert" in SKILLS_SYSTEM_PROMPT


class TestAssessQuality:
    @pytest.mark.anyio
    async def test_parses_quality_response(self):
        analyzer = LastenheftAnalyzer()
        analyzer.initialized = True
        analyzer.client = MagicMock()
        analyzer.model = "gpt-4o"

        analyzer.client.chat.completions.create = AsyncMock(return_value=_make_llm_response(QUALITY_RESPONSE))

        result = await analyzer.assess_quality(SAMPLE_TEXT)
        assert isinstance(result, QualityScore)
        assert result.completeness == 60
        assert result.clarity == 75
        assert result.overall == 66
        assert "Lastenheft" in result.summary


class TestExtractQuestions:
    @pytest.mark.anyio
    async def test_parses_questions_response(self):
        analyzer = LastenheftAnalyzer()
        analyzer.initialized = True
        analyzer.client = MagicMock()
        analyzer.model = "gpt-4o"

        analyzer.client.chat.completions.create = AsyncMock(return_value=_make_llm_response(QUESTIONS_RESPONSE))

        result = await analyzer.extract_questions(SAMPLE_TEXT)
        assert len(result) == 2
        assert isinstance(result[0], OpenQuestion)
        assert result[0].category == "technical"
        assert result[0].priority == "high"
        assert result[1].category == "team"


class TestExtractSkills:
    @pytest.mark.anyio
    async def test_parses_skills_response(self):
        analyzer = LastenheftAnalyzer()
        analyzer.initialized = True
        analyzer.client = MagicMock()
        analyzer.model = "gpt-4o"

        analyzer.client.chat.completions.create = AsyncMock(return_value=_make_llm_response(SKILLS_RESPONSE))

        result = await analyzer.extract_skills(SAMPLE_TEXT)
        assert len(result) == 3
        assert isinstance(result[0], ExtractedSkill)
        assert result[0].name == "React"
        assert result[0].category == "framework"
        assert result[0].mandatory is True
        assert result[0].level == "senior"
        assert result[1].level is None


class TestCallLLM:
    @pytest.mark.anyio
    async def test_not_initialized_raises(self):
        analyzer = LastenheftAnalyzer()
        with pytest.raises(LastenheftAnalyzerError, match="not initialized"):
            await analyzer._call_llm("prompt", "text")

    @pytest.mark.anyio
    async def test_uses_json_response_format(self):
        analyzer = LastenheftAnalyzer()
        analyzer.initialized = True
        analyzer.client = MagicMock()
        analyzer.model = "gpt-4o"

        analyzer.client.chat.completions.create = AsyncMock(return_value=_make_llm_response('{"key": "value"}'))

        await analyzer._call_llm("system", "text")

        call_kwargs = analyzer.client.chat.completions.create.call_args[1]
        assert call_kwargs["response_format"] == {"type": "json_object"}
        assert call_kwargs["temperature"] == LLM_TEMPERATURE
        assert call_kwargs["max_tokens"] == LLM_MAX_TOKENS

    @pytest.mark.anyio
    async def test_empty_llm_response_raises(self):
        analyzer = LastenheftAnalyzer()
        analyzer.initialized = True
        analyzer.client = MagicMock()
        analyzer.model = "gpt-4o"

        response = _make_llm_response("")
        response.choices[0].message.content = None
        analyzer.client.chat.completions.create = AsyncMock(return_value=response)

        with pytest.raises(LastenheftAnalyzerError, match="Empty response"):
            await analyzer._call_llm("system", "text")

    @pytest.mark.anyio
    async def test_invalid_json_raises(self):
        analyzer = LastenheftAnalyzer()
        analyzer.initialized = True
        analyzer.client = MagicMock()
        analyzer.model = "gpt-4o"

        analyzer.client.chat.completions.create = AsyncMock(return_value=_make_llm_response("not json {{{"))

        with pytest.raises(LastenheftAnalyzerError, match="Failed to parse"):
            await analyzer._call_llm("system", "text")

    @pytest.mark.anyio
    async def test_openai_exception_raises(self):
        analyzer = LastenheftAnalyzer()
        analyzer.initialized = True
        analyzer.client = MagicMock()
        analyzer.model = "gpt-4o"

        analyzer.client.chat.completions.create = AsyncMock(side_effect=Exception("rate limited"))

        with pytest.raises(LastenheftAnalyzerError, match="LLM call failed"):
            await analyzer._call_llm("system", "text")


class TestAnalyze:
    @pytest.mark.anyio
    async def test_not_initialized_raises(self):
        analyzer = LastenheftAnalyzer()
        with pytest.raises(LastenheftAnalyzerError, match="not initialized"):
            await analyzer.analyze("text")

    @pytest.mark.anyio
    async def test_runs_three_calls_in_parallel(self):
        analyzer = LastenheftAnalyzer()
        analyzer.initialized = True
        analyzer.client = MagicMock()
        analyzer.model = "gpt-4o"

        call_order: list[str] = []

        async def mock_create(**kwargs):
            messages = kwargs.get("messages", [])
            system_content = messages[0]["content"] if messages else ""

            if "Bewertung" in system_content:
                call_order.append("quality")
                return _make_llm_response(QUALITY_RESPONSE)
            elif "offene Fragen" in system_content:
                call_order.append("questions")
                return _make_llm_response(QUESTIONS_RESPONSE)
            else:
                call_order.append("skills")
                return _make_llm_response(SKILLS_RESPONSE)

        analyzer.client.chat.completions.create = AsyncMock(side_effect=mock_create)

        result = await analyzer.analyze(SAMPLE_TEXT)

        assert isinstance(result, LastenheftAnalysisResponse)
        assert len(call_order) == 3
        assert analyzer.client.chat.completions.create.call_count == 3

    @pytest.mark.anyio
    async def test_returns_complete_analysis(self):
        analyzer = LastenheftAnalyzer()
        analyzer.initialized = True
        analyzer.client = MagicMock()
        analyzer.model = "gpt-4o"

        responses = iter(
            [
                _make_llm_response(QUALITY_RESPONSE),
                _make_llm_response(QUESTIONS_RESPONSE),
                _make_llm_response(SKILLS_RESPONSE),
            ]
        )
        analyzer.client.chat.completions.create = AsyncMock(side_effect=lambda **kw: next(responses))

        result = await analyzer.analyze(SAMPLE_TEXT)

        assert result.quality_assessment.overall == 66
        assert len(result.open_questions) == 2
        assert len(result.extracted_skills) == 3

    @pytest.mark.anyio
    async def test_propagates_llm_error(self):
        analyzer = LastenheftAnalyzer()
        analyzer.initialized = True
        analyzer.client = MagicMock()
        analyzer.model = "gpt-4o"

        analyzer.client.chat.completions.create = AsyncMock(side_effect=Exception("service unavailable"))

        with pytest.raises(LastenheftAnalyzerError):
            await analyzer.analyze(SAMPLE_TEXT)


class TestAnalyzeEndpoint:
    def test_returns_401_without_auth(self):
        app.dependency_overrides.clear()
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/lastenheft/analyze",
                json={"text": SAMPLE_TEXT},
            )
        assert response.status_code == 401

    def test_returns_422_for_short_text(self):
        mock_user = UserInfo(id="u1", name="Test", email="t@emposo.de", roles=["admin"])
        app.dependency_overrides[get_current_user] = lambda: mock_user
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/lastenheft/analyze",
                json={"text": "short"},
            )
        assert response.status_code == 422
        app.dependency_overrides.clear()

    def test_returns_analysis_with_auth(self):
        mock_user = UserInfo(id="u1", name="Test", email="t@emposo.de", roles=["admin"])
        app.dependency_overrides[get_current_user] = lambda: mock_user

        mock_response = LastenheftAnalysisResponse(
            quality_assessment=QualityScore(
                completeness=60,
                clarity=75,
                specificity=50,
                feasibility=80,
                overall=66,
                summary="Good quality.",
            ),
            open_questions=[
                OpenQuestion(question="Timeline?", category="timeline", priority="high"),
            ],
            extracted_skills=[
                ExtractedSkill(name="Python", category="programming", mandatory=True, level="senior"),
            ],
        )

        with patch("app.api.v1.endpoints.lastenheft.lastenheft_analyzer") as mock_analyzer:
            mock_analyzer.analyze = AsyncMock(return_value=mock_response)
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/lastenheft/analyze",
                    json={"text": SAMPLE_TEXT},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["quality_assessment"]["overall"] == 66
        assert len(data["open_questions"]) == 1
        assert len(data["extracted_skills"]) == 1
        assert data["extracted_skills"][0]["name"] == "Python"
        app.dependency_overrides.clear()

    def test_returns_502_on_analyzer_error(self):
        mock_user = UserInfo(id="u1", name="Test", email="t@emposo.de", roles=["admin"])
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch("app.api.v1.endpoints.lastenheft.lastenheft_analyzer") as mock_analyzer:
            mock_analyzer.analyze = AsyncMock(side_effect=LastenheftAnalyzerError("LLM unavailable"))
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/lastenheft/analyze",
                    json={"text": SAMPLE_TEXT},
                )

        assert response.status_code == 502
        assert "AI analysis failed" in response.json()["detail"]
        app.dependency_overrides.clear()
