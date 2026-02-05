from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from app.core.dependencies import get_current_user
from app.main import app
from app.models.auth import UserInfo
from app.models.lastenheft import (
    CandidateMatch,
    CandidateMatchResponse,
    ExtractedSkill,
    ScoreBreakdown,
)
from app.services.candidate_matcher import (
    CandidateMatcher,
    CandidateMatcherError,
    calculate_experience_score,
    calculate_skill_match,
    normalize_search_score,
)

SAMPLE_SKILLS = [
    ExtractedSkill(name="Python", category="programming", mandatory=True, level="senior"),
    ExtractedSkill(name="React", category="framework", mandatory=True, level="mid"),
    ExtractedSkill(name="Azure", category="cloud", mandatory=False, level=None),
    ExtractedSkill(name="Docker", category="cloud", mandatory=False, level="junior"),
]

SAMPLE_TEXT = (
    "Das Projekt erfordert einen erfahrenen Python-Entwickler mit React-Kenntnissen. "
    "Azure Cloud Erfahrung und Docker sind wünschenswert."
)


def _make_search_result(
    idx: int,
    skills: list[str] | None = None,
    tools: list[str] | None = None,
    score: float = 0.9,
) -> dict:
    return {
        "id": f"id-{idx}",
        "employee_name": f"Employee {idx}",
        "employee_alias": f"emp{idx}",
        "content": f"Senior developer with broad experience {idx}",
        "skills": skills or ["Python", "Java"],
        "tools": tools or ["VS Code", "Docker"],
        "title": f"Engineer {idx}",
        "location": "Berlin",
        "score": score,
    }


def _make_llm_response(content: str) -> MagicMock:
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


class TestCalculateSkillMatch:
    def test_all_skills_match(self):
        required = [
            ExtractedSkill(name="Python", category="programming", mandatory=True, level=None),
            ExtractedSkill(name="React", category="framework", mandatory=False, level=None),
        ]
        result = calculate_skill_match(required, ["Python", "React", "Java"], [])
        assert result == 1.0

    def test_no_skills_match(self):
        required = [
            ExtractedSkill(name="Python", category="programming", mandatory=True, level=None),
            ExtractedSkill(name="React", category="framework", mandatory=True, level=None),
        ]
        result = calculate_skill_match(required, ["Go", "Rust"], ["Vim"])
        assert result == 0.0

    def test_partial_match(self):
        required = [
            ExtractedSkill(name="Python", category="programming", mandatory=False, level=None),
            ExtractedSkill(name="React", category="framework", mandatory=False, level=None),
        ]
        result = calculate_skill_match(required, ["Python"], [])
        assert result == pytest.approx(0.5)

    def test_mandatory_skills_count_double(self):
        required = [
            ExtractedSkill(name="Python", category="programming", mandatory=True, level=None),
            ExtractedSkill(name="React", category="framework", mandatory=False, level=None),
        ]
        result_mandatory = calculate_skill_match(required, ["Python"], [])
        result_optional = calculate_skill_match(required, ["React"], [])
        assert result_mandatory > result_optional

    def test_case_insensitive_matching(self):
        required = [
            ExtractedSkill(name="Python", category="programming", mandatory=True, level=None),
        ]
        result = calculate_skill_match(required, ["python"], [])
        assert result == 1.0

    def test_matches_against_tools_too(self):
        required = [
            ExtractedSkill(name="Docker", category="cloud", mandatory=True, level=None),
        ]
        result = calculate_skill_match(required, [], ["Docker", "Kubernetes"])
        assert result == 1.0

    def test_empty_required_skills(self):
        result = calculate_skill_match([], ["Python", "React"], ["Docker"])
        assert result == 0.0

    def test_empty_employee_skills_and_tools(self):
        required = [
            ExtractedSkill(name="Python", category="programming", mandatory=True, level=None),
        ]
        result = calculate_skill_match(required, [], [])
        assert result == 0.0


class TestCalculateExperienceScore:
    def test_no_level_specified_returns_neutral(self):
        result = calculate_experience_score(None, 5.0)
        assert result == pytest.approx(0.7)

    def test_junior_with_low_years(self):
        result = calculate_experience_score("junior", 1.0)
        assert result >= 0.8

    def test_junior_with_high_years(self):
        result = calculate_experience_score("junior", 10.0)
        assert result < 0.8

    def test_senior_with_high_years(self):
        result = calculate_experience_score("senior", 7.0)
        assert result >= 0.8

    def test_senior_with_low_years(self):
        result = calculate_experience_score("senior", 1.0)
        assert result < 0.8

    def test_mid_with_mid_years(self):
        result = calculate_experience_score("mid", 3.0)
        assert result >= 0.8

    def test_expert_with_very_high_years(self):
        result = calculate_experience_score("expert", 12.0)
        assert result >= 0.7

    def test_expert_with_low_years(self):
        result = calculate_experience_score("expert", 2.0)
        assert result < 0.8

    def test_returns_between_0_and_1(self):
        for level in [None, "junior", "mid", "senior", "expert"]:
            for years in [0.0, 1.0, 3.0, 5.0, 10.0, 20.0]:
                score = calculate_experience_score(level, years)
                assert 0.0 <= score <= 1.0, f"Out of range for level={level}, years={years}"


class TestNormalizeSearchScore:
    def test_zero_score(self):
        assert normalize_search_score(0.0, 10.0) == 0.0

    def test_max_score(self):
        assert normalize_search_score(10.0, 10.0) == 1.0

    def test_mid_score(self):
        assert normalize_search_score(5.0, 10.0) == pytest.approx(0.5)

    def test_zero_max_score_returns_zero(self):
        assert normalize_search_score(5.0, 0.0) == 0.0

    def test_negative_score_clamps_to_zero(self):
        assert normalize_search_score(-1.0, 10.0) == 0.0

    def test_score_above_max_clamps_to_one(self):
        assert normalize_search_score(15.0, 10.0) == 1.0


class TestCandidateMatcherInitialize:
    @pytest.mark.anyio
    async def test_initialize_sets_client(self):
        matcher = CandidateMatcher()
        settings = MagicMock()
        settings.OPENAI_ENDPOINT = "https://test.openai.azure.com"
        settings.OPENAI_API_KEY = "test-key"
        settings.OPENAI_API_VERSION = "2024-10-21"
        settings.OPENAI_CHAT_MODEL = "gpt-4o"

        with patch("app.services.candidate_matcher.AsyncAzureOpenAI"):
            await matcher.initialize(settings)

        assert matcher.initialized is True
        assert matcher.model == "gpt-4o"

    @pytest.mark.anyio
    async def test_initialize_skips_when_already_initialized(self):
        matcher = CandidateMatcher()
        matcher.initialized = True
        matcher.client = MagicMock()
        settings = MagicMock()
        await matcher.initialize(settings)
        assert matcher.initialized is True

    @pytest.mark.anyio
    async def test_initialize_warns_without_credentials(self):
        matcher = CandidateMatcher()
        settings = MagicMock()
        settings.OPENAI_ENDPOINT = ""
        settings.OPENAI_API_KEY = ""
        await matcher.initialize(settings)
        assert matcher.initialized is False

    @pytest.mark.anyio
    async def test_close_resets_state(self):
        matcher = CandidateMatcher()
        matcher.initialized = True
        matcher.client = MagicMock()
        await matcher.close()
        assert matcher.initialized is False
        assert matcher.client is None


class TestCandidateMatcherMatch:
    @pytest.mark.anyio
    async def test_not_initialized_raises(self):
        matcher = CandidateMatcher()
        with pytest.raises(CandidateMatcherError, match="not initialized"):
            await matcher.match(SAMPLE_SKILLS, SAMPLE_TEXT)

    @pytest.mark.anyio
    async def test_empty_search_results_returns_empty(self):
        matcher = CandidateMatcher()
        matcher.initialized = True
        matcher.client = MagicMock()
        matcher.model = "gpt-4o"

        with (
            patch("app.services.candidate_matcher.embedding_service") as mock_emb,
            patch("app.services.candidate_matcher.search_service") as mock_search,
        ):
            mock_emb.get_embedding = AsyncMock(return_value=[0.1] * 3072)
            mock_search.hybrid_search = AsyncMock(return_value=[])

            result = await matcher.match(SAMPLE_SKILLS, SAMPLE_TEXT)

        assert isinstance(result, CandidateMatchResponse)
        assert result.matches == []
        assert result.total_candidates_searched == 0
        assert "Python" in result.query_skills

    @pytest.mark.anyio
    async def test_full_pipeline_returns_scored_matches(self):
        matcher = CandidateMatcher()
        matcher.initialized = True
        matcher.client = MagicMock()
        matcher.model = "gpt-4o"

        search_results = [
            _make_search_result(0, skills=["Python", "React", "Azure"], tools=["Docker"], score=0.95),
            _make_search_result(1, skills=["Python"], tools=[], score=0.80),
            _make_search_result(2, skills=["Java", "Spring"], tools=["Maven"], score=0.60),
        ]

        explanations_json = json.dumps(
            {
                "explanations": [
                    {"employee_alias": "emp0", "explanation": "Perfekte Übereinstimmung mit allen Skills."},
                    {"employee_alias": "emp1", "explanation": "Python-Erfahrung vorhanden, React fehlt."},
                    {"employee_alias": "emp2", "explanation": "Keine relevanten Skills gefunden."},
                ]
            }
        )

        with (
            patch("app.services.candidate_matcher.embedding_service") as mock_emb,
            patch("app.services.candidate_matcher.search_service") as mock_search,
        ):
            mock_emb.get_embedding = AsyncMock(return_value=[0.1] * 3072)
            mock_search.hybrid_search = AsyncMock(return_value=search_results)
            matcher.client.chat.completions.create = AsyncMock(return_value=_make_llm_response(explanations_json))

            result = await matcher.match(SAMPLE_SKILLS, SAMPLE_TEXT)

        assert isinstance(result, CandidateMatchResponse)
        assert len(result.matches) == 3
        assert result.total_candidates_searched == 3

        assert result.matches[0].total_score >= result.matches[1].total_score
        assert result.matches[1].total_score >= result.matches[2].total_score

        first = result.matches[0]
        assert first.employee_name == "Employee 0"
        assert isinstance(first.breakdown, ScoreBreakdown)
        assert 0.0 <= first.breakdown.skill_match <= 1.0
        assert 0.0 <= first.breakdown.experience <= 1.0
        assert 0.0 <= first.breakdown.semantic_similarity <= 1.0
        assert first.breakdown.availability == pytest.approx(0.8)
        assert first.explanation != ""

    @pytest.mark.anyio
    async def test_limits_to_top_10(self):
        matcher = CandidateMatcher()
        matcher.initialized = True
        matcher.client = MagicMock()
        matcher.model = "gpt-4o"

        search_results = [_make_search_result(i, skills=["Python"], score=1.0 - i * 0.05) for i in range(15)]

        explanations_json = json.dumps(
            {"explanations": [{"employee_alias": f"emp{i}", "explanation": f"Match {i}"} for i in range(10)]}
        )

        with (
            patch("app.services.candidate_matcher.embedding_service") as mock_emb,
            patch("app.services.candidate_matcher.search_service") as mock_search,
        ):
            mock_emb.get_embedding = AsyncMock(return_value=[0.1] * 3072)
            mock_search.hybrid_search = AsyncMock(return_value=search_results)
            matcher.client.chat.completions.create = AsyncMock(return_value=_make_llm_response(explanations_json))

            result = await matcher.match(SAMPLE_SKILLS, SAMPLE_TEXT)

        assert len(result.matches) <= 10

    @pytest.mark.anyio
    async def test_llm_error_returns_matches_without_explanations(self):
        matcher = CandidateMatcher()
        matcher.initialized = True
        matcher.client = MagicMock()
        matcher.model = "gpt-4o"

        search_results = [
            _make_search_result(0, skills=["Python", "React"], score=0.9),
        ]

        with (
            patch("app.services.candidate_matcher.embedding_service") as mock_emb,
            patch("app.services.candidate_matcher.search_service") as mock_search,
        ):
            mock_emb.get_embedding = AsyncMock(return_value=[0.1] * 3072)
            mock_search.hybrid_search = AsyncMock(return_value=search_results)
            matcher.client.chat.completions.create = AsyncMock(side_effect=Exception("LLM rate limited"))

            result = await matcher.match(SAMPLE_SKILLS, SAMPLE_TEXT)

        assert len(result.matches) == 1
        assert result.matches[0].employee_name == "Employee 0"
        assert result.matches[0].explanation == ""

    @pytest.mark.anyio
    async def test_builds_query_from_mandatory_skills(self):
        matcher = CandidateMatcher()
        matcher.initialized = True
        matcher.client = MagicMock()
        matcher.model = "gpt-4o"

        skills = [
            ExtractedSkill(name="Python", category="programming", mandatory=True, level=None),
            ExtractedSkill(name="Docker", category="cloud", mandatory=False, level=None),
        ]

        with (
            patch("app.services.candidate_matcher.embedding_service") as mock_emb,
            patch("app.services.candidate_matcher.search_service") as mock_search,
        ):
            mock_emb.get_embedding = AsyncMock(return_value=[0.1] * 3072)
            mock_search.hybrid_search = AsyncMock(return_value=[])

            result = await matcher.match(skills, SAMPLE_TEXT)

        assert "Python" in result.query_skills
        assert "Docker" in result.query_skills

    @pytest.mark.anyio
    async def test_no_mandatory_skills_uses_all(self):
        matcher = CandidateMatcher()
        matcher.initialized = True
        matcher.client = MagicMock()
        matcher.model = "gpt-4o"

        skills = [
            ExtractedSkill(name="Python", category="programming", mandatory=False, level=None),
            ExtractedSkill(name="React", category="framework", mandatory=False, level=None),
        ]

        with (
            patch("app.services.candidate_matcher.embedding_service") as mock_emb,
            patch("app.services.candidate_matcher.search_service") as mock_search,
        ):
            mock_emb.get_embedding = AsyncMock(return_value=[0.1] * 3072)
            mock_search.hybrid_search = AsyncMock(return_value=[])

            result = await matcher.match(skills, SAMPLE_TEXT)

        assert "Python" in result.query_skills
        assert "React" in result.query_skills

    @pytest.mark.anyio
    async def test_embedding_error_raises(self):
        matcher = CandidateMatcher()
        matcher.initialized = True
        matcher.client = MagicMock()
        matcher.model = "gpt-4o"

        with patch("app.services.candidate_matcher.embedding_service") as mock_emb:
            mock_emb.get_embedding = AsyncMock(side_effect=RuntimeError("Embedding failed"))

            with pytest.raises(CandidateMatcherError, match="Embedding failed"):
                await matcher.match(SAMPLE_SKILLS, SAMPLE_TEXT)

    @pytest.mark.anyio
    async def test_search_error_raises(self):
        matcher = CandidateMatcher()
        matcher.initialized = True
        matcher.client = MagicMock()
        matcher.model = "gpt-4o"

        with (
            patch("app.services.candidate_matcher.embedding_service") as mock_emb,
            patch("app.services.candidate_matcher.search_service") as mock_search,
        ):
            mock_emb.get_embedding = AsyncMock(return_value=[0.1] * 3072)
            mock_search.hybrid_search = AsyncMock(side_effect=RuntimeError("Search unavailable"))

            with pytest.raises(CandidateMatcherError, match="Search unavailable"):
                await matcher.match(SAMPLE_SKILLS, SAMPLE_TEXT)


class TestMatchEndpoint:
    def test_returns_401_without_auth(self):
        app.dependency_overrides.clear()
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/lastenheft/match",
                json={
                    "extracted_skills": [
                        {"name": "Python", "category": "programming", "mandatory": True, "level": None}
                    ],
                    "text": SAMPLE_TEXT,
                },
            )
        assert response.status_code == 401

    def test_returns_422_for_short_text(self):
        mock_user = UserInfo(id="u1", name="Test", email="t@emposo.de", roles=["admin"])
        app.dependency_overrides[get_current_user] = lambda: mock_user
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/lastenheft/match",
                json={
                    "extracted_skills": [
                        {"name": "Python", "category": "programming", "mandatory": True, "level": None}
                    ],
                    "text": "short",
                },
            )
        assert response.status_code == 422
        app.dependency_overrides.clear()

    def test_returns_matches_with_auth(self):
        mock_user = UserInfo(id="u1", name="Test", email="t@emposo.de", roles=["admin"])
        app.dependency_overrides[get_current_user] = lambda: mock_user

        mock_response = CandidateMatchResponse(
            matches=[
                CandidateMatch(
                    employee_name="Max Mustermann",
                    employee_alias="mmustermann",
                    title="Senior Developer",
                    location="Berlin",
                    skills=["Python", "React"],
                    total_score=0.85,
                    breakdown=ScoreBreakdown(
                        skill_match=0.9,
                        experience=0.8,
                        semantic_similarity=0.85,
                        availability=0.8,
                    ),
                    explanation="Starke Übereinstimmung mit geforderten Skills.",
                )
            ],
            total_candidates_searched=5,
            query_skills=["Python", "React"],
        )

        with patch("app.api.v1.endpoints.lastenheft.candidate_matcher") as mock_matcher:
            mock_matcher.match = AsyncMock(return_value=mock_response)
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/lastenheft/match",
                    json={
                        "extracted_skills": [
                            {"name": "Python", "category": "programming", "mandatory": True, "level": "senior"}
                        ],
                        "text": SAMPLE_TEXT,
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert len(data["matches"]) == 1
        assert data["matches"][0]["employee_name"] == "Max Mustermann"
        assert data["matches"][0]["total_score"] == 0.85
        assert data["total_candidates_searched"] == 5
        assert "Python" in data["query_skills"]
        app.dependency_overrides.clear()

    def test_returns_502_on_matcher_error(self):
        mock_user = UserInfo(id="u1", name="Test", email="t@emposo.de", roles=["admin"])
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch("app.api.v1.endpoints.lastenheft.candidate_matcher") as mock_matcher:
            mock_matcher.match = AsyncMock(side_effect=CandidateMatcherError("Search unavailable"))
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/lastenheft/match",
                    json={
                        "extracted_skills": [
                            {"name": "Python", "category": "programming", "mandatory": True, "level": None}
                        ],
                        "text": SAMPLE_TEXT,
                    },
                )

        assert response.status_code == 502
        assert "Candidate matching failed" in response.json()["detail"]
        app.dependency_overrides.clear()
