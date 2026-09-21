"""Read-only presentation helpers shared by the assessment and Dataset Lab.

Render panels from their coordinates, never by masking parts of a source PNG.
Only the matrix and the four choices are used; answer keys and rules are not.
"""
from __future__ import annotations

import re
from typing import Any


def verbal_question(question: Any, context: Any) -> str:
    prompt = str(question or "").strip()
    passage = str(context or "").strip()
    if passage:
        # Research exports may prepend the passage with different whitespace.
        prefix = r"^" + r"\s+".join(re.escape(word) for word in passage.split())
        match = re.match(prefix + r"(?=$|\s|[:.\u2014\u2013-])", prompt, re.IGNORECASE)
        if match:
            prompt = prompt[match.end():].lstrip(" \n\r\t:.-\u2014\u2013")
    return prompt or "Choose the best answer."


def validate_matrix(stimulus: Any, options: Any) -> None:
    matrix = stimulus.get("matrix") if isinstance(stimulus, dict) else None
    if not isinstance(matrix, list) or len(matrix) != 3 or any(not isinstance(row, list) or len(row) != 3 for row in matrix):
        raise ValueError("Expected a 3 by 3 panel matrix")
    panels = [panel for row in matrix for panel in row]
    if sum(panel is None for panel in panels) != 1:
        raise ValueError("Expected exactly one missing panel")
    if not isinstance(options, list) or len(options) != 4:
        raise ValueError("Expected four visual options")
    populated = [panel for panel in panels if panel is not None] + options
    first = populated[0]
    size = len(first) if isinstance(first, list) else 0
    if size not in {3, 4}:
        raise ValueError("Expected a 3 by 3 or 4 by 4 binary panel")
    for panel in populated:
        if not isinstance(panel, list) or len(panel) != size:
            raise ValueError("Inconsistent panel sizes")
        for row in panel:
            if not isinstance(row, list) or len(row) != size or any(type(cell) is not int or cell not in (0, 1) for cell in row):
                raise ValueError("Invalid panel cells")


def render_matrix_svg(stimulus: Any, options: Any) -> str:
    validate_matrix(stimulus, options)
    matrix = stimulus["matrix"]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 560" role="img" aria-labelledby="title">',
        '<title id="title">Pattern matrix with one missing panel and choices A, B, C, D</title>',
        '<rect width="720" height="560" fill="white"/>',
    ]

    def panel_svg(panel: list, x: int, y: int, width: int) -> None:
        cell_size = width / len(panel)
        for row, cells in enumerate(panel):
            for col, value in enumerate(cells):
                fill = "#17313D" if value else "white"
                parts.append(f'<rect x="{x + col * cell_size:g}" y="{y + row * cell_size:g}" width="{cell_size:g}" height="{cell_size:g}" fill="{fill}" stroke="#B7C6CF" stroke-width="1"/>')

    for row, panels in enumerate(matrix):
        for col, panel in enumerate(panels):
            x, y = 198 + col * 120, 32 + row * 120
            parts.append(f'<g data-matrix-row="{row}" data-matrix-col="{col}">')
            if panel is None:
                parts.append(f'<rect x="{x}" y="{y}" width="84" height="84" fill="white" stroke="#B7C6CF" stroke-dasharray="4 4"/>')
                parts.append(f'<text data-missing-panel="true" x="{x + 42}" y="{y + 42}" text-anchor="middle" dominant-baseline="central" font-family="Arial, sans-serif" font-size="36" fill="#17313D">?</text>')
            else:
                panel_svg(panel, x, y, 84)
            parts.append('</g>')
    for index, panel in enumerate(options):
        label, x = chr(65 + index), 36 + index * 174
        parts.append(f'<g data-option="{label}"><text x="{x}" y="396" font-family="Arial, sans-serif" font-size="20" fill="#17313D">{label}</text>')
        panel_svg(panel, x, 410, 126)
        parts.append('</g>')
    return "".join(parts) + "</svg>"
