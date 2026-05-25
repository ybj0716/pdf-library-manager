import re
import requests
from typing import Optional, Dict, Any

CROSSREF_BASE = "https://api.crossref.org/works"
SS_BASE = "https://api.semanticscholar.org/graph/v1/paper"
SS_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search"

HEADERS = {"User-Agent": "PDF-Manager/1.0 (Academic Library Tool)"}
TIMEOUT = 12


def fetch_metadata(doi: Optional[str], title: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Main entry point. Try DOI first, then title search.
    Returns normalized metadata dict or None.
    """
    if doi:
        result = _crossref_by_doi(doi)
        if result:
            return result
        result = _semantic_scholar_by_doi(doi)
        if result:
            return result

    if title:
        result = _crossref_by_title(title)
        if result:
            return result
        result = _semantic_scholar_by_title(title)
        if result:
            return result

    return None


# ── CrossRef ──────────────────────────────────────────────────────────────────

def _crossref_by_doi(doi: str) -> Optional[Dict[str, Any]]:
    try:
        resp = requests.get(f"{CROSSREF_BASE}/{doi}", headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 200:
            return _parse_crossref(resp.json()['message'])
    except Exception as e:
        print(f"[CrossRef DOI] {e}")
    return None


def _crossref_by_title(title: str) -> Optional[Dict[str, Any]]:
    try:
        params = {
            "query.title": title,
            "rows": 1,
            "select": "DOI,title,author,published,published-print,published-online,"
                      "container-title,abstract,subject,type"
        }
        resp = requests.get(CROSSREF_BASE, params=params, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 200:
            items = resp.json()['message'].get('items', [])
            if items:
                return _parse_crossref(items[0])
    except Exception as e:
        print(f"[CrossRef Title] {e}")
    return None


def _parse_crossref(data: Dict) -> Dict[str, Any]:
    authors = ", ".join(
        f"{a.get('family', '')} {a.get('given', '')}".strip()
        for a in data.get('author', [])
    )

    titles = data.get('title', [])
    title = titles[0] if titles else ""

    year = None
    for field in ('published', 'published-print', 'published-online'):
        pub = data.get(field)
        if pub and 'date-parts' in pub:
            parts = pub['date-parts']
            if parts and parts[0]:
                year = parts[0][0]
                break

    container = data.get('container-title', [])
    journal = container[0] if container else ""

    abstract = re.sub(r'<[^>]+>', '', data.get('abstract', ''))

    subjects = data.get('subject', [])
    keywords = ", ".join(subjects[:8])

    return {
        'title': title,
        'authors': authors,
        'year': year,
        'journal': journal,
        'doi': data.get('DOI', ''),
        'abstract': abstract.strip(),
        'keywords': keywords,
        'metadata_source': 'CrossRef',
    }


# ── Semantic Scholar ──────────────────────────────────────────────────────────

def _semantic_scholar_by_doi(doi: str) -> Optional[Dict[str, Any]]:
    try:
        fields = "title,authors,year,venue,abstract,externalIds"
        resp = requests.get(
            f"{SS_BASE}/DOI:{doi}",
            params={"fields": fields},
            headers=HEADERS, timeout=TIMEOUT
        )
        if resp.status_code == 200:
            return _parse_semantic_scholar(resp.json())
    except Exception as e:
        print(f"[SemanticScholar DOI] {e}")
    return None


def _semantic_scholar_by_title(title: str) -> Optional[Dict[str, Any]]:
    try:
        fields = "title,authors,year,venue,abstract,externalIds"
        resp = requests.get(
            SS_SEARCH,
            params={"query": title, "fields": fields, "limit": 1},
            headers=HEADERS, timeout=TIMEOUT
        )
        if resp.status_code == 200:
            data = resp.json().get('data', [])
            if data:
                return _parse_semantic_scholar(data[0])
    except Exception as e:
        print(f"[SemanticScholar Title] {e}")
    return None


def _parse_semantic_scholar(data: Dict) -> Dict[str, Any]:
    authors = ", ".join(a.get('name', '') for a in data.get('authors', []))
    ext = data.get('externalIds') or {}
    doi = ext.get('DOI', '')
    return {
        'title': data.get('title', ''),
        'authors': authors,
        'year': data.get('year'),
        'journal': data.get('venue', ''),
        'doi': doi,
        'abstract': data.get('abstract', '') or '',
        'keywords': '',
        'metadata_source': 'Semantic Scholar',
    }
