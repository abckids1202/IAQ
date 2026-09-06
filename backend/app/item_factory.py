"""Deterministic, reviewable pilot item factories.

These factories create candidate variants from explicit rules. They are useful
for expanding the pilot bank and testing the delivery system, but they do not
establish psychometric difficulty or validity. Every generated item remains in
the PILOT lifecycle until a human reviewer promotes it.
"""
from __future__ import annotations

from typing import Any, Dict, List


GENERATION_RUN_ID = "IAQ-FACTORY-2026-09-06"


def _item(
    item_id: str,
    domain: str,
    family: str,
    prompt: str,
    options: List[str],
    answer: str,
    explanation: str,
    kind: str = "choice",
) -> Dict[str, Any]:
    return {
        "id": item_id,
        "item_family_id": family,
        "domain": domain,
        "type": kind,
        "prompt": prompt,
        "options": options,
        "answer": answer,
        "explanation": explanation,
        "difficulty_label": "medium_hard",
        "difficulty_estimate": None,
        "lifecycle_status": "PILOT",
        "status": "PILOT",
        "data_origin": "ORIGINAL_GENERATED",
        "content_version": 1,
        "generation_run_id": GENERATION_RUN_ID,
        "generation_parameters": {"factory": family, "seed": item_id},
    }


def _choice_options(values: List[str], correct_index: int) -> tuple[List[str], str]:
    options = [f"{chr(65 + index)}. {value}" for index, value in enumerate(values)]
    return options, options[correct_index]


def abstract_items() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    directions = ["up", "right", "down", "left"]
    for index in range(1, 21):
        if index % 2:
            start = 4 + index
            step = 3 + index % 4
            values = [start + step * offset for offset in range(4)]
            answer_value = values[-1]
            options, answer = _choice_options([str(values[1] - step), str(answer_value), str(answer_value + step), str(answer_value + step * 2)], 1)
            prompt = f"A sequence changes by the same amount each time: {values[0]}, {values[1]}, {values[2]}, ?. Which number completes it?"
            explanation = f"Each step adds {step}, so the next value is {answer_value}."
        else:
            current = directions[index % 4]
            target = directions[(index + 2) % 4]
            options, answer = _choice_options(directions, directions.index(target))
            prompt = f"A mark points {current}. It turns 90 degrees clockwise twice. Which direction does it point now?"
            explanation = f"Two quarter-turns make a half-turn, taking {current} to {target}."
        items.append(_item(f"ABS-{20 + index:03d}", "abstract_reasoning", f"abstract_factory_{index % 8:02d}", prompt, options, answer, explanation))
    return items


def deductive_items() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    pairs = [
        ("All cedar objects are wooden. This frame is cedar.", "The frame is wooden.", ["The frame is metal.", "The frame is wooden.", "The frame is new.", "Nothing follows."]),
        ("All encrypted files require a key. File R is encrypted.", "File R requires a key.", ["File R is public.", "File R is compressed.", "File R requires a key.", "File R is deleted."]),
        ("Every violinist in the group can read music. Noor is a violinist.", "Noor can read music.", ["Noor writes music.", "Noor can read music.", "Noor plays piano.", "Noor is the group leader."]),
        ("If the sensor is active, the green indicator is lit. The indicator is not lit.", "The sensor is not active.", ["The sensor is active.", "The sensor is not active.", "The battery is full.", "The room is empty."]),
        ("If a route is shorter, it uses fewer kilometres. Route B does not use fewer kilometres.", "Route B is not shorter.", ["Route B is shorter.", "Route B is not shorter.", "Route B is closed.", "Route B has more stops."]),
    ]
    for index in range(1, 21):
        statement, correct, values = pairs[(index - 1) % len(pairs)]
        correct_index = values.index(correct)
        options, answer = _choice_options(values, correct_index)
        items.append(_item(f"LOG-{20 + index:03d}", "deductive_logic", f"logic_factory_{index % 8:02d}", f"{statement} What must be true?", options, answer, "The conclusion follows directly from the stated rule and fact."))
    return items


def numerical_items() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for index in range(1, 21):
        start = 2 + index
        if index % 4 == 1:
            values = [start, start + 3, start + 8, start + 15]
            answer_value = start + 24
            explanation = "The gaps grow by two each time: +3, +5, +7, then +9."
        elif index % 4 == 2:
            values = [start, start * 2, start * 4, start * 8]
            answer_value = start * 16
            explanation = "Each term doubles."
        elif index % 4 == 3:
            values = [start, start + 5, start + 10, start + 15]
            answer_value = start + 20
            explanation = "The sequence adds five each time."
        else:
            values = [start * 2, start * 3, start * 5, start * 8]
            answer_value = start * 13
            explanation = "The multipliers increase by one: ×2, ×3, ×5, then ×8; the next multiplier is ×13." 
        options, answer = _choice_options([str(answer_value - 2), str(answer_value + 3), str(answer_value), str(answer_value + 8)], 2)
        prompt = f"Complete the sequence: {values[0]}, {values[1]}, {values[2]}, {values[3]}, ?."
        items.append(_item(f"NUM-{20 + index:03d}", "numerical_reasoning", f"numerical_factory_{index % 8:02d}", prompt, options, answer, explanation, "sequence"))
    return items


def verbal_items() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    templates = [
        ("Blueprint is to building as recipe is to…", ["cooking", "weather", "distance", "silence"], 0, "A blueprint guides construction; a recipe guides cooking."),
        ("A notice says: ‘The lab opened earlier on Tuesday, and attendance increased.’ What is directly supported?", ["Tuesday attendance increased after the opening time changed", "The lab is always full", "The earlier opening caused every visit", "Attendance fell on Monday"], 0, "The statement supports a sequence and an association, not a universal causal claim."),
        ("Which word is closest in meaning to ‘precise’?", ["exact", "distant", "noisy", "temporary"], 0, "Precise means exact or carefully measured."),
        ("Which item does not belong with the others?", ["maple", "oak", "pine", "granite"], 3, "The first three are trees; granite is rock."),
        ("A report says: ‘Students who reviewed their notes twice recalled more details; the groups were not randomly assigned.’ What is safest?", ["Reviewing was associated with better recall", "Reviewing definitely caused the improvement", "No students reviewed notes", "The groups were identical"], 0, "Without random assignment, the result supports association rather than certainty about cause."),
    ]
    for index in range(1, 21):
        prompt, values, correct_index, explanation = templates[(index - 1) % len(templates)]
        options, answer = _choice_options(values, correct_index)
        items.append(_item(f"VRB-{20 + index:03d}", "verbal_reasoning", f"verbal_factory_{index % 8:02d}", prompt, options, answer, explanation))
    return items


def spatial_items() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    directions = ["north", "east", "south", "west"]
    for index in range(1, 21):
        if index % 2:
            start = directions[index % 4]
            target = directions[(index + 1) % 4]
            values = directions
            correct_index = values.index(target)
            prompt = f"A pointer faces {start}. Rotate it 90 degrees clockwise. Which direction does it face?"
            explanation = f"A clockwise quarter-turn moves {start} to {target}."
        else:
            east = 2 + index % 4
            west = 1 + index % 3
            north = 3 + index % 3
            south = 1 + index % 2
            horizontal = east - west
            vertical = north - south
            horizontal_word = "east" if horizontal > 0 else "west" if horizontal < 0 else "no horizontal movement"
            vertical_word = "north" if vertical > 0 else "south" if vertical < 0 else "no vertical movement"
            correct = f"{abs(horizontal)} {horizontal_word}, {abs(vertical)} {vertical_word}"
            values = [correct, f"{abs(horizontal) + 1} east, {abs(vertical)} north", f"{abs(horizontal)} west, {abs(vertical) + 1} south", "back at the start"]
            correct_index = 0
            prompt = f"Move {east} squares east, {north} north, {west} west, and {south} south. Where are you from the start?"
            explanation = "Combine the horizontal moves and then the vertical moves; opposite directions cancel."
        options, answer = _choice_options(values, correct_index)
        items.append(_item(f"SPA-{20 + index:03d}", "visual_spatial_reasoning", f"spatial_factory_{index % 8:02d}", prompt, options, answer, explanation))
    return items


def memory_items() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for index in range(1, 21):
        sequence = [str((index * 3 + offset * 5) % 10) for offset in range(5)]
        correct_value = " — ".join(sequence)
        distractors = [
            " — ".join(sequence[1:] + sequence[:1]),
            " — ".join(reversed(sequence)),
            " — ".join(sequence[:2] + sequence[3:] + sequence[2:3]),
        ]
        values = [correct_value, *distractors]
        options, answer = _choice_options(values, 0)
        prompt = f"Remember this sequence, then choose the exact match: {' — '.join(sequence)}"
        items.append(_item(f"MEM-{20 + index:03d}", "working_memory", f"memory_factory_{index % 8:02d}", prompt, options, answer, "The correct option preserves every item and its position.", "memory"))
    return items


def speed_items() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for index in range(1, 21):
        target = f"{(index * 137) % 1000:03d}"
        values = [target[::-1], target, target[:-1] + str((int(target[-1]) + 1) % 10), target[1:] + target[0]]
        options, answer = _choice_options(values, 1)
        prompt = f"Find the exact match for the target code {target}."
        items.append(_item(f"SPD-{20 + index:03d}", "processing_speed", f"speed_factory_{index % 8:02d}", prompt, options, answer, "Only the exact target preserves all characters in the same positions.", "speed"))
    return items


def generated_items() -> List[Dict[str, Any]]:
    return abstract_items() + deductive_items() + numerical_items() + verbal_items() + spatial_items() + memory_items() + speed_items()
