import copy
import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient

from app import external_data, main, staged_assessment
from app.question_presentation import render_matrix_svg, validate_matrix, verbal_question

NS = {"s": "http://www.w3.org/2000/svg"}
PANEL = [[0, 1, 0], [1, 0, 0], [0, 0, 1]]


def fixture_visual(row=2, col=2):
    matrix = [[copy.deepcopy(PANEL) for _ in range(3)] for _ in range(3)]
    matrix[row][col] = None
    return {"matrix": matrix}, [copy.deepcopy(PANEL) for _ in range(4)]


@pytest.mark.parametrize("row,col", [(r, c) for r in range(3) for c in range(3)])
def test_marker_is_centered_in_the_actual_missing_panel(row, col):
    stimulus, options = fixture_visual(row, col)
    before = copy.deepcopy(stimulus)
    svg = ET.fromstring(render_matrix_svg(stimulus, options))
    markers = svg.findall('.//s:text[@data-missing-panel="true"]', NS)
    assert len(markers) == 1
    marker = markers[0]
    assert marker.text == "?"
    assert marker.attrib["x"] == str(240 + col * 120)
    assert marker.attrib["y"] == str(74 + row * 120)
    missing = svg.find(f's:g[@data-matrix-row="{row}"][@data-matrix-col="{col}"]', NS)
    assert marker in missing
    # Every populated panel keeps all of its cells and each option keeps its order.
    for r, panels in enumerate(stimulus["matrix"]):
        for c, panel in enumerate(panels):
            if panel is not None:
                group = svg.find(f's:g[@data-matrix-row="{r}"][@data-matrix-col="{c}"]', NS)
                assert [node.attrib["fill"] for node in group.findall('s:rect', NS)] == ["#17313D" if cell else "white" for cells in panel for cell in cells]
    assert [group.attrib["data-option"] for group in svg.findall('s:g[@data-option]', NS)] == list("ABCD")
    assert stimulus == before


@pytest.mark.parametrize("prompt,passage,expected", [
    ("Passage text. Which is true?", "Passage text.", "Which is true?"),
    ("Passage\ntext.\n\nWhich is true?", "Passage text.", "Which is true?"),
    ("PASSAGE TEXT.", "Passage text.", "Choose the best answer."),
    ("Which is true?", "Passage text.", "Which is true?"),
    ("Higher values are possible?", "High", "Higher values are possible?"),
    (None, None, "Choose the best answer."),
])
def test_verbal_prompt_does_not_repeat_the_passage(prompt, passage, expected):
    assert verbal_question(prompt, passage) == expected


def test_invalid_matrix_does_not_fall_back_to_a_misplaced_png():
    stimulus, options = fixture_visual()
    stimulus["matrix"][0][0] = None
    with pytest.raises(ValueError):
        validate_matrix(stimulus, options)
    item = staged_assessment._choice_item({
        "id": "invalid-matrix", "domain": "abstract_reasoning",
        "asset_path": "five_domains/assets/abstract/test.png", "asset_exists": True,
        "source_record": {"stimulus": stimulus, "options": options, "answer_index": 2},
    })
    assert item["image_url"] is None


def test_real_matrix_image_endpoint_preserves_choices_and_hides_keys(monkeypatch):
    candidate = external_data.preview_items(limit=1, domain="abstract_reasoning")[0]
    item = staged_assessment._choice_item(candidate)
    monkeypatch.setattr(main, "ASSESSMENT_SOURCE", "staged")
    monkeypatch.setitem(main.ITEMS, item["id"], item)
    with TestClient(main.app) as client:
        response = client.get(item["image_url"])
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/svg+xml")
        svg = ET.fromstring(response.text)
        for label, panel in zip("ABCD", candidate["source_record"]["options"]):
            group = svg.find(f's:g[@data-option="{label}"]', NS)
            assert [node.attrib["fill"] for node in group.findall('s:rect', NS)] == ["#17313D" if value else "white" for row in panel for value in row]
        for key in ("answer", "answer_index", "rule", "matrix_visual"):
            assert key not in main.public_item(item)
            assert key not in response.text
        assert item["answer"] == "ABCD"[candidate["answer_index"]]
        monkeypatch.setattr(main, "ASSESSMENT_SOURCE", "authored")
        assert client.get(item["image_url"]).status_code == 404


def test_every_imported_abstract_matrix_renders_without_modifying_its_data():
    path = external_data.assessment_root() / "five_domains" / "banks" / "abstract_original.jsonl"
    count = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            before = copy.deepcopy(record)
            svg = ET.fromstring(render_matrix_svg(record["stimulus"], record["options"]))
            assert len(svg.findall('.//s:text[@data-missing-panel="true"]', NS)) == 1
            assert record == before
            count += 1
    assert count == 2000


def test_dataset_lab_uses_the_same_matrix_renderer_and_verbal_normalizer():
    path = Path(__file__).resolve().parents[2] / "tools" / "dataset-lab" / "server.py"
    spec = importlib.util.spec_from_file_location("dataset_lab_presentation_test", path)
    lab = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lab)
    stimulus, options = fixture_visual()
    record = {"id": "abstract-preview", "_dataset": "abstract", "stimulus": stimulus, "options": options, "question": "Which panel is missing?"}
    assert lab._public_record(record)["image_url"] == "/stimuli/abstract-preview.svg"
    assert lab.render_matrix_svg(stimulus, options) == render_matrix_svg(stimulus, options)
    verbal = {"id": "verbal-preview", "_dataset": "verbal", "question": "Passage. Which is true?", "context": "Passage.", "options": ["a", "b", "c", "d"]}
    assert lab._public_record(verbal)["prompt"] == "Which is true?"
    assert lab._public_record(verbal)["context"] == "Passage."
