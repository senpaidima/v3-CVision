from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

from openai import AsyncAzureOpenAI

from app.core.config import Settings
from app.services.embedding_service import embedding_service
from app.services.search_service import search_service

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_DE = (
    "Du bist ein KI-Assistent für HR-Fachleute bei der Suche nach geeigneten Mitarbeitern. Deine Aufgabe:\n"
    "1. Analysiere die bereitgestellten Mitarbeiterdaten und beantworte präzise die Anfrage.\n"
    "2. Verwende nur Informationen, die in den Mitarbeiterdaten vorhanden sind.\n"
    "3. Strukturiere deine Antwort klar und hebe wichtige Informationen hervor.\n"
    "4. Vergleiche Mitarbeiter miteinander und stelle ihre jeweiligen Stärken und Schwächen gegenüber.\n"
    "5. Wenn relevante Filterkriterien in der Anfrage erkannt wurden (z.B. Standort oder Erfahrung), "
    "betone besonders, welche Mitarbeiter diese Kriterien erfüllen.\n"
    "6. Sei objektiv, professionell und konzentriere dich auf Fakten.\n"
    "7. Wenn du einen besonders geeigneten Mitarbeiter identifizierst, erkläre warum.\n"
    "8. Wenn keine Mitarbeiter den Anforderungen entsprechen, erkläre dies ehrlich.\n"
    "9. Schließe mit einer Empfehlung ab, welcher Mitarbeiter am besten zur Anfrage passt.\n"
    "10. Formatiere deine Antwort mit Markdown für bessere Lesbarkeit."
)

SYSTEM_PROMPT_EN = (
    "You are an AI assistant for HR professionals searching for suitable employees. Your task:\n"
    "1. Analyze the provided employee data and precisely answer the query.\n"
    "2. Only use information that is present in the employee data.\n"
    "3. Structure your answer clearly and highlight important information.\n"
    "4. Compare employees and contrast their respective strengths and weaknesses.\n"
    "5. If relevant filter criteria were recognized in the query (e.g., location or experience), "
    "emphasize which employees meet these criteria.\n"
    "6. Be objective, professional, and focus on facts.\n"
    "7. If you identify a particularly suitable employee, explain why.\n"
    "8. If no employees meet the requirements, explain this honestly.\n"
    "9. Conclude with a recommendation of which employee(s) best match the query.\n"
    "10. Format your answer with Markdown for better readability."
)


class ChatService:
    def __init__(self) -> None:
        self.client: AsyncAzureOpenAI | None = None
        self.initialized = False
        self.model = ""

    async def initialize(self, settings: Settings) -> None:
        if self.initialized:
            return

        if not settings.OPENAI_ENDPOINT or not settings.OPENAI_API_KEY:
            logger.warning("OpenAI credentials missing — ChatService not initialized")
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

    def get_system_prompt(self, language: str) -> str:
        if language == "de":
            return SYSTEM_PROMPT_DE
        return SYSTEM_PROMPT_EN

    def assemble_context(self, results: list[dict], language: str) -> str:
        if not results:
            if language == "de":
                return "Keine passenden Mitarbeiter gefunden."
            return "No matching employees found."

        if language == "de":
            header = "Hier sind die relevantesten Mitarbeiter für Ihre Anfrage:\n\n"
        else:
            header = "Here are the most relevant employees for your query:\n\n"

        parts: list[str] = [header]
        for i, result in enumerate(results[:10]):
            name = result.get("employee_name", "Unknown")
            alias = result.get("employee_alias", "")
            title = result.get("title", "")
            location = result.get("location", "")
            skills = result.get("skills", [])
            tools = result.get("tools", [])
            content = result.get("content", "")

            parts.append(f"**{i + 1}. {name}**")
            if alias:
                parts.append(f"  Alias: {alias}")
            if title:
                label = "Position" if language == "de" else "Title"
                parts.append(f"  {label}: {title}")
            if location:
                label = "Standort" if language == "de" else "Location"
                parts.append(f"  {label}: {location}")
            if skills:
                skill_str = ", ".join(skills) if isinstance(skills, list) else str(skills)
                label = "Fähigkeiten" if language == "de" else "Skills"
                parts.append(f"  {label}: {skill_str}")
            if tools:
                tool_str = ", ".join(tools) if isinstance(tools, list) else str(tools)
                parts.append(f"  Tools: {tool_str}")
            if content:
                label = "Profil" if language == "de" else "Profile"
                parts.append(f"  {label}: {content[:300]}")
            parts.append("")

        if len(results) > 10:
            remaining = len(results) - 10
            if language == "de":
                parts.append(f"... und {remaining} weitere Ergebnisse")
            else:
                parts.append(f"... and {remaining} more results")

        return "\n".join(parts)

    async def stream_chat(self, query: str, language: str = "de") -> AsyncGenerator[str, None]:
        if not self.initialized or not self.client:
            raise RuntimeError("ChatService not initialized")

        yield f"event: start\ndata: {json.dumps({'status': 'started'})}\n\n"

        try:
            query_vector = await embedding_service.get_embedding(query)

            results = await search_service.hybrid_search(
                query_text=query,
                query_vector=query_vector,
                top=10,
            )

            employees_summary = [
                {
                    "name": r.get("employee_name", ""),
                    "alias": r.get("employee_alias", ""),
                    "title": r.get("title", ""),
                }
                for r in results
            ]
            yield (
                f"event: search_complete\n"
                f"data: {json.dumps({'results_count': len(results), 'employees': employees_summary})}\n\n"
            )

            context = self.assemble_context(results, language)

            system_prompt = self.get_system_prompt(language)
            if language == "de":
                user_content = f"Anfrage: {query}\n\nMitarbeiterinformationen:\n{context}"
            else:
                user_content = f"Query: {query}\n\nEmployee information:\n{context}"

            messages: list[dict[str, str]] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=0.7,
                max_tokens=2000,
                stream=True,
            )

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    yield f"event: token\ndata: {json.dumps({'content': token})}\n\n"

            yield f"event: complete\ndata: {json.dumps({'status': 'complete'})}\n\n"

        except Exception as e:
            logger.exception("Chat streaming error")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


chat_service = ChatService()
