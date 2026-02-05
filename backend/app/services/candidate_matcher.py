from __future__ import annotations

import json
import logging

from openai import AsyncAzureOpenAI

from app.core.config import Settings
from app.models.lastenheft import (
    CandidateMatch,
    CandidateMatchResponse,
    ExtractedSkill,
    ScoreBreakdown,
)
from app.services.embedding_service import embedding_service
from app.services.search_service import search_service

logger = logging.getLogger(__name__)

WEIGHT_SKILL_MATCH = 0.40
WEIGHT_EXPERIENCE = 0.25
WEIGHT_SEMANTIC = 0.20
WEIGHT_AVAILABILITY = 0.15

DEFAULT_AVAILABILITY = 0.8
MAX_CANDIDATES = 10

LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 3000

MATCH_EXPLANATION_SYSTEM_PROMPT = (
    "Du bist ein HR-Experte der die Eignung von Kandidaten für Projekte bewertet. "
    "Du erhältst eine Zusammenfassung der Projektanforderungen (Lastenheft) sowie eine "
    "Liste von Kandidaten mit ihren Fähigkeiten und Bewertungen.\n\n"
    "Erstelle für jeden Kandidaten eine kurze Erklärung (2-3 Sätze), warum er gut oder "
    "weniger gut zum Projekt passt. Beziehe dich auf konkrete Skills und Erfahrungen.\n\n"
    "Antworte ausschließlich als JSON-Objekt mit dem Feld 'explanations', "
    "wobei jedes Element die Felder 'employee_alias' und 'explanation' hat."
)


class CandidateMatcherError(Exception):
    pass


def calculate_skill_match(
    required_skills: list[ExtractedSkill],
    employee_skills: list[str],
    employee_tools: list[str],
) -> float:
    if not required_skills:
        return 0.0

    employee_set = {s.lower() for s in employee_skills} | {t.lower() for t in employee_tools}
    if not employee_set:
        return 0.0

    weighted_total = 0.0
    weighted_matched = 0.0

    for skill in required_skills:
        weight = 2.0 if skill.mandatory else 1.0
        weighted_total += weight
        if skill.name.lower() in employee_set:
            weighted_matched += weight

    if weighted_total == 0.0:
        return 0.0
    return weighted_matched / weighted_total


def calculate_experience_score(required_level: str | None, years: float) -> float:
    if required_level is None:
        return 0.7

    level_ranges: dict[str, tuple[float, float]] = {
        "junior": (0.0, 2.0),
        "mid": (2.0, 5.0),
        "senior": (5.0, 10.0),
        "expert": (8.0, 20.0),
    }

    ideal_min, ideal_max = level_ranges.get(required_level, (2.0, 5.0))
    ideal_mid = (ideal_min + ideal_max) / 2.0

    distance = abs(years - ideal_mid)
    spread = (ideal_max - ideal_min) / 2.0 + 2.0

    score = max(0.0, 1.0 - (distance / spread))
    return min(1.0, score)


def normalize_search_score(score: float, max_score: float) -> float:
    if max_score <= 0.0:
        return 0.0
    normalized = score / max_score
    return max(0.0, min(1.0, normalized))


class CandidateMatcher:
    def __init__(self) -> None:
        self.client: AsyncAzureOpenAI | None = None
        self.initialized = False
        self.model = ""

    async def initialize(self, settings: Settings) -> None:
        if self.initialized:
            return

        if not settings.OPENAI_ENDPOINT or not settings.OPENAI_API_KEY:
            logger.warning("OpenAI credentials missing — CandidateMatcher not initialized")
            return

        self.client = AsyncAzureOpenAI(
            azure_endpoint=settings.OPENAI_ENDPOINT,
            api_key=settings.OPENAI_API_KEY,
            api_version=settings.OPENAI_API_VERSION,
        )
        self.model = settings.OPENAI_CHAT_MODEL
        self.initialized = True

    async def close(self) -> None:
        self.client = None
        self.initialized = False

    def _build_search_query(self, skills: list[ExtractedSkill]) -> tuple[str, list[str]]:
        mandatory = [s.name for s in skills if s.mandatory]
        all_names = [s.name for s in skills]

        query_skills = mandatory if mandatory else all_names
        query_text = " ".join(query_skills)
        return query_text, all_names

    def _score_candidate(
        self,
        result: dict,
        required_skills: list[ExtractedSkill],
        max_search_score: float,
    ) -> tuple[float, ScoreBreakdown]:
        skill_score = calculate_skill_match(
            required_skills,
            result.get("skills", []),
            result.get("tools", []),
        )

        primary_level = next(
            (s.level for s in required_skills if s.mandatory and s.level),
            next((s.level for s in required_skills if s.level), None),
        )
        years = float(result.get("years_of_experience", 0) or 0)
        experience_score = calculate_experience_score(primary_level, years)

        semantic_score = normalize_search_score(
            result.get("score", 0),
            max_search_score,
        )

        availability_score = DEFAULT_AVAILABILITY

        total = (
            WEIGHT_SKILL_MATCH * skill_score
            + WEIGHT_EXPERIENCE * experience_score
            + WEIGHT_SEMANTIC * semantic_score
            + WEIGHT_AVAILABILITY * availability_score
        )

        breakdown = ScoreBreakdown(
            skill_match=round(skill_score, 4),
            experience=round(experience_score, 4),
            semantic_similarity=round(semantic_score, 4),
            availability=round(availability_score, 4),
        )
        return round(total, 4), breakdown

    async def _generate_explanations(
        self,
        candidates: list[dict],
        skills: list[ExtractedSkill],
        text: str,
    ) -> dict[str, str]:
        if not self.client:
            return {}

        skill_summary = ", ".join(s.name for s in skills)
        candidates_text = "\n".join(
            f"- {c['employee_alias']} ({c.get('employee_name', '')}): "
            f"Skills: {', '.join(c.get('skills', []))}, "
            f"Tools: {', '.join(c.get('tools', []))}, "
            f"Titel: {c.get('title', '')}"
            for c in candidates
        )

        user_content = (
            f"Lastenheft-Anforderungen (Kurzfassung):\n"
            f"Geforderte Skills: {skill_summary}\n\n"
            f"Text-Auszug: {text[:1000]}\n\n"
            f"Kandidaten:\n{candidates_text}"
        )

        messages = [
            {"role": "system", "content": MATCH_EXPLANATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            if not content:
                return {}
            data = json.loads(content)
            return {item["employee_alias"]: item["explanation"] for item in data.get("explanations", [])}
        except Exception:
            logger.exception("Failed to generate match explanations — continuing without")
            return {}

    async def match(
        self,
        skills: list[ExtractedSkill],
        text: str,
    ) -> CandidateMatchResponse:
        if not self.initialized or not self.client:
            raise CandidateMatcherError("CandidateMatcher not initialized")

        query_text, all_skill_names = self._build_search_query(skills)

        try:
            query_vector = await embedding_service.get_embedding(query_text)
        except Exception as e:
            raise CandidateMatcherError(f"Embedding failed: {e}") from e

        try:
            search_results = await search_service.hybrid_search(
                query_text=query_text,
                query_vector=query_vector,
                top=MAX_CANDIDATES * 2,
            )
        except Exception as e:
            raise CandidateMatcherError(f"Search failed: {e}") from e

        if not search_results:
            return CandidateMatchResponse(
                matches=[],
                total_candidates_searched=0,
                query_skills=all_skill_names,
            )

        max_search_score = max(r.get("score", 0) for r in search_results) or 1.0

        scored: list[tuple[float, ScoreBreakdown, dict]] = []
        for result in search_results:
            total, breakdown = self._score_candidate(result, skills, max_search_score)
            scored.append((total, breakdown, result))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_scored = scored[:MAX_CANDIDATES]

        top_results = [item[2] for item in top_scored]
        explanations = await self._generate_explanations(top_results, skills, text)

        matches: list[CandidateMatch] = []
        for total, breakdown, result in top_scored:
            alias = result.get("employee_alias", "")
            matches.append(
                CandidateMatch(
                    employee_name=result.get("employee_name", ""),
                    employee_alias=alias,
                    title=result.get("title", ""),
                    location=result.get("location", ""),
                    skills=result.get("skills", []),
                    total_score=total,
                    breakdown=breakdown,
                    explanation=explanations.get(alias, ""),
                )
            )

        return CandidateMatchResponse(
            matches=matches,
            total_candidates_searched=len(search_results),
            query_skills=all_skill_names,
        )


candidate_matcher = CandidateMatcher()
