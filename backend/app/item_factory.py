"""Deterministic IAQ candidate factories.

These factories create original, reproducible pilot candidates. They are not
scientific norming and they never make an item active by themselves. Every
candidate carries its seed and factory parameters so reviewers can reproduce
the exact stimulus and independently verify the answer.
"""
from __future__ import annotations

import random
from typing import Any, Dict, Iterable, List, Sequence, Tuple

GENERATED_PER_DOMAIN = 100
FACTORY_SEED = "iaq-v2-medium-hard-2026-09"


def _item(item_id: str, domain: str, family: str, prompt: str, options: List[str], answer: str, explanation: str, kind: str = "choice", construct: str | None = None) -> Dict[str, Any]:
    if answer not in options or len(set(options)) != 4:
        raise ValueError(f"Invalid options for {item_id}")
    return {
        "id": item_id,
        "item_family_id": family,
        "domain": domain,
        "construct_id": construct or family,
        "type": kind,
        "prompt": prompt,
        "options": options,
        "answer": answer,
        "explanation": explanation,
        "difficulty_label": "medium_hard",
        "difficulty_estimate": None,
        # Generated candidates are never student-eligible until two human
        # reviewers approve the exact item version.  Keeping this state
        # explicit prevents the seed job from accidentally turning generated
        # content into production assessment material.
        "lifecycle_status": "AUTO_VERIFIED",
        # `status` remains the legacy demo-form flag used by the local preview;
        # `lifecycle_status` is authoritative for release and seed gating.
        "status": "PILOT",
        "data_origin": "ORIGINAL_GENERATED",
        "content_version": 2,
        "generation_run_id": FACTORY_SEED,
        "generation_parameters": {"factory": family.split("_")[0], "seed": FACTORY_SEED, "variant": item_id[-3:]},
        "provenance": "Original IAQ deterministic candidate; human review required before activation.",
        "language": "en",
        "render_type": "svg_stimulus" if domain in {"abstract_reasoning", "visual_spatial_reasoning"} else kind,
        "render_parameters": {"seed": f"{FACTORY_SEED}:{item_id}", "family": family, "variant": item_id[-3:]},
        "review_required": True,
        "review_history": [],
    }


def _place_correct(answer: str, distractors: Sequence[str], index: int) -> Tuple[List[str], str]:
    values = [answer, *distractors]
    if len(set(values)) != 4:
        raise ValueError("Each item must have four distinct options")
    shift = (index * 7) % 4
    return values[shift:] + values[:shift], answer


def _number_options(answer: int, spread: int, index: int) -> Tuple[List[str], str]:
    candidates = [answer, answer + spread, answer - spread, answer + spread * 2]
    if len(set(candidates)) != 4:
        candidates = [answer, answer + 3, answer - 4, answer + 8]
    return _place_correct(str(answer), [str(value) for value in candidates[1:]], index)


def abstract_items() -> List[Dict[str, Any]]:
    shapes = ["triangle", "square", "pentagon", "hexagon", "circle"]
    fills = ["outline", "striped", "solid", "dotted"]
    rotations = [0, 90, 180, 270]
    items: List[Dict[str, Any]] = []
    for index in range(100):
        shape = shapes[index % len(shapes)]
        fill = fills[(index // 5) % len(fills)]
        rotation = rotations[(index * 2) % len(rotations)]
        mark_count = 1 + index // 20
        next_shape = shapes[(shapes.index(shape) + 2) % len(shapes)]
        next_fill = fills[(fills.index(fill) + 1) % len(fills)]
        next_rotation = (rotation + 90) % 360
        answer = f"{next_fill} {next_shape}, rotated {next_rotation}°"
        options, key = _place_correct(answer, [f"{fill} {next_shape}, rotated {next_rotation}°", f"{next_fill} {shape}, rotated {rotation}°", f"{next_fill} {next_shape}, rotated {(next_rotation + 180) % 360}°"], index)
        items.append(_item(f"ABS-{21 + index:03d}", "abstract_reasoning", f"abstract_composition_{index % 10:02d}", f"A tile with {mark_count} marks is {fill} {shape}, rotated {rotation}°. Each step changes the shape by two positions, advances the fill by one, and rotates 90° clockwise. Which tile comes next?", options, key, "The three attributes follow separate rules: +2 shape positions, +1 fill position, and +90° rotation.", construct="relational_transformation"))
    return items


def deductive_items() -> List[Dict[str, Any]]:
    subjects = ["lantern", "archive", "proposal", "robot", "scholar", "survey", "blueprint", "instrument", "parcel", "prototype"]
    categories = ["inspected", "encrypted", "approved", "calibrated", "published"]
    items: List[Dict[str, Any]] = []
    for index in range(100):
        subject = subjects[index % len(subjects)]
        category = categories[(index // 10) % len(categories)]
        setting = ["a lab", "an archive room", "a workshop", "a field study", "a classroom"][index // 20]
        if index % 4 == 0:
            prompt = f"In {setting}, every {category} {subject} is logged. No logged {subject} is anonymous. This {subject} is {category}. Which conclusion must be true?"
            answer, distractors, explanation, family = "It is logged and not anonymous", ["It is anonymous", f"It is not {category}", "It is the newest item"], "The first rule gives logged; the second rule excludes anonymous for logged items.", "logic_chained_universal"
        elif index % 4 == 1:
            prompt = f"In {setting}, if a {subject} is marked urgent, it is reviewed today. The {subject} was not reviewed today. Assuming the rule is reliable, what follows?"
            answer, distractors, explanation, family = f"The {subject} was not marked urgent", [f"The {subject} was marked urgent", "The review was completed early", "Nothing can be inferred"], "The absent consequence rules out the condition by contraposition.", "logic_contrapositive"
        elif index % 4 == 2:
            prompt = f"In {setting}, four {subject}s—A, B, C, and D—are ordered. A is before C, C is before D, and B is after A but before C. Which position must C occupy?"
            answer, distractors, explanation, family = "Third", ["First", "Second", "Fourth"], "The constraints force A, B, C, D, so C is third.", "logic_order_constraints"
        else:
            prompt = f"In {setting}, all {category} {subject} records are checked. Some checked records are archived. Which statement is guaranteed by these facts?"
            answer, distractors, explanation, family = f"Every {category} record is checked", ["Every checked record is archived", f"Some {category} records are not checked", "No archived record is checked"], "Only the stated universal relationship is guaranteed; the other options reverse or overextend it.", "logic_scope_quantifiers"
        options, key = _place_correct(answer, distractors, index)
        items.append(_item(f"LOG-{21 + index:03d}", "deductive_logic", f"{family}_{index % 10:02d}", prompt, options, key, explanation, construct=family))
    return items


def numerical_items() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for index in range(100):
        a, b = 3 + (index % 9), 2 + (index % 5)
        context = ["lab measurement", "transport log", "budget model", "game score", "survey count"][index // 20]
        if index % 4 == 0:
            values = [a, a + b, a + b + 2, a + 2 * b + 2, a + 2 * b + 6]
            answer, explanation, family = values[-1] + 2 * b + 4, "The increments alternate between adding b and adding b+2, with the increment itself increasing by two after each pair.", "number_alternating_differences"
        elif index % 4 == 1:
            values = [a, a * 2 + b, (a * 2 + b) * 2 - b, ((a * 2 + b) * 2 - b) * 2 + b]
            answer, explanation, family = values[-1] * 2 - b, "The operation alternates between doubling and adding b, then doubling and subtracting b.", "number_alternating_operations"
        elif index % 4 == 2:
            values = [a, a + b, a + 2 * b, a + 3 * b + 1, a + 4 * b + 1]
            answer, explanation, family = a + 5 * b + 2, "The sequence adds b, b, then b+1, b+1, so the next paired increment is b+2.", "number_paired_increments"
        else:
            values = [a, a + 2, a * 2 + 1, a * 2 + 5, a * 4 + 7]
            answer, explanation, family = values[-1] * 2 + 9, "Each pair alternates a small linear increase with a doubling step; the final transition continues the doubling rule with its offset.", "number_mixed_rule"
        options, key = _number_options(answer, max(3, b + index % 4), index)
        items.append(_item(f"NUM-{21 + index:03d}", "numerical_reasoning", f"{family}_{index % 10:02d}", f"In this {context}, complete the sequence: {', '.join(str(value) for value in values)}, ?. Which value follows the underlying rule?", options, key, explanation, "sequence", construct=family))
    return items


def verbal_items() -> List[Dict[str, Any]]:
    pairs = [("scarce", "abundant", "rigid", "flexible"), ("blueprint", "building", "outline", "essay"), ("evidence", "claim", "measurement", "conclusion"), ("thermometer", "temperature", "compass", "direction"), ("editor", "manuscript", "curator", "collection"), ("seed", "tree", "prototype", "product"), ("cautious", "reckless", "precise", "careless"), ("question", "investigate", "problem", "solve"), ("transparent", "visible", "audible", "heard"), ("archive", "preserve", "filter", "select")]
    items: List[Dict[str, Any]] = []
    for index in range(100):
        first, relation, third, answer = pairs[index % len(pairs)]
        context = ["a design brief", "a research note", "a school project", "a museum label"][index // 30]
        if index % 3 == 1:
            prompt, answer, distractors, family, explanation = f"A report says attendance rose by {15 + index}% after evening access was extended, but it does not measure morning attendance. Which conclusion is best supported?", "Evening access became more popular after the change", ["All visitors prefer evenings", "Morning attendance fell", "The venue became free"], "verbal_evidence_scope", "The report supports the observed change without justifying broader claims."
        elif index % 3 == 2:
            prompt, answer, distractors, family, explanation = f"In {context}, which word is closest in meaning to {first!r}?", relation, [third, "temporary", "unrelated"], "verbal_context_vocabulary", f"{relation.title()} is the closest contextual meaning for {first}."
        else:
            prompt, distractors, family, explanation = f"In {context}, {first.title()} is to {relation} as {third} is to…", ["measure", "decorate", "delay"], "verbal_analogy", "The second pair follows the same relationship as the first pair."
        options, key = _place_correct(answer, distractors, index)
        items.append(_item(f"VRB-{21 + index:03d}", "verbal_reasoning", f"{family}_{index % 10:02d}", prompt, options, key, explanation, construct=family))
    return items


def spatial_items() -> List[Dict[str, Any]]:
    directions, positions = ["north", "east", "south", "west"], ["top-left", "top-right", "bottom-right", "bottom-left"]
    items: List[Dict[str, Any]] = []
    for index in range(100):
        board = ["paper", "screen", "floor", "map", "model"][index // 20]
        if index % 3 == 0:
            start, turns = directions[index % 4], 2 + index % 3
            answer = directions[(directions.index(start) + turns) % 4]
            distractors = [directions[(directions.index(answer) + offset) % 4] for offset in (1, 2, 3)]
            prompt, explanation, family = f"On a {board} grid of {5 + index // 12}×{5 + index // 12}, a pointer faces {start}. Rotate it 90° clockwise {turns} times. Which direction does it face?", "Each clockwise turn advances one position in the four-direction cycle.", "spatial_rotation"
        elif index % 3 == 1:
            start = positions[index % 4]
            answer, distractors = positions[(positions.index(start) + 1) % 4], [position for position in positions if position != positions[(positions.index(start) + 1) % 4]]
            prompt, explanation, family = f"On a {board} grid, a marked corner starts at the {start} of a square with side length {4 + index // 12}. Rotate the square 90° clockwise. Where does the marked corner move?", "A clockwise quarter-turn moves each corner to the next corner in the clockwise direction.", "spatial_corner_rotation"
        else:
            width, height = 4 + index % 7, 2 + index % 5
            if width == height:
                height += 1
            answer, distractors = f"{height} units wide and {width} units tall", [f"{width} units wide and {height} units tall", f"{width + height} units wide and {height} units tall", "equal width and height"]
            prompt, explanation, family = f"On a {board} grid, a rectangle is {width} units wide and {height} units tall. After a 90° clockwise rotation, which description is correct?", "A quarter-turn swaps the rectangle's width and height.", "spatial_dimension_transform"
        options, key = _place_correct(answer, distractors, index)
        items.append(_item(f"SPA-{21 + index:03d}", "visual_spatial_reasoning", f"{family}_{index % 10:02d}", prompt, options, key, explanation, construct=family))
    return items


def memory_items() -> List[Dict[str, Any]]:
    symbols = ["K", "7", "M", "2", "R", "9", "T", "4", "P", "6", "H", "8"]
    openings = ["Study", "Read", "Observe", "Take in", "Focus on", "Notice", "Hold", "Keep", "Attend to", "Inspect"]
    focus_phrases = ["the order", "each position", "the sequence from left to right", "the full run", "the symbols in place", "the arrangement as shown", "the order exactly", "each symbol's location", "the displayed arrangement", "the sequence as presented"]
    items: List[Dict[str, Any]] = []
    for index in range(100):
        length = 6 + index % 3
        context = ["symbol", "number", "letter", "mixed", "location"][index // 20]
        step = 2 + (index // 12) % 5
        sequence = [symbols[(index * 3 + offset * step + offset // 2) % len(symbols)] for offset in range(length)]
        answer = " — ".join(sequence)
        reverse, rotate = " — ".join(reversed(sequence)), " — ".join(sequence[2:] + sequence[:2])
        swap = sequence[:]
        swap[1], swap[2] = swap[2], swap[1]
        options, key = _place_correct(answer, [reverse, rotate, " — ".join(swap)], index)
        prompt = f"{openings[index % len(openings)]} this {context} sequence for three seconds, focusing on {focus_phrases[index // len(openings)]}. It will disappear. Which option matches it exactly?"
        item = _item(f"MEM-{21 + index:03d}", "working_memory", f"memory_update_{index % 10:02d}", prompt, options, key, "The correct response preserves every symbol and its position; distractors target reversal, rotation, and adjacent swaps.", "memory", construct="short_term_order_memory")
        item["memory_stimulus"] = sequence
        item["memory_protocol"] = {"study_ms": 3000, "response_timeout_ms": 30000, "replay_allowed": False, "score_method": "exact_option"}
        items.append(item)
    return items


def speed_items() -> List[Dict[str, Any]]:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    items: List[Dict[str, Any]] = []
    for index in range(100):
        rng = random.Random(f"{FACTORY_SEED}:speed:{index}")
        target = "".join(rng.choice(alphabet) for _ in range(5))
        candidates = [target[::-1], target[:2] + target[3] + target[2] + target[4], target[:4] + alphabet[(alphabet.index(target[4]) + 1) % len(alphabet)]]
        distractors: List[str] = []
        for candidate in candidates:
            if candidate != target and candidate not in distractors:
                distractors.append(candidate)
        cursor = 0
        while len(distractors) < 3:
            replacement = alphabet[(alphabet.index(target[cursor % 5]) + cursor + 1) % len(alphabet)]
            candidate = target[:cursor % 5] + replacement + target[cursor % 5 + 1:]
            if candidate != target and candidate not in distractors:
                distractors.append(candidate)
            cursor += 1
        options, key = _place_correct(target, distractors, index)
        items.append(_item(f"SPD-{21 + index:03d}", "processing_speed", f"speed_exact_match_{index % 10:02d}", f"Compare the target with the four codes. Which option is an exact match? Target: {target}", options, key, "Only the exact match keeps all five symbols in the same positions; distractors contain a transposition, one substitution, or reversal.", "speed", construct="visual_exact_matching"))
    return items


def _assert_unique(items: Iterable[Dict[str, Any]]) -> None:
    records = list(items)
    if len({item["id"] for item in records}) != len(records):
        raise ValueError("Generated item IDs must be unique")
    if len({item["prompt"] for item in records}) != len(records):
        seen: set[str] = set()
        for item in records:
            if item["prompt"] in seen:
                raise ValueError(f"Generated prompts must be unique: {item['id']} :: {item['prompt']}")
            seen.add(item["prompt"])


def generated_items() -> List[Dict[str, Any]]:
    all_items = abstract_items() + deductive_items() + numerical_items() + verbal_items() + spatial_items() + memory_items() + speed_items()
    _assert_unique(all_items)
    return all_items
