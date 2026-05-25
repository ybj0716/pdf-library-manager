import re
from pathlib import Path
from typing import Optional, Tuple

DOI_PATTERN = re.compile(r'10\.\d{4,9}/[-._;()/:\w]+', re.IGNORECASE)


def extract_doi_and_title(pdf_path: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract DOI and potential title from PDF using pymupdf."""
    try:
        import fitz  # pymupdf
        doc = fitz.open(pdf_path)

        meta = doc.metadata
        doi: Optional[str] = None
        title: Optional[str] = None

        # Check internal PDF metadata for title
        if meta.get('title') and len(meta['title'].strip()) > 5:
            title = meta['title'].strip()

        # Extract text from first 3 pages
        text = ""
        for i in range(min(3, len(doc))):
            text += doc[i].get_text()
        doc.close()

        # Search for DOI
        doi_matches = DOI_PATTERN.findall(text)
        if doi_matches:
            doi = re.sub(r'[.,;)\]\s]+$', '', doi_matches[0])

        # If no title from metadata, try to extract from first page text
        if not title and text:
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            for line in lines[:15]:
                # Skip lines that look like headers, page numbers, or URLs
                if (len(line) > 25
                        and not line.lower().startswith('http')
                        and not re.match(r'^\d+[\s\.]', line)
                        and not re.match(r'^(abstract|introduction|doi|vol|volume)', line, re.I)
                        and len(line) < 250):
                    title = line
                    break

        return doi, title

    except ImportError:
        # Fallback: try basic binary scan for DOI
        return _extract_doi_from_bytes(pdf_path), None
    except Exception as e:
        print(f"PDF 처리 오류 ({Path(pdf_path).name}): {e}")
        return None, None


def _extract_doi_from_bytes(pdf_path: str) -> Optional[str]:
    """Fallback: scan raw PDF bytes for DOI pattern."""
    try:
        with open(pdf_path, 'rb') as f:
            content = f.read(50000).decode('latin-1', errors='ignore')
        matches = DOI_PATTERN.findall(content)
        if matches:
            return re.sub(r'[.,;)\]\s]+$', '', matches[0])
    except Exception:
        pass
    return None
