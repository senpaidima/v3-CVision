"""Tests for the one-time re-indexing script."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from scripts.reindex import (
    _calculate_years,
    build_search_document,
    build_searchable_text,
    parse_args,
    upload_batch,
)

SAMPLE_COSMOS_DOC: dict = {
    "id": "JDOE",
    "metadata": {
        "title": "Doe, John",
        "first_name": "John",
        "last_name": "Doe",
    },
    "personal_info": {
        "location": "Berlin",
    },
    "skills": {
        "tools": ["VS Code", "Docker", "Git"],
        "technologies": ["Python", "JavaScript", "React"],
        "methods": [],
        "standards": [],
        "soft_skills": [],
    },
    "experience": [
        {
            "type": "job",
            "title": "Senior Developer",
            "company": "ACME",
            "start_date": "2020-01-15",
            "end_date": "",
            "tasks": [],
            "areas_of_expertise": [],
            "description": "5 years in software development",
            "role": "Senior Developer",
        },
        {
            "type": "project",
            "title": "CVision",
            "company": "",
            "start_date": "",
            "end_date": "",
            "tasks": [],
            "areas_of_expertise": [],
            "description": "",
            "role": "",
        },
        {
            "type": "project",
            "title": "DataPlatform",
            "company": "",
            "start_date": "",
            "end_date": "",
            "tasks": [],
            "areas_of_expertise": [],
            "description": "",
            "role": "",
        },
    ],
    "education": [],
    "certifications": [],
    "languages": [],
    "industry_knowledge": {
        "industries": [],
        "companies": [],
    },
}

MINIMAL_COSMOS_DOC: dict = {
    "id": "MINIMAL",
}


def test_build_searchable_text_with_all_fields():
    text = build_searchable_text(SAMPLE_COSMOS_DOC)

    assert "Doe, John" in text
    assert "Senior Developer" in text
    assert "Python" in text
    assert "JavaScript" in text
    assert "VS Code" in text
    assert "Docker" in text
    assert "5 years in software development" in text
    assert "CVision" in text
    assert "Berlin" in text


def test_build_searchable_text_with_missing_fields():
    text = build_searchable_text(MINIMAL_COSMOS_DOC)

    assert isinstance(text, str)
    assert "None" not in text


def test_build_search_document_maps_all_fields():
    embedding = [0.1] * 10
    doc = build_search_document(SAMPLE_COSMOS_DOC, embedding)

    assert doc["@search.action"] == "mergeOrUpload"
    assert doc["id"] == "JDOE"
    assert doc["employeeName"] == "Doe, John"
    assert doc["employeeAlias"] == "JDOE"
    assert doc["title"] == "Senior Developer"
    assert doc["skills"] == ["VS Code", "Docker", "Git", "Python", "JavaScript", "React"]
    assert doc["tools"] == ["VS Code", "Docker", "Git"]
    assert "Senior Developer" in doc["experience"]
    assert "ACME" in doc["experience"]
    assert "5 years in software development" in doc["experience"]
    assert doc["projects"] == "CVision, DataPlatform"
    assert doc["location"] == "Berlin"
    assert doc["department"] == ""
    assert doc["contentVector"] == embedding
    assert isinstance(doc["content"], str)
    assert len(doc["content"]) > 0


def test_build_search_document_handles_missing_fields():
    embedding = [0.0] * 10
    doc = build_search_document(MINIMAL_COSMOS_DOC, embedding)

    assert doc["id"] == "MINIMAL"
    assert doc["employeeName"] == ""
    assert doc["skills"] == []
    assert doc["tools"] == []
    assert doc["yearsOfExperience"] == 0.0
    assert doc["contentVector"] == embedding


def test_build_search_document_calculates_years_of_experience():
    embedding = [0.0] * 10
    doc = build_search_document(SAMPLE_COSMOS_DOC, embedding)

    assert isinstance(doc["yearsOfExperience"], float)
    assert doc["yearsOfExperience"] > 5.0


def test_build_search_document_uses_new_job_title_fallback():
    raw = {
        "id": "FB",
        "experience": [
            {
                "type": "job",
                "title": "Fallback Title",
                "company": "",
                "start_date": "",
                "end_date": "",
                "tasks": [],
                "areas_of_expertise": [],
                "description": "",
                "role": "",
            }
        ],
    }
    doc = build_search_document(raw, [0.0] * 10)

    assert doc["title"] == "Fallback Title"


def test_build_search_document_handles_csv_skills():
    raw = {
        "id": "MINIMAL",
        "skills": {
            "technologies": ["Python", "JavaScript", "React"],
            "tools": [],
            "methods": [],
            "standards": [],
            "soft_skills": [],
        },
    }
    doc = build_search_document(raw, [0.0] * 10)

    assert doc["skills"] == ["Python", "JavaScript", "React"]


def test_calculate_years_with_valid_iso_date():
    result = _calculate_years("2020-01-01")
    assert isinstance(result, float)
    assert result > 0.0


def test_calculate_years_with_none():
    assert _calculate_years(None) == 0.0


def test_calculate_years_with_invalid_string():
    assert _calculate_years("not-a-date") == 0.0


def test_parse_args_defaults():
    args = parse_args([])

    assert args.dry_run is False
    assert args.batch_size == 10
    assert args.verbose is False


def test_parse_args_custom_values():
    args = parse_args(["--batch-size", "25", "--verbose"])

    assert args.batch_size == 25
    assert args.verbose is True
    assert args.dry_run is False


def test_parse_args_dry_run():
    args = parse_args(["--dry-run"])

    assert args.dry_run is True


@pytest.mark.anyio
async def test_upload_batch_dry_run_skips_upload():
    mock_session = MagicMock()
    documents = [{"id": "1"}, {"id": "2"}]

    succeeded, failed = await upload_batch(
        mock_session,
        "http://example.com",
        {},
        documents,
        dry_run=True,
    )

    assert succeeded == 2
    assert failed == 0
    mock_session.post.assert_not_called()


@pytest.mark.anyio
async def test_upload_batch_success():
    response_data = {
        "value": [
            {"key": "1", "status": True, "statusCode": 200},
            {"key": "2", "status": True, "statusCode": 201},
        ]
    }

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=response_data)

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.post.return_value = mock_ctx

    documents = [{"id": "1"}, {"id": "2"}]
    succeeded, failed = await upload_batch(
        mock_session,
        "http://test/index",
        {"api-key": "k"},
        documents,
        dry_run=False,
    )

    assert succeeded == 2
    assert failed == 0
    mock_session.post.assert_called_once()


@pytest.mark.anyio
async def test_upload_batch_failure_raises():
    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.text = AsyncMock(return_value="Bad Request")

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.post.return_value = mock_ctx

    with pytest.raises(RuntimeError, match="Upload failed"):
        await upload_batch(
            mock_session,
            "http://test/index",
            {},
            [{"id": "1"}],
            dry_run=False,
        )
