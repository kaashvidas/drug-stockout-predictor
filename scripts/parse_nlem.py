"""
Parse the real NLEM 2022 PDF (downloaded from CDSCO) into a structured drug catalog.

Source: https://cdsco.gov.in/opencms/resources/UploadCDSCOWeb/2018/UploadConsumer/nlem2022.pdf
This is the actual, official National List of Essential Medicines 2022 document.
Every drug name, code, level-of-care and section below is extracted directly from
the PDF text -- nothing in this catalog is invented.
"""
import json
import re
from pathlib import Path

from pypdf import PdfReader

RAW_PDF = Path(__file__).resolve().parent.parent / "data" / "raw" / "nlem2022.pdf"
OUT_JSON = Path(__file__).resolve().parent.parent / "data" / "processed" / "nlem_catalog.json"

HEADER_JUNK = re.compile(
    r"Medicine\s+Level\s+of\s+Healthcare\s+Dosage\s+form\(s\)\s+and\s+strength\(s\)",
    re.IGNORECASE,
)
SECTION_HDR_RE = re.compile(r"^Section\s+(\d+)\s*$")
SECTION_INLINE_RE = re.compile(r"^Section\s+(\d+)\s*[\-\.]?\s*(.+)$")
SUBSECTION_RE = re.compile(r"^(\d{1,2}\.\d{1,2})\s*[\-\.]\s*(?!\d)([A-Z].+)$")

# A medicine record begins with a code like 5.1.10 / 26.1 / 5.2.1.1 followed by a name
# that starts with a capital letter (or digit, e.g. combination drugs) and continues
# until we hit the level-of-care token (one or more of P/S/T, comma separated).
CODE_START_RE = re.compile(r"(?<![\d.])(\d{1,2}(?:\.\d{1,2}){1,3})\s+(?=[A-Z(])")
LEVEL_RE = re.compile(r"\b((?:P|S|T)(?:\s*,\s*(?:P|S|T)){0,2})\b")


def extract_all_text(pdf_path: Path) -> list[str]:
    reader = PdfReader(str(pdf_path))
    return [page.extract_text() or "" for page in reader.pages]


def clean_page_text(raw: str) -> str:
    text = HEADER_JUNK.sub(" ", raw)
    # collapse newlines that are just word-wraps into spaces, but keep track of
    # section boundaries by inserting explicit markers first
    text = re.sub(r"\n", " \n", text)
    return text


def find_sections(lines: list[str]) -> dict:
    """Map line index -> (section_num, section_title) for header lookups."""
    return {}


def parse_catalog(pages: list[str]) -> list[dict]:
    entries = []
    current_section_num = None
    current_section_title = None
    current_subsection_num = None
    current_subsection_title = None

    for page_text in pages:
        raw_lines = [l.strip() for l in page_text.split("\n") if l.strip()]
        idx = 0
        while idx < len(raw_lines):
            line = raw_lines[idx]
            m_sec = SECTION_HDR_RE.match(line)
            if m_sec:
                current_section_num = m_sec.group(1)
                if idx + 1 < len(raw_lines):
                    current_section_title = raw_lines[idx + 1]
                    idx += 1
                idx += 1
                continue
            idx += 1

        # Now work on a joined blob for this page to catch multi-line records,
        # re-walking to also update subsection titles inline.
        blob_parts = []
        current_section_num_p = current_section_num
        current_section_title_p = current_section_title
        idx = 0
        while idx < len(raw_lines):
            line = raw_lines[idx]
            m_sec = SECTION_HDR_RE.match(line)
            if m_sec:
                current_section_num_p = m_sec.group(1)
                if idx + 1 < len(raw_lines):
                    current_section_title_p = raw_lines[idx + 1]
                    blob_parts.append(("__SECTION__", current_section_num_p, current_section_title_p))
                    idx += 2
                    continue
            m_sub = SUBSECTION_RE.match(line)
            if m_sub and not line.lower().startswith("section"):
                blob_parts.append(("__SUBSECTION__", m_sub.group(1), m_sub.group(2).strip()))
                idx += 1
                continue
            m_sub_inline = re.match(r"^(\d{1,2}\.\d{1,2})[\-\.]\s*([A-Z][A-Za-z ,/\-]+)$", line)
            if m_sub_inline:
                blob_parts.append(("__SUBSECTION__", m_sub_inline.group(1), m_sub_inline.group(2).strip()))
                idx += 1
                continue
            blob_parts.append(("__TEXT__", line))
            idx += 1

        # Build final text blob while tracking section/subsection at each text token
        text_tokens = []
        for part in blob_parts:
            if part[0] == "__SECTION__":
                current_section_num = part[1]
                current_section_title = part[2]
            elif part[0] == "__SUBSECTION__":
                current_subsection_num = part[1]
                current_subsection_title = part[2]
            else:
                text_tokens.append((part[1], current_section_num, current_section_title,
                                     current_subsection_num, current_subsection_title))

        joined = " ".join(t[0] for t in text_tokens)
        joined = re.sub(r"\s+", " ", joined)

        # Split on medicine code boundaries
        matches = list(CODE_START_RE.finditer(joined))
        for i, m in enumerate(matches):
            code = m.group(1)
            # only accept 3+ segment codes as true medicine entries (X.Y.Z[.W])
            if code.count(".") < 2:
                continue
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(joined)
            chunk = joined[start:end].strip()

            level_match = LEVEL_RE.search(chunk)
            if not level_match:
                continue
            name = chunk[: level_match.start()].strip(" *,-")
            name = re.sub(r"\*+", "", name).strip()
            name = re.sub(r"\s+", " ", name)
            if not name or len(name) > 80 or not re.match(r"^[A-Za-z(]", name):
                continue
            level = re.sub(r"\s*,\s*", ",", level_match.group(1))

            entries.append(
                {
                    "code": code,
                    "name": name,
                    "level_of_healthcare": level,
                    "section": current_section_num,
                    "section_title": current_section_title,
                }
            )

    return entries


def dedupe(entries: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for e in entries:
        key = (e["code"], e["name"].lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def main():
    print(f"Reading {RAW_PDF} ...")
    pages = extract_all_text(RAW_PDF)
    print(f"Extracted text from {len(pages)} pages")

    entries = parse_catalog(pages)
    entries = dedupe(entries)
    print(f"Parsed {len(entries)} unique medicine entries")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    print(f"Wrote catalog to {OUT_JSON}")

    sections = sorted(set((e["section"], e["section_title"]) for e in entries if e["section"]))
    print(f"Distinct sections represented: {len(sections)}")
    for s in sections:
        print("  ", s)


if __name__ == "__main__":
    main()
