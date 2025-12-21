from fastapi import (
    APIRouter,
    HTTPException,
    UploadFile,
    File,
    Form,
)
from typing import Any, Optional
from pydantic import BaseModel, Field

from app.features.tax_article.tax_agent import TaxAgent


# -------------------------------------------------
# Router & Agent
# -------------------------------------------------

agent_router = APIRouter(
    prefix="/api/tax",
    tags=["Tax Research"],
)

agent = TaxAgent()


# -------------------------------------------------
# Request Models
# -------------------------------------------------

class ResearchRequest(BaseModel):
    query: str = Field(..., description="Tax topic or question")
    country: Optional[str] = Field(
        default="Nigeria",
        description="Jurisdiction (e.g. Nigeria, Germany)",
    )
    compare: Optional[bool] = Field(
        default=False,
        description="Enable cross-country comparison",
    )
    top_k: Optional[int] = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of statute chunks / sources",
    )


class PublishBlogRequest(BaseModel):
    title: str = Field(..., description="Blog title")
    body: str = Field(..., description="Markdown content")
    author: Optional[str] = Field(default="tax-bot")


# -------------------------------------------------
# Endpoints
# -------------------------------------------------

@agent_router.post("/research", summary="Research a tax topic")
def research_tax(req: ResearchRequest) -> Any:
    """
    Research tax laws using:
    - Local statute vectors (Nigeria)
    - Web research (comparative / foreign)

    ⚠️ Informational only. Not tax advice.
    """
    return agent.answer(
        query=req.query,
        country=req.country,
        compare=req.compare,
    )


# -------------------------------------------------
# Document Upload & Ingestion
# -------------------------------------------------

@agent_router.post("/documents/upload", status_code=201, summary="Upload and ingest a tax document")
async def upload_tax_document(
    file: UploadFile = File(...),
    law: str = Form(..., description="Law name (e.g. Personal Income Tax Act)"),
    year: int = Form(..., description="Year of enactment"),
    section: Optional[str] = Form(
        default=None,
        description="Optional section reference",
    ),
    doc_id: Optional[str] = Form(
        default=None,
        description="Optional explicit document ID",
    ),
) -> Any:
    """
    Upload and ingest a tax document (PDF, DOCX, TXT).

    The document is:
    - Text-extracted
    - Chunked
    - Stored in the vector database
    """
    try:
        text = await agent.extract_text_from_file(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    prefix = doc_id or f"{law.lower().replace(' ', '_')}_{year}"

    ids = agent.ingest_large_text(
        text=text,
        law=prefix,
    )

    return {
        "status": "success",
        "doc_id": prefix,
        "chunks_ingested": len(ids),
        "chunk_ids": ids,
    }


# -------------------------------------------------
# Document Deletion
# -------------------------------------------------

@agent_router.delete("/documents/{doc_id}", summary="Delete ingested tax document")
def delete_tax_document(doc_id: str) -> Any:
    """
    Delete an ingested law or section by document ID prefix.
    """
    deleted = agent.delete_by_prefix(doc_id)

    if deleted == 0:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    return {
        "status": "deleted",
        "doc_id": doc_id,
        "chunks_removed": deleted,
    }


# -------------------------------------------------
# Blog Publishing
# -------------------------------------------------

@agent_router.post("/publish/blog", summary="Publish tax blog post")
def publish_blog(req: PublishBlogRequest) -> Any:
    """
    Publish a markdown blog post generated from tax research.
    """
    path = agent.publish_blog(
        title=req.title,
        body=req.body,
        author=req.author,
    )

    return {
        "status": "published",
        "path": path,
    }
