"""classifier.py – paper classification logic"""
import re
from typing import Dict, Any, List


def classify_paper(metadata: Dict[str, Any], rules: Dict[str, Any] = None) -> str:
    """Return a category string based on classification rules."""
    if rules is None:
        rules = {"use_year": True, "use_journal": True, "use_keywords": False,
                 "custom_rules": []}

    parts: List[str] = []

    if rules.get('use_year') and metadata.get('year'):
        parts.append(str(metadata['year']))

    if rules.get('use_journal') and metadata.get('journal'):
        j = _sanitize(metadata['journal'])[:60]
        if j:
            parts.append(j)

    if rules.get('use_keywords') and metadata.get('keywords'):
        kws = [k.strip() for k in metadata['keywords'].split(',') if k.strip()]
        if kws:
            parts.append(kws[0])

    # Custom keyword → category rules
    for rule in (rules.get('custom_rules') or []):
        needle = rule.get('keyword', '').lower()
        if not needle:
            continue
        haystack = " ".join([
            metadata.get('title', ''),
            metadata.get('keywords', ''),
            metadata.get('abstract', ''),
        ]).lower()
        if needle in haystack:
            parts.append(_sanitize(rule['category']))
            break

    return " / ".join(p for p in parts if p) or "미분류"


def suggest_tags(metadata: Dict[str, Any]) -> List[str]:
    tags: List[str] = []
    if metadata.get('keywords'):
        tags += [k.strip() for k in metadata['keywords'].split(',') if k.strip()][:5]
    if metadata.get('journal'):
        tags.append(metadata['journal'][:40])
    return list(dict.fromkeys(tags))  # deduplicate, preserve order


def _sanitize(text: str) -> str:
    """Remove characters unsafe for folder/category names."""
    return re.sub(r'[<>:"/\\|?*]', '', text).strip()
