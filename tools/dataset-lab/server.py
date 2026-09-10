"""Standalone local viewer for the IAQ JSONL assessment banks.

This tool is intentionally separate from the IAQ application. It reads the
private research files from ``data/assessment`` and returns answer keys only
from the explicit local review endpoint after a tester submits an option.
It does not write to the production database, create sessions, or change
review/lifecycle state.
"""
from __future__ import annotations

from collections import Counter
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import random
import urllib.parse
from typing import Any, Dict, Iterable, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data" / "assessment"
HOST = "127.0.0.1"
PORT = 8787

DATASETS = {
    "abstract": {"label": "Abstract reasoning", "path": DATA_ROOT / "five_domains" / "banks" / "abstract_original.jsonl", "asset_root": DATA_ROOT / "five_domains" / "assets" / "abstract", "kind": "visual"},
    "logical": {"label": "Logical reasoning", "path": DATA_ROOT / "five_domains" / "banks" / "logical_original.jsonl", "asset_root": DATA_ROOT / "five_domains" / "assets" / "logical", "kind": "visual"},
    "numerical": {"label": "Numerical reasoning", "path": DATA_ROOT / "five_domains" / "banks" / "numerical_original.jsonl", "asset_root": DATA_ROOT / "five_domains" / "assets" / "numerical", "kind": "visual"},
    "spatial": {"label": "Spatial reasoning", "path": DATA_ROOT / "five_domains" / "banks" / "spatial_original.jsonl", "asset_root": DATA_ROOT / "five_domains" / "assets" / "spatial", "kind": "visual"},
    "memory": {"label": "Working memory", "path": DATA_ROOT / "five_domains" / "banks" / "memory_original.jsonl", "asset_root": DATA_ROOT / "five_domains" / "assets" / "memory", "kind": "visual"},
    "verbal": {"label": "Verbal / reading research", "paths": sorted((DATA_ROOT / "verbal" / "jsonl").glob("*_en_*.jsonl")), "kind": "research"},
}

VISUAL_LABEL_DATASETS = {"abstract", "logical", "numerical", "spatial"}
MEMORY_DATASET = "memory"
MEMORY_RESPONSE_TYPES = {"ordered_sequence", "cell_set"}

CONTENT_ISSUE_PREFIXES = {
    "invalid_json",
    "missing_id",
    "missing_question",
    "options_missing_or_too_short",
    "options_must_have_four_choices",
    "answer_index_missing",
    "answer_index_out_of_range",
    "answer_and_answer_index_disagree",
    "image_missing_or_unresolved",
    "memory_protocol_incomplete",
    "memory_response_type_invalid",
    "memory_stimulus_invalid",
    "memory_answer_invalid",
}
REVIEW_WARNING_ISSUES = {"not_human_reviewed"}
READINESS_WARNING_ISSUES = {"not_calibrated", "not_production_eligible", "commercial_use_not_approved"}

RECORDS: Dict[str, List[Dict[str, Any]]] = {}
BY_ID: Dict[str, Dict[str, Any]] = {}


def _read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                yield {"id": f"invalid:{path.name}:{line_number}", "_parse_error": str(error), "_source_file": path.name}
                continue
            if isinstance(record, dict):
                record["_source_file"] = path.name
                yield record


def _dataset_records(dataset: str) -> List[Dict[str, Any]]:
    config = DATASETS[dataset]
    paths = config.get("paths") or [config["path"]]
    records: List[Dict[str, Any]] = []
    for path in paths:
        records.extend(_read_jsonl(path))
    return records


def _json_equal(left: Any, right: Any) -> bool:
    return json.dumps(left, ensure_ascii=False, sort_keys=True, separators=(",", ":")) == json.dumps(right, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _presentation_mode(dataset: str, record: Optional[Dict[str, Any]] = None) -> str:
    if dataset in VISUAL_LABEL_DATASETS:
        return "visual_labels"
    if dataset == MEMORY_DATASET:
        response_type = (record or {}).get("response_type")
        return "memory_sequence" if response_type == "ordered_sequence" else "memory_grid" if response_type == "cell_set" else "memory_incomplete"
    return "verbal_options"


def _issue_buckets(issues: List[str]) -> Dict[str, List[str]]:
    return {
        "content_issues": [issue for issue in issues if issue in CONTENT_ISSUE_PREFIXES],
        "review_warnings": [issue for issue in issues if issue in REVIEW_WARNING_ISSUES],
        "readiness_warnings": [issue for issue in issues if issue in READINESS_WARNING_ISSUES],
    }


def _is_int_list(value: Any, *, allow_empty: bool = False) -> bool:
    return isinstance(value, list) and (allow_empty or bool(value)) and all(isinstance(item, int) and not isinstance(item, bool) for item in value)


def _asset_for(record: Dict[str, Any], dataset: str) -> Optional[Path]:
    image_path = record.get("image_path")
    config = DATASETS.get(dataset, {})
    root = config.get("asset_root")
    if not image_path or not isinstance(root, Path):
        return None
    if record.get("_asset_checked") is True:
        return root / str(record.get("_asset_name", "")) if record.get("_asset_exists") else None
    candidate = (root / Path(str(image_path)).name).resolve()
    allowed = root.resolve()
    try:
        candidate.relative_to(allowed)
    except ValueError:
        record["_asset_checked"] = True
        record["_asset_exists"] = False
        return None
    record["_asset_checked"] = True
    record["_asset_exists"] = candidate.is_file()
    record["_asset_name"] = candidate.name
    return candidate if record["_asset_exists"] else None


def _issues(record: Dict[str, Any], dataset: str) -> List[str]:
    issues: List[str] = []
    if record.get("_parse_error"):
        issues.append("invalid_json")
    if not record.get("id"):
        issues.append("missing_id")
    if not str(record.get("question") or "").strip():
        issues.append("missing_question")
    if dataset == MEMORY_DATASET:
        response_type = record.get("response_type")
        stimulus = record.get("stimulus")
        answer = record.get("answer")
        if response_type not in MEMORY_RESPONSE_TYPES:
            issues.append("memory_response_type_invalid")
            issues.append("memory_protocol_incomplete")
        elif not isinstance(stimulus, dict):
            issues.append("memory_stimulus_invalid")
            issues.append("memory_protocol_incomplete")
        elif response_type == "ordered_sequence":
            sequence = stimulus.get("sequence")
            if not _is_int_list(sequence) or not _is_int_list(answer) or len(sequence) < 2 or len(sequence) != len(answer):
                issues.append("memory_answer_invalid")
                issues.append("memory_protocol_incomplete")
        elif response_type == "cell_set":
            grid_size = stimulus.get("grid_size")
            filled_cells = stimulus.get("filled_cells")
            max_cell = grid_size * grid_size if isinstance(grid_size, int) and not isinstance(grid_size, bool) and grid_size > 0 else 0
            valid_cells = _is_int_list(filled_cells) and len(set(filled_cells)) == len(filled_cells) and all(0 <= cell < max_cell for cell in filled_cells)
            valid_answer = _is_int_list(answer) and len(set(answer)) == len(answer) and all(0 <= cell < max_cell for cell in answer)
            if not isinstance(grid_size, int) or isinstance(grid_size, bool) or grid_size < 2 or not valid_cells or not valid_answer or set(filled_cells or []) != set(answer or []):
                issues.append("memory_answer_invalid")
                issues.append("memory_protocol_incomplete")
    else:
        options = record.get("options")
        if not isinstance(options, list) or len(options) < 2:
            issues.append("options_missing_or_too_short")
        if dataset in VISUAL_LABEL_DATASETS and isinstance(options, list) and len(options) != 4:
            issues.append("options_must_have_four_choices")
        answer_index = record.get("answer_index")
        if not isinstance(answer_index, int):
            issues.append("answer_index_missing")
        elif not isinstance(options, list) or not 0 <= answer_index < len(options):
            issues.append("answer_index_out_of_range")
        elif "answer" in record and not _json_equal(options[answer_index], record.get("answer")):
            issues.append("answer_and_answer_index_disagree")
    if dataset != "verbal" and record.get("image_path") and not _asset_for(record, dataset):
        issues.append("image_missing_or_unresolved")
    if record.get("review_status") != "reviewed":
        issues.append("not_human_reviewed")
    if record.get("calibrated") is not True:
        issues.append("not_calibrated")
    if record.get("production_eligible") is not True:
        issues.append("not_production_eligible")
    if record.get("commercial_use_approved") is not True:
        issues.append("commercial_use_not_approved")
    return issues


def _load() -> None:
    for dataset in DATASETS:
        records = _dataset_records(dataset)
        for record in records:
            record["_dataset"] = dataset
            record["_issues"] = _issues(record, dataset)
            RECORDS.setdefault(dataset, []).append(record)
            if record.get("id"):
                BY_ID.setdefault(str(record["id"]), record)


def _public_record(record: Dict[str, Any], locale: str = "en") -> Dict[str, Any]:
    dataset = str(record["_dataset"])
    asset = _asset_for(record, dataset)
    prompt = record.get("question_id") if locale == "id" and record.get("question_id") else record.get("question", "")
    presentation_mode = _presentation_mode(dataset, record)
    issues = record.get("_issues", [])
    buckets = _issue_buckets(issues)
    options = record.get("options") or []
    return {
        "id": record.get("id"),
        "dataset": dataset,
        "dataset_label": DATASETS[dataset]["label"],
        "kind": DATASETS[dataset]["kind"],
        "source_file": record.get("_source_file"),
        "domain": record.get("domain"),
        "family": record.get("family"),
        "prompt": prompt,
        "alternate_prompt": record.get("question_id") if locale != "id" else record.get("question"),
        "context": record.get("context"),
        "presentation_mode": presentation_mode,
        "response_type": record.get("response_type"),
        "option_count": len(options) if isinstance(options, list) else 0,
        "options": [] if presentation_mode in {"visual_labels", "memory_sequence", "memory_grid", "memory_incomplete"} else options,
        "stimulus": None if dataset == MEMORY_DATASET else record.get("stimulus"),
        "protocol": record.get("protocol"),
        "image_url": f"/assets/{dataset}/{urllib.parse.quote(asset.name)}" if asset else None,
        "review_status": record.get("review_status", "unknown"),
        "calibrated": record.get("calibrated", False),
        "commercial_use_approved": record.get("commercial_use_approved", False),
        "production_eligible": record.get("production_eligible", False),
        "origin": record.get("origin") or record.get("data_origin"),
        "issues": issues,
        "validation": buckets,
        "can_check": not buckets["content_issues"],
    }


def _summary() -> Dict[str, Any]:
    datasets: Dict[str, Any] = {}
    for dataset, records in RECORDS.items():
        issue_counts = Counter(issue for record in records for issue in record.get("_issues", []))
        issue_buckets = [_issue_buckets(record.get("_issues", [])) for record in records]
        datasets[dataset] = {
            "label": DATASETS[dataset]["label"],
            "count": len(records),
            "with_images": sum(1 for record in records if _asset_for(record, dataset)),
            "reviewed": sum(1 for record in records if record.get("review_status") == "reviewed"),
            "calibrated": sum(1 for record in records if record.get("calibrated") is True),
            "production_eligible": sum(1 for record in records if record.get("production_eligible") is True),
            "issue_counts": dict(issue_counts),
            "content_issue_counts": dict(Counter(issue for bucket in issue_buckets for issue in bucket["content_issues"])),
            "review_warning_counts": dict(Counter(issue for bucket in issue_buckets for issue in bucket["review_warnings"])),
            "readiness_warning_counts": dict(Counter(issue for bucket in issue_buckets for issue in bucket["readiness_warnings"])),
            "content_issue_total": sum(len(bucket["content_issues"]) for bucket in issue_buckets),
            "review_warning_total": sum(len(bucket["review_warnings"]) for bucket in issue_buckets),
            "readiness_warning_total": sum(len(bucket["readiness_warnings"]) for bucket in issue_buckets),
            "source_files": sorted({str(record.get("_source_file")) for record in records}),
        }
    all_records = [record for records in RECORDS.values() for record in records]
    duplicate_ids = [item_id for item_id, count in Counter(str(record.get("id")) for record in all_records).items() if count > 1]
    return {
        "datasets": datasets,
        "total": len(all_records),
        "duplicate_ids": duplicate_ids,
        "balanced_all_mode": "All mode chooses domains evenly, not in proportion to source record counts.",
        "note": "Local research inspection only. No item is treated as production-ready by this tool.",
    }


def _json_response(handler: BaseHTTPRequestHandler, payload: Dict[str, Any], status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class Handler(BaseHTTPRequestHandler):
    server_version = "IAQDatasetLab/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if parsed.path in {"/", "/index.html"}:
            self._file("index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/styles.css":
            self._file("styles.css", "text/css; charset=utf-8")
            return
        if parsed.path == "/app.js":
            self._file("app.js", "text/javascript; charset=utf-8")
            return
        if parsed.path == "/api/summary":
            _json_response(self, _summary())
            return
        if parsed.path == "/api/item":
            dataset = query.get("dataset", ["all"])[0]
            locale = query.get("locale", ["en"])[0]
            excluded = {value for value in query.get("exclude", [""])[0].split(",") if value}
            if dataset == "all":
                available_datasets = [name for name, records in RECORDS.items() if any(str(record.get("id")) not in excluded for record in records)]
                if not available_datasets:
                    _json_response(self, {"error": "No unseen items remain in this filter. Reset the run to continue."}, HTTPStatus.NOT_FOUND)
                    return
                chosen_dataset = random.SystemRandom().choice(available_datasets)
                pool = RECORDS.get(chosen_dataset, [])
            else:
                pool = RECORDS.get(dataset, [])
            pool = [record for record in pool if str(record.get("id")) not in excluded]
            if not pool:
                _json_response(self, {"error": "No unseen items remain in this filter. Reset the run to continue."}, HTTPStatus.NOT_FOUND)
                return
            item = random.SystemRandom().choice(pool)
            _json_response(self, {"item": _public_record(item, locale)})
            return
        if parsed.path == "/api/memory/recall":
            item_id = query.get("id", [""])[0]
            record = BY_ID.get(item_id)
            if not record or record.get("_dataset") != MEMORY_DATASET:
                _json_response(self, {"error": "Memory item not found."}, HTTPStatus.NOT_FOUND)
                return
            content_issues = _issue_buckets(record.get("_issues", []))["content_issues"]
            if content_issues:
                _json_response(self, {"error": "This memory item cannot enter recall because its protocol is incomplete.", "issues": content_issues}, HTTPStatus.UNPROCESSABLE_ENTITY)
                return
            response_type = record.get("response_type")
            answer = record.get("answer")
            stimulus = record.get("stimulus") or {}
            if response_type == "ordered_sequence":
                recall = {
                    "response_type": response_type,
                    "input_length": len(answer),
                    "allowed_digits": list(range(10)),
                    "order_mode": "sequence_entry",
                }
            else:
                recall = {
                    "response_type": response_type,
                    "grid_size": stimulus.get("grid_size"),
                    "input_length": len(answer),
                    "order_mode": "set_selection",
                }
            _json_response(self, {"id": item_id, "recall": recall})
            return
        if parsed.path.startswith("/assets/"):
            parts = parsed.path.split("/", 3)
            if len(parts) == 4:
                dataset, filename = parts[2], urllib.parse.unquote(parts[3])
                asset = _asset_for({"image_path": filename}, dataset)
                if asset:
                    self._binary_file(asset, "image/png")
                    return
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/api/check":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            item_id = str(payload.get("id", ""))
        except (ValueError, TypeError, json.JSONDecodeError):
            _json_response(self, {"error": "Invalid answer payload."}, HTTPStatus.BAD_REQUEST)
            return
        record = BY_ID.get(item_id)
        if not record:
            _json_response(self, {"error": "Item not found."}, HTTPStatus.NOT_FOUND)
            return
        if record.get("_dataset") == MEMORY_DATASET:
            response_type = payload.get("response_type")
            response = payload.get("response")
            expected = record.get("answer")
            content_issues = _issue_buckets(record.get("_issues", []))["content_issues"]
            if content_issues:
                _json_response(self, {"error": "This memory item cannot be checked because its protocol is incomplete.", "issues": content_issues}, HTTPStatus.UNPROCESSABLE_ENTITY)
                return
            if response_type != record.get("response_type") or not _is_int_list(response):
                _json_response(self, {"error": "Invalid memory response payload."}, HTTPStatus.BAD_REQUEST)
                return
            if response_type == "ordered_sequence":
                valid = len(response) == len(expected) and all(0 <= value <= 9 for value in response)
                correct = valid and response == expected
            else:
                grid_size = (record.get("stimulus") or {}).get("grid_size")
                max_cell = grid_size * grid_size
                valid = len(response) == len(set(response)) and all(0 <= value < max_cell for value in response)
                correct = valid and set(response) == set(expected)
            if not valid:
                _json_response(self, {"error": "Memory response is outside the allowed format."}, HTTPStatus.UNPROCESSABLE_ENTITY)
                return
            _json_response(self, {
                "id": item_id,
                "correct": correct,
                "response_type": response_type,
                "submitted_response": response,
                "answer": expected,
                "rule": record.get("rule"),
                "issues": record.get("_issues", []),
                "explanation": record.get("explanation"),
            })
            return
        try:
            answer_index = int(payload.get("answer_index"))
        except (ValueError, TypeError):
            _json_response(self, {"error": "Invalid answer payload."}, HTTPStatus.BAD_REQUEST)
            return
        options = record.get("options") or []
        correct_index = record.get("answer_index")
        if not isinstance(correct_index, int) or not 0 <= answer_index < len(options):
            _json_response(self, {"error": "Answer option is invalid."}, HTTPStatus.UNPROCESSABLE_ENTITY)
            return
        _json_response(self, {
            "id": item_id,
            "correct": answer_index == correct_index,
            "selected_index": answer_index,
            "correct_index": correct_index,
            "answer": record.get("answer"),
            "rule": record.get("rule"),
            "issues": record.get("_issues", []),
            "explanation": record.get("explanation"),
        })

    def _file(self, name: str, content_type: str) -> None:
        path = Path(__file__).with_name(name)
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _binary_file(self, path: Path, content_type: str) -> None:
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    _load()
    counts = ", ".join(f"{name}={len(records)}" for name, records in RECORDS.items())
    print(f"IAQ Dataset Lab: http://{HOST}:{PORT}")
    print(f"Loaded: {counts}")
    print("Research data is read-only; answer keys are revealed only after a local check request.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
