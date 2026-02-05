from __future__ import annotations

import io
import logging

import docx
import fitz

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

SUPPORTED_CONTENT_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}


class DocumentExtractionError(Exception):
    pass


class DocumentExtractor:
    def extract_from_pdf(self, file_bytes: bytes) -> str:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            pages = [page.get_text() for page in doc]
            doc.close()
            return "\n".join(pages).strip()
        except Exception as e:
            logger.error("PDF extraction failed: %s", e)
            raise DocumentExtractionError(f"Failed to extract text from PDF: {e}") from e

    def extract_from_docx(self, file_bytes: bytes) -> str:
        try:
            doc = docx.Document(io.BytesIO(file_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n".join(paragraphs).strip()
        except Exception as e:
            logger.error("DOCX extraction failed: %s", e)
            raise DocumentExtractionError(f"Failed to extract text from DOCX: {e}") from e

    def extract_from_text(self, text: str) -> str:
        return text.strip()

    def extract(self, file_bytes: bytes, content_type: str) -> str:
        if content_type not in SUPPORTED_CONTENT_TYPES:
            raise DocumentExtractionError(f"Unsupported content type: {content_type}")

        if len(file_bytes) > MAX_FILE_SIZE:
            raise DocumentExtractionError(f"File too large: {len(file_bytes)} bytes (max {MAX_FILE_SIZE})")

        if not file_bytes:
            raise DocumentExtractionError("Empty file")

        fmt = SUPPORTED_CONTENT_TYPES[content_type]
        if fmt == "pdf":
            return self.extract_from_pdf(file_bytes)
        return self.extract_from_docx(file_bytes)


document_extractor = DocumentExtractor()
