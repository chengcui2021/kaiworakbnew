"""Document transform endpoint — restructure a document to match a template."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.database import get_db
from app.persistence.llm_service import BedrockLLMService, get_llm_service, get_llm_settings
from app.routes_persistent.llm_usage import record_usage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

MAX_TEXT_CONTENT_LENGTH = 100_000
MAX_PDF_FILE_BYTES = 5_000_000  # 5 MB

TRANSFORM_SYSTEM_PROMPT = """\
You are a document restructuring assistant. Your job is to take an existing \
document and reorganize its content to match a target template structure.

Rules:
1. Extract all relevant information from the source document and map it to the \
corresponding sections in the template.
2. Preserve the original facts, data, names, dates, and technical details exactly \
as they appear — do not fabricate information.
3. If a template section has no corresponding content in the source document, \
keep the section heading with a placeholder note like "[No information available \
in source document]".
4. Use the template's formatting conventions (headings, tables, lists, bold text) \
as shown in the template.
5. Output valid Markdown only — no preamble, no explanation, no code fences \
wrapping the output. Just the restructured document.
6. Do not add content that does not exist in the source document.\
"""


class TransformResponse(BaseModel):
    """Response from the transform endpoint."""

    content: str


def _build_user_prompt(document_text: str, template_content: str) -> str:
    return (
        "## Source Document\n\n"
        f"{document_text}\n\n"
        "## Target Template\n\n"
        f"{template_content}\n\n"
        "## Instructions\n\n"
        "Restructure the source document above to match the target template's structure "
        "and formatting. Map every piece of information from the source into the "
        "appropriate template section. Output only the final restructured Markdown."
    )


def _extract_pdf_text(raw: bytes) -> str:
    """Extract text from a PDF using pdfplumber."""
    import io

    import pdfplumber

    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    full_text = "\n\n".join(text_parts).strip()
    if not full_text:
        raise ValueError("PDF contains no extractable text")
    return full_text


@router.post(
    "/transform",
    response_model=TransformResponse,
    summary="Transform a document to match a template structure",
)
async def transform_document(
    document_text: str | None = Form(None),
    template_content: str | None = Form(None),
    file: UploadFile | None = File(None),
    llm: BedrockLLMService = Depends(get_llm_service),
    db: AsyncSession = Depends(get_db),
) -> TransformResponse:
    # Determine document text: from file upload (PDF) or from form field
    if file is not None:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are supported for file upload. "
                "Markdown files should be read client-side.",
            )
        raw = await file.read()
        if len(raw) > MAX_PDF_FILE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"PDF file is too large (max {MAX_PDF_FILE_BYTES // 1_000_000} MB).",
            )
        try:
            doc_text = _extract_pdf_text(raw)
        except Exception as e:
            logger.exception("PDF text extraction failed")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not extract text from PDF: {e}",
            ) from e
    elif document_text:
        doc_text = document_text
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either document_text or a PDF file must be provided.",
        )

    if not template_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="template_content is required.",
        )

    if len(doc_text) > MAX_TEXT_CONTENT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document text exceeds {MAX_TEXT_CONTENT_LENGTH:,} character limit.",
        )

    user_prompt = _build_user_prompt(doc_text, template_content)

    try:
        result = await llm.generate(TRANSFORM_SYSTEM_PROMPT, user_prompt)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM service error: {e}",
        ) from e

    try:
        settings = get_llm_settings()
        await record_usage(db, "/api/transform", settings.bedrock_llm_model_id, result.usage)
    except Exception:
        logger.warning("Failed to record LLM usage", exc_info=True)

    return TransformResponse(content=result.text)
