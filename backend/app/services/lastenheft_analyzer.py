from __future__ import annotations

import asyncio
import json
import logging

from openai import AsyncAzureOpenAI

from app.core.config import Settings
from app.models.lastenheft import (
    ExtractedSkill,
    LastenheftAnalysisResponse,
    OpenQuestion,
    QualityScore,
)

logger = logging.getLogger(__name__)

QUALITY_SYSTEM_PROMPT = (
    "Du bist ein Experte für die Bewertung von Lastenheften/Leistungsbeschreibungen. "
    "Bewerte den folgenden Text anhand dieser Kriterien auf einer Skala von 0-100:\n"
    "- completeness: Sind alle wesentlichen Aspekte abgedeckt (Ziele, Anforderungen, Rahmenbedingungen, Abnahmekriterien)?\n"
    "- clarity: Sind die Formulierungen klar und eindeutig?\n"
    "- specificity: Sind Anforderungen konkret und messbar formuliert?\n"
    "- feasibility: Sind die Anforderungen technisch und zeitlich umsetzbar?\n"
    "- overall: Gewichteter Gesamtwert (completeness 30%, clarity 25%, specificity 25%, feasibility 20%)\n"
    "- summary: Kurze Zusammenfassung (2-3 Sätze) der Bewertung.\n\n"
    "Antworte ausschließlich als JSON-Objekt mit den Feldern: "
    "completeness, clarity, specificity, feasibility, overall, summary."
)

QUESTIONS_SYSTEM_PROMPT = (
    "Du bist ein erfahrener IT-Berater der offene Fragen in Ausschreibungen identifiziert. "
    "Analysiere den folgenden Lastenheft-Text und identifiziere offene Fragen, "
    "die vor einer Angebotserstellung geklärt werden sollten.\n\n"
    "Kategorien für Fragen:\n"
    "- technical: Technische Unklarheiten\n"
    "- team: Fragen zu Team-Zusammensetzung und Rollen\n"
    "- timeline: Fragen zu Zeitplan und Meilensteinen\n"
    "- budget: Fragen zu Budget und Vergütung\n"
    "- domain: Fachliche/domänenspezifische Fragen\n\n"
    "Prioritäten: high, medium, low\n\n"
    "Antworte ausschließlich als JSON-Objekt mit dem Feld 'questions', "
    "wobei jedes Element die Felder question, category, priority hat."
)

SKILLS_SYSTEM_PROMPT = (
    "Du bist ein Technical Recruiter der benötigte Skills aus Lastenheften extrahiert. "
    "Analysiere den folgenden Text und extrahiere alle geforderten technischen und "
    "fachlichen Kompetenzen.\n\n"
    "Kategorien für Skills:\n"
    "- programming: Programmiersprachen (z.B. Python, Java, C#)\n"
    "- framework: Frameworks und Libraries (z.B. React, FastAPI, Spring)\n"
    "- cloud: Cloud-Plattformen und Services (z.B. Azure, AWS, Docker)\n"
    "- database: Datenbanken (z.B. PostgreSQL, Cosmos DB, Redis)\n"
    "- methodology: Methoden und Prozesse (z.B. Scrum, CI/CD, TDD)\n"
    "- soft_skill: Soft Skills (z.B. Teamfähigkeit, Kommunikation)\n"
    "- domain: Domänenwissen (z.B. Finanzwesen, Gesundheitswesen)\n"
    "- other: Sonstige Kompetenzen\n\n"
    "Für jeden Skill gib an:\n"
    "- name: Normalisierter Skill-Name\n"
    "- category: Eine der obigen Kategorien\n"
    "- mandatory: true wenn explizit gefordert, false wenn nice-to-have\n"
    "- level: junior, mid, senior, expert oder null wenn nicht spezifiziert\n\n"
    "Antworte ausschließlich als JSON-Objekt mit dem Feld 'skills'."
)

LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 2000


class LastenheftAnalyzerError(Exception):
    pass


class LastenheftAnalyzer:
    def __init__(self) -> None:
        self.client: AsyncAzureOpenAI | None = None
        self.initialized = False
        self.model = ""

    async def initialize(self, settings: Settings) -> None:
        if self.initialized:
            return

        if not settings.OPENAI_ENDPOINT or not settings.OPENAI_API_KEY:
            logger.warning("OpenAI credentials missing — LastenheftAnalyzer not initialized")
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

    def _build_messages(self, system_prompt: str, text: str) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]

    async def _call_llm(self, system_prompt: str, text: str) -> dict:
        if not self.initialized or not self.client:
            raise LastenheftAnalyzerError("LastenheftAnalyzer not initialized")

        messages = self._build_messages(system_prompt, text)

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
                raise LastenheftAnalyzerError("Empty response from LLM")
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise LastenheftAnalyzerError(f"Failed to parse LLM JSON response: {e}") from e
        except LastenheftAnalyzerError:
            raise
        except Exception as e:
            raise LastenheftAnalyzerError(f"LLM call failed: {e}") from e

    async def assess_quality(self, text: str) -> QualityScore:
        data = await self._call_llm(QUALITY_SYSTEM_PROMPT, text)
        return QualityScore(**data)

    async def extract_questions(self, text: str) -> list[OpenQuestion]:
        data = await self._call_llm(QUESTIONS_SYSTEM_PROMPT, text)
        questions_raw = data.get("questions", [])
        return [OpenQuestion(**q) for q in questions_raw]

    async def extract_skills(self, text: str) -> list[ExtractedSkill]:
        data = await self._call_llm(SKILLS_SYSTEM_PROMPT, text)
        skills_raw = data.get("skills", [])
        return [ExtractedSkill(**s) for s in skills_raw]

    async def analyze(self, text: str) -> LastenheftAnalysisResponse:
        if not self.initialized or not self.client:
            raise LastenheftAnalyzerError("LastenheftAnalyzer not initialized")

        quality_task = self.assess_quality(text)
        questions_task = self.extract_questions(text)
        skills_task = self.extract_skills(text)

        quality, questions, skills = await asyncio.gather(quality_task, questions_task, skills_task)

        return LastenheftAnalysisResponse(
            quality_assessment=quality,
            open_questions=questions,
            extracted_skills=skills,
        )


lastenheft_analyzer = LastenheftAnalyzer()
