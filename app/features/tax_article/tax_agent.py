from __future__ import annotations

import io
import os
import re
import json
import time
from fastapi import UploadFile
from typing import List, Dict, Optional, Any
import PyPDF2
from openai import OpenAI

from app.core.config import get_settings
from .tax_research import TaxResearchAgent

# ----------------------------
# Config & LLM Client
# ----------------------------

OPENAI_API_KEY = get_settings().OPENAI_API_KEY
LLM_CLIENT = OpenAI(api_key=OPENAI_API_KEY)  # GPT-4o-mini client

DATA_DIR = os.path.join(os.path.dirname(__file__), "tax_data")
BLOG_DIR = os.path.join(os.path.dirname(__file__), "blog_posts")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(BLOG_DIR, exist_ok=True)


# ----------------------------
# Utilities
# ----------------------------

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def sanitize_filename(text: str) -> str:
    return re.sub(r"[^a-z0-9-]", "-", text.lower())


# ----------------------------
# Tax Agent (LLM-only)
# ----------------------------

class TaxAgent:
    """Pure LLM-driven Nigerian Tax Research Agent."""

    def __init__(self):
        self.research_agent = TaxResearchAgent()
        self.ingested_texts: List[Dict[str, Any]] = []  # stores ingested statutes

    # -------- Text Ingestion --------

    async def extract_text_from_file(self, file: UploadFile) -> str:
        """Extract text from PDF or TXT file."""
        content = await file.read()
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            text = content.decode("utf-8", errors="ignore")
        return text

    def ingest_text(
        self, 
        text: str, 
        doc_id: Optional[str] = None, 
        section: Optional[str] = None, 
        law: str = "Unknown Law", 
        year: Optional[int] = None
    ) -> None:
        """Store statute excerpts for LLM reference."""
        doc_id = doc_id or f"{law}-{len(self.ingested_texts)}"
        self.ingested_texts.append({
            "id": doc_id,
            "text": text,
            "meta": {"section": section, "law": law, "year": year}
        })

    def ingest_large_text(self, text: str, law: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
        """Chunk large statutes for ingestion."""
        words = text.split()
        ids = []
        idx = 0
        i = 0
        while i < len(words):
            chunk = " ".join(words[i:i + chunk_size])
            doc_id = f"{law}-{idx}"
            self.ingest_text(chunk, doc_id=doc_id, section=f"chunk-{idx}", law=law)
            ids.append(doc_id)
            i += chunk_size - overlap
            idx += 1
        return ids

    # -------- LLM Summarization --------

    def _llm_summarize(self, query: str, statutes: List[Dict[str, Any]]) -> str:
        """Generate concise answer from statutes using GPT-4o-mini."""
        if not statutes:
            return "No relevant statutes ingested to answer this question."

        combined_text = "\n".join([s["text"] for s in statutes])

        prompt = f"""
        You are a Nigerian tax assistant. Using ONLY the Nigerian Tax Act excerpts below,
        answer the following question concisely and clearly. Do NOT quote statutes; give only
        the final answer.

        Question: {query}

        Excerpts:
        {combined_text}

        Answer:
        """
        try:
            resp = LLM_CLIENT.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            return "Unable to generate answer using LLM."

    # -------- Web Fallback --------

    def _web_research(self, query: str, country: Optional[str], top_k: int = 5) -> Dict[str, Any]:
        """Fallback to web-based research if query is cross-country."""
        data = self.research_agent.research(
            topic=query,
            country=country or "",
            use_web=True,
            max_results=top_k
        )
        summary = data.get("summary", "")
        sources = data.get("sources", [])
        return {
            "source": "web_research",
            "confidence": "medium",
            "answer": summary + "\n\n⚠️ *Informational only. Verify with official tax authorities.*",
            "citations": sources
        }

    # -------- Public API --------

    def answer(
        self, 
        query: str, 
        country: Optional[str] = None, 
        compare: bool = False
    ) -> Dict[str, Any]:
        """
        Main entry point: uses LLM for Nigerian statutes, web fallback for others.
        """
        is_nigeria = (country or "").lower() == "nigeria"
        if compare or not is_nigeria:
            return self._web_research(query, country)

        answer_text = self._llm_summarize(query, self.ingested_texts)
        return {
            "source": "nigerian_statute",
            "confidence": "high",
            "answer": answer_text,
            "citations": self.ingested_texts,
            "confidence_score": 0.85,
            "jurisdiction": "Nigeria"
        }

    # -------- Blog / Admin --------

    def publish_blog(self, title: str, body: str, author: str = "tax-bot") -> str:
        """Publish content as a markdown blog post."""
        slug = sanitize_filename(title)
        filename = f"{int(time.time())}-{slug}.md"
        path = os.path.join(BLOG_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
        return path

    def delete_all_ingested(self) -> None:
        """Clear all ingested statutes."""
        self.ingested_texts.clear()
