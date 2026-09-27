"""Score extractor markdown against a memo's ground truth. Pure functions, no ML imports."""

import re
import unicodedata

from rapidfuzz.distance import Levenshtein

_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_ESCAPE = re.compile(r"\\([%$&_#*|\\\[\]().-])")
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")
_ASCII = str.maketrans({
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-",
    "‘": "'", "’": "'", "“": '"', "”": '"', " ": " ",
})


def normalize(text: str) -> str:
    """NFKC, ASCII punctuation, no markdown escapes or emphasis, casefolded, single spaces."""
    text = unicodedata.normalize("NFKC", text).translate(_ASCII)
    text = _ESCAPE.sub(r"\1", text)
    text = text.replace("*", "").replace("_", "")
    return " ".join(text.casefold().split())


def strip_comments(markdown: str) -> str:
    return _COMMENT.sub("", markdown)


def parse_headings(markdown: str) -> list[tuple[int, str]]:
    """``(level, text)`` for every ATX heading line."""
    headings = []
    for line in strip_comments(markdown).splitlines():
        match = _HEADING.match(line.strip())
        if match:
            headings.append((len(match.group(1)), match.group(2)))
    return headings


def heading_score(markdown: str, expected: list[dict]) -> dict:
    """How many truth headings appear as headings, and how many at the right level."""
    found = {}
    for level, text in parse_headings(markdown):
        found.setdefault(normalize(text), level)
    as_heading = [item for item in expected if normalize(item["text"]) in found]
    right_level = [item for item in as_heading if found[normalize(item["text"])] == item["level"]]
    return {
        "expected": len(expected),
        "as_heading": len(as_heading),
        "right_level": len(right_level),
        "misses": [item["text"] for item in expected if item not in as_heading],
        "wrong_level": [
            f"{item['text']} (h{found[normalize(item['text'])]}, expected h{item['level']})"
            for item in as_heading
            if item not in right_level
        ],
    }


def parse_md_tables(markdown: str) -> list[list[list[str]]]:
    """Each run of ``|`` lines becomes a table of rows of cells, without separator rows."""
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in strip_comments(markdown).splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if cells and not all(_SEPARATOR_CELL.match(cell) for cell in cells):
                current.append(cells)
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


def table_score(markdown: str, expected_tables: list[dict]) -> dict:
    """Header match, whole-row recall, and cell recall counted only inside tables."""
    parsed_rows = [
        tuple(normalize(cell) for cell in row)
        for table in parse_md_tables(markdown)
        for row in table
    ]
    row_set = set(parsed_rows)
    cell_set = {cell for row in parsed_rows for cell in row}
    headers = rows = cells = 0
    expected_rows = expected_cells = 0
    missed_rows: list[str] = []
    for table in expected_tables:
        headers += tuple(normalize(cell) for cell in table["header"]) in row_set
        for row in table["rows"]:
            expected_rows += 1
            expected_cells += len(row)
            cells += sum(normalize(cell) in cell_set for cell in row)
            if tuple(normalize(cell) for cell in row) in row_set:
                rows += 1
            else:
                missed_rows.append(" | ".join(row))
    return {
        "tables_found": len(parse_md_tables(markdown)),
        "headers": {"found": headers, "expected": len(expected_tables)},
        "rows": {"found": rows, "expected": expected_rows, "misses": missed_rows},
        "cells_in_tables": {"found": cells, "expected": expected_cells},
    }


def text_similarity(markdown: str, reference: str, furniture: list[str] = ()) -> float:
    """Normalized Levenshtein similarity to the reference, ignoring comments and furniture."""
    text = normalize(strip_comments(markdown))
    for item in furniture:
        text = text.replace(normalize(item), " ")
    text = " ".join(text.split())
    return round(Levenshtein.normalized_similarity(text, normalize(reference)), 4)


def containment_recall(markdown: str, items: list[str]) -> dict:
    """Substring recall after normalization. Only for long or unambiguous strings."""
    haystack = normalize(strip_comments(markdown))
    hits = [item for item in items if normalize(item) in haystack]
    return {
        "found": len(hits),
        "expected": len(items),
        "misses": [item for item in items if item not in hits],
    }


def chart_score(markdown: str, chart: dict) -> dict:
    """Chart labels and values as whole words outside tables, so table cells cannot count."""
    prose = "\n".join(
        line for line in strip_comments(markdown).splitlines() if not line.strip().startswith("|")
    )
    haystack = normalize(prose)

    def recall(items: list[str]) -> dict:
        # Not part of a longer word, price, decimal, or percentage ("15" must not match "$15.20").
        hits = [
            item for item in items
            if re.search(rf"(?<![\w.$]){re.escape(normalize(item))}(?!\w|\.\d|%)", haystack)
        ]
        return {"found": len(hits), "expected": len(items), "misses": [i for i in items if i not in hits]}

    return {"labels": recall(chart["labels"]), "values": recall(chart["values"])}


def furniture_kept(markdown: str, items: list[str]) -> dict:
    """Which repeated page header/footer strings the extractor kept. Not a hit or miss."""
    haystack = normalize(strip_comments(markdown))
    return {item: normalize(item) in haystack for item in items}


def score(markdown: str, truth: dict, reference: str) -> dict:
    return {
        "headings": heading_score(markdown, truth["headings"]),
        "tables": table_score(markdown, truth["tables"]),
        "text_similarity": text_similarity(markdown, reference, truth["page_furniture"]),
        "bullets": containment_recall(markdown, truth["bullets"]),
        "chart": chart_score(markdown, truth["chart"]),
        "page_furniture": furniture_kept(markdown, truth["page_furniture"]),
    }
