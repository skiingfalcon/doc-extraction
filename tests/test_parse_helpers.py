"""CPU-only tests for the Nemotron output helpers in parse.py."""

import types

import pytest

from doc_extraction.parse import _extract_blocks, _is_truncated, _new_token_count

TITLE = "<x_0.1><y_0.05>Northwind Harbor<x_0.5><y_0.07><class_Title>"
BODY = "<x_0.1><y_0.1>Body text here<x_0.9><y_0.3><class_Text>"
PAGE_NUMBER = "<x_0.45><y_0.95>1<x_0.55><y_0.97><class_Page-number>"


def _stub_postprocessing():
    """Mimics the snapshot's extract_classes_bboxes, including its page-number assertion."""
    import re

    pattern = re.compile(
        r"<x_(\d+(?:\.\d+)?)><y_(\d+(?:\.\d+)?)>(.*?)<x_(\d+(?:\.\d+)?)><y_(\d+(?:\.\d+)?)><class_([^>]+)>",
        re.DOTALL,
    )

    def extract_classes_bboxes(text):
        classes, boxes, texts = [], [], []
        for match in pattern.finditer(text):
            x1, y1, body, x2, y2, cls = match.groups()
            classes.append(cls)
            boxes.append((float(x1), float(y1), float(x2), float(y2)))
            texts.append(body)
        assert "Page-number" not in classes
        return classes, boxes, texts

    return types.SimpleNamespace(extract_classes_bboxes=extract_classes_bboxes)


def test_page_number_at_end_keeps_the_rest_of_the_page():
    classes, _boxes, texts, dropped = _extract_blocks(_stub_postprocessing(), TITLE + BODY + PAGE_NUMBER)
    assert classes == ["Title", "Text"]
    assert texts == ["Northwind Harbor", "Body text here"]
    assert dropped is True


def test_page_number_in_the_middle_keeps_both_neighbours():
    classes, _boxes, _texts, dropped = _extract_blocks(_stub_postprocessing(), TITLE + PAGE_NUMBER + BODY)
    assert classes == ["Title", "Text"]
    assert dropped is True


def test_clean_page_is_untouched():
    classes, _boxes, _texts, dropped = _extract_blocks(_stub_postprocessing(), TITLE + BODY)
    assert classes == ["Title", "Text"]
    assert dropped is False


def test_unrelated_assertion_is_not_swallowed():
    def always_fails(_text):
        raise AssertionError("something else")

    with pytest.raises(AssertionError):
        _extract_blocks(types.SimpleNamespace(extract_classes_bboxes=always_fails), TITLE + BODY)


@pytest.mark.parametrize(
    ("count", "budget", "last", "eos", "expected"),
    [
        (120, 9000, 2, 2, False),  # stopped on end-of-sequence
        (9000, 9000, 2, 2, False),  # used the whole budget but still ended cleanly
        (9000, 9000, 517, 2, True),  # ran out of budget mid-output
        (120, 9000, 517, 2, False),  # short and no eos: not a budget problem
        (9000, 9000, 7, [2, 7], False),  # eos given as a list
        (50, None, 517, 2, False),  # no budget configured
    ],
)
def test_is_truncated(count, budget, last, eos, expected):
    assert _is_truncated(count, budget, last, eos) is expected


def test_new_token_count_ignores_batch_padding():
    assert _new_token_count([5, 6, 2, 1, 1, 1], pad_token_id=1) == 3
    assert _new_token_count([5, 6, 2], pad_token_id=1) == 3
    assert _new_token_count([], pad_token_id=1) == 0
