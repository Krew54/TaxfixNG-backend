"""
TaxResearchAgent (Compliance-Safe)

Purpose:
- Provide jurisdiction-aware tax research summaries
- Prefer deterministic statutory summaries for Nigeria
- Use lightweight web research ONLY for cross-border or non-local queries
- Produce citation-ready, non-interpretive outputs

IMPORTANT:
This module performs INFORMATIONAL RESEARCH ONLY.
It does NOT provide tax advice or legal interpretation.
"""

from typing import List, Dict, Optional
import re
import requests
from urllib.parse import urlencode

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except Exception:
    BeautifulSoup = None  # type: ignore
    HAS_BS4 = False


# ----------------------------
# Tax Research Agent
# ----------------------------

class TaxResearchAgent:
    """
    Lightweight, compliance-aware tax research agent.

    Outputs are designed to be consumed by TaxAgent and MUST NOT
    contain interpretation or recommendations.
    """

    USER_AGENT = "tax-research-agent/2.0"
    DDG_HTML = "https://duckduckgo.com/html"

    def __init__(self, timeout: int = 8):
        self.session = requests.Session()
        self.timeout = timeout
        self.session.headers.update({"User-Agent": self.USER_AGENT})

    # --------------------------------------------------
    # Deterministic Nigeria Statutory Summary
    # --------------------------------------------------

    def nigeria_pit_statutory_summary(self) -> str:
        """
        Deterministic, statute-aligned summary of Nigerian Personal Income Tax.
        Mirrors statutory structure and app logic.
        """
        return (
            "Nigeria Personal Income Tax (PIT) operates under the Personal Income Tax Act (PITA). "
            "Tax is charged on chargeable income after allowable deductions. "
            "Chargeable income is derived from assessable income less capital allowances "
            "and permitted reliefs. "
            "Progressive tax bands commonly applied are: "
            "0% on the first ₦800,000; "
            "15% on the next ₦2,200,000; "
            "18% on the next ₦9,000,000; "
            "21% on the next ₦13,000,000; "
            "23% on the next ₦25,000,000; "
            "25% on income above ₦50,000,000. "
            "Allowable deductions typically include pension contributions, "
            "National Housing Fund (NHF), National Health Insurance Scheme (NHIS), "
            "life insurance premiums, and mortgage interest. "
            "Consolidated Relief Allowance (CRA) applies at 20% of gross income "
            "plus ₦200,000, subject to statutory conditions."
        )

    # --------------------------------------------------
    # DuckDuckGo Search (HTML-only)
    # --------------------------------------------------

    def _duckduckgo_search(self, query: str, limit: int) -> List[Dict[str, str]]:
        params = {"q": query}
        url = f"{self.DDG_HTML}?{urlencode(params)}"

        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()

        results: List[Dict[str, str]] = []
        html = resp.text

        if HAS_BS4 and BeautifulSoup:
            soup = BeautifulSoup(html, "html.parser")
            anchors = soup.select("a.result__a")

            for a in anchors:
                href = a.get("href")
                if not href or not href.startswith("http"):
                    continue

                snippet = ""
                parent = a.find_parent("div")
                if parent:
                    p = parent.find("p")
                    if p:
                        snippet = p.get_text(strip=True)

                results.append({"url": href, "snippet": snippet})
                if len(results) >= limit:
                    break
        else:
            for match in re.finditer(r"https?://[^\s\"'>]+", html):
                results.append({"url": match.group(0), "snippet": ""})
                if len(results) >= limit:
                    break

        return results

    # --------------------------------------------------
    # Page Fetch (Small, Safe Extract)
    # --------------------------------------------------

    def _fetch_page_excerpt(self, url: str) -> str:
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()

            text = resp.text
            if HAS_BS4 and BeautifulSoup:
                soup = BeautifulSoup(text, "html.parser")
                paragraphs = [
                    p.get_text(strip=True)
                    for p in soup.find_all("p")
                    if len(p.get_text(strip=True)) > 40
                ]
                return "\n\n".join(paragraphs[:2])

            clean = re.sub(r"<[^>]+>", "", text)
            clean = re.sub(r"\s+", " ", clean)
            return clean[:1200]

        except Exception:
            return ""

    # --------------------------------------------------
    # Extractive Summary (Non-Interpretive)
    # --------------------------------------------------

    def _extractive_summary(self, texts: List[str], max_sentences: int = 5) -> str:
        joined = " ".join(texts)
        sentences = re.split(r"(?<=[.!?])\s+", joined)

        picked = []
        for s in sentences:
            s = s.strip()
            if len(s) < 40:
                continue
            picked.append(s)
            if len(picked) >= max_sentences:
                break

        return " ".join(picked) if picked else joined[:800]

    # --------------------------------------------------
    # Public Research API (Used by TaxAgent)
    # --------------------------------------------------

    def research(
        self,
        topic: str,
        country: str,
        use_web: bool = True,
        max_results: int = 5
    ) -> Dict[str, object]:
        """
        Research tax topics by jurisdiction.

        Returns:
        {
            "query": str,
            "country": str,
            "summary": str,
            "sources": [{ "url": str, "snippet": str }]
        }
        """

        query = f"{country} {topic} tax law"

        # --- Nigeria: deterministic statutory summary ---
        if country.lower() == "nigeria" and not use_web:
            return {
                "query": query,
                "country": "Nigeria",
                "summary": self.nigeria_pit_statutory_summary(),
                "sources": [
                    {
                        "url": "local://pita",
                        "note": "Personal Income Tax Act (Nigeria) – deterministic statutory summary"
                    }
                ],
            }

        # --- Web research path ---
        results = self._duckduckgo_search(query, max_results)
        texts: List[str] = []
        sources: List[Dict[str, str]] = []

        for r in results:
            url = r.get("url")
            snippet = r.get("snippet", "")
            page_text = self._fetch_page_excerpt(url) if url else ""
            texts.append(snippet or page_text)
            sources.append({
                "url": url,
                "snippet": (snippet or page_text[:300])
            })

        summary = self._extractive_summary(texts)

        # Nigeria + web → add statutory context
        if country.lower() == "nigeria":
            summary = (
                self.nigeria_pit_statutory_summary()
                + "\n\nAdditional publicly available commentary:\n"
                + summary
            )

        return {
            "query": query,
            "country": country,
            "summary": summary,
            "sources": sources
        }
