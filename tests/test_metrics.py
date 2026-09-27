"""CPU-only tests for the scoring functions."""

import json

import pytest

from doc_extraction.metrics import (
    chart_score,
    heading_score,
    normalize,
    parse_headings,
    parse_md_tables,
    score,
    table_score,
)
from doc_extraction.paths import MEMO_DIR

LAKEFRONT = MEMO_DIR / "digital" / "lakefront"


def _truth():
    return json.loads(LAKEFRONT.with_suffix(".truth.json").read_text(encoding="utf-8"))


def _reference():
    return LAKEFRONT.with_suffix(".reference.md").read_text(encoding="utf-8")


def test_normalize_strips_escapes_emphasis_and_unicode_punctuation():
    assert normalize(r"**18.4\%** of \$42.10") == normalize("18.4% of $42.10")
    assert normalize("Cedar – Pine Partners") == "cedar - pine partners"
    assert normalize(r"Issuer\_name") == "issuername"


def test_parse_headings_reads_levels_and_skips_comments():
    md = "<!-- page 1 -->\n\n# Title\n\n## Section ##\n\nnot # a heading"
    assert parse_headings(md) == [(1, "Title"), (2, "Section")]


def test_heading_score_separates_text_from_level():
    expected = [{"text": "Title", "level": 1}, {"text": "Section", "level": 2}]
    result = heading_score("## Title\n\n## Section", expected)
    assert (result["as_heading"], result["right_level"]) == (2, 1)
    assert result["wrong_level"] == ["Title (h2, expected h1)"]


def test_parse_md_tables_drops_separator_rows():
    md = "| A | B |\n| --- | :---: |\n| 1 | 2 |\n\ntext\n\n| C |\n|---|\n| 3 |"
    assert parse_md_tables(md) == [[["A", "B"], ["1", "2"]], [["C"], ["3"]]]


def test_broken_table_with_cells_in_prose_scores_low():
    """The old substring check gave this 100%: every cell string appears somewhere."""
    truth = _truth()
    cells = [cell for row in truth["tables"][0]["rows"] for cell in row]
    prose = "Holdings: " + ", ".join(cells) + "."
    result = table_score(prose, truth["tables"])
    assert result["rows"]["found"] == 0
    assert result["cells_in_tables"]["found"] == 0


def test_chart_labels_inside_tables_do_not_count():
    chart = {"labels": ["Transportation"], "values": ["15"]}
    in_table = "| Red Maple Tollway | Transportation | 15 |"
    assert chart_score(in_table, chart)["labels"]["found"] == 0
    assert chart_score("Transportation\n\n15", chart)["values"]["found"] == 1
    assert chart_score("$15.20", chart)["values"]["found"] == 0


@pytest.mark.parametrize("variant", ["digital", "scanned"])
def test_reference_scores_perfectly_against_its_own_truth(variant):
    base = MEMO_DIR / variant / "lakefront"
    truth = json.loads(base.with_suffix(".truth.json").read_text(encoding="utf-8"))
    reference = base.with_suffix(".reference.md").read_text(encoding="utf-8")
    result = score(reference, truth, reference)
    assert result["headings"]["right_level"] == result["headings"]["expected"]
    assert result["tables"]["headers"]["found"] == 1
    assert result["tables"]["rows"]["found"] == result["tables"]["rows"]["expected"]
    assert result["text_similarity"] == 1.0
    assert result["bullets"]["found"] == result["bullets"]["expected"]


def test_furniture_is_ignored_by_text_similarity():
    truth, reference = _truth(), _reference()
    with_footer = reference + "\n\n" + truth["page_furniture"][1]
    assert score(with_footer, truth, reference)["text_similarity"] == 1.0
