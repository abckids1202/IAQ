"""Deterministic, reviewable pilot item factories.

The factory expands the bank with explicit, reproducible rules. It creates
candidate content for pilot review; it does not establish psychometric
difficulty, validity, or normed scores. Every generated item stays in PILOT
until a human reviewer promotes it.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence, Tuple


GENERATION_RUN_ID = "IAQ-FACTORY-2026-09-06-120-PER-DOMAIN"
GENERATED_PER_DOMAIN = 100


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
    if len(options) != 4 or len(set(options)) != 4 or answer not in options:
        raise ValueError(f"Invalid answer set for {item_id}")
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


def _place_correct(answer: str, distractors: Sequence[str], index: int) -> Tuple[List[str], str]:
    values = list(distractors)
    if len(values) != 3 or answer in values or len(set(values)) != 3:
        raise ValueError("Generated distractors must be distinct from the answer")
    position = index % 4
    values.insert(position, answer)
    return [f"{chr(65 + number)}. {value}" for number, value in enumerate(values)], f"{chr(65 + position)}. {answer}"


def _number_options(answer: int, spread: int, index: int) -> Tuple[List[str], str]:
    return _place_correct(str(answer), [str(answer - spread), str(answer + spread), str(answer + spread * 2)], index)


def abstract_items() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    directions = ["up", "right", "down", "left"]
    for index in range(1, GENERATED_PER_DOMAIN + 1):
        mode = index % 4
        family = f"abstract_factory_{index % 32:02d}"
        if mode == 0:
            start = 7 + index
            step = 2 + index % 11
            sequence = [start + step * offset for offset in range(4)]
            answer = sequence[-1] + step
            options, key = _number_options(answer, step, index)
            prompt = f"Sequence study {index}: {sequence[0]}, {sequence[1]}, {sequence[2]}, {sequence[3]}, ?. Which number follows?"
            explanation = f"The sequence adds {step} each time, so the next value is {answer}."
        elif mode == 1:
            start = 2 + index % 17
            multiplier = 2 + index % 3
            sequence = [start]
            for _ in range(3):
                sequence.append(sequence[-1] * multiplier)
            answer = sequence[-1] * multiplier
            options, key = _number_options(answer, start, index)
            prompt = f"Pattern study {index}: {sequence[0]}, {sequence[1]}, {sequence[2]}, {sequence[3]}, ?. Which number completes the rule?"
            explanation = f"Each term is multiplied by {multiplier}, so the next value is {answer}."
        elif mode == 2:
            start_index = (index * 3) % 4
            turns = 1 + index % 3
            current = directions[start_index]
            target = directions[(start_index + turns) % 4]
            distractors = [direction for direction in directions if direction != target]
            options, key = _place_correct(target, distractors, index)
            prompt = f"Direction study {index}: a mark points {current} and turns 90 degrees clockwise {turns} time(s). Where does it point?"
            explanation = f"{turns} clockwise quarter-turns move {current} to {target}."
        else:
            start = 5 + index
            first_gap = 2 + index % 7
            second_gap = 3 + index % 5
            sequence = [start, start + first_gap, start + first_gap + second_gap, start + 2 * first_gap + second_gap]
            answer = sequence[-1] + second_gap
            options, key = _number_options(answer, first_gap, index)
            prompt = f"Alternating study {index}: {sequence[0]}, {sequence[1]}, {sequence[2]}, {sequence[3]}, ?. What comes next?"
            explanation = f"The gaps alternate +{first_gap}, +{second_gap}; the next step is +{second_gap}."
        items.append(_item(f"ABS-{20 + index:03d}", "abstract_reasoning", family, prompt, options, key, explanation))
    return items


def deductive_items() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    subjects = ["the archivist", "Mina", "the rover", "the new policy", "the blue folder", "Sam", "the sensor", "the garden"]
    categories = ["metal objects", "night-shift workers", "sealed files", "winter plants", "trained pilots", "library books", "encrypted messages", "audited records"]
    properties = ["are durable", "know the route", "need a key", "survive frost", "follow the checklist", "have a catalogue entry", "use a passphrase", "keep a timestamp"]
    conditions = ["the alarm is armed", "the file is encrypted", "the route is closed", "the sample is heated", "the account is verified", "the light is green", "the device is connected", "the report is approved"]
    consequences = ["the warning is active", "a key is required", "the detour is used", "the sample expands", "access is granted", "the motor can start", "the signal is available", "the report can be released"]
    for index in range(1, GENERATED_PER_DOMAIN + 1):
        mode = index % 4
        family = f"logic_factory_{index % 32:02d}"
        slot = (index - 1) % len(subjects)
        if mode == 0:
            subject = subjects[slot]
            category = categories[slot]
            property_value = properties[slot]
            distractors = [f"{subject} {properties[(slot + offset) % len(properties)]}" for offset in (1, 2, 3)]
            answer = f"{subject} {property_value}"
            options, key = _place_correct(answer, distractors, index)
            prompt = f"Deduction {index}: all {category} {property_value}; {subject} is a {category[:-1]}. What must be true?"
            explanation = f"The stated category rule applies directly to {subject}."
        elif mode == 1:
            category = categories[slot]
            subject = subjects[(slot + 3) % len(subjects)]
            excluded = properties[(slot + 4) % len(properties)]
            answer = f"{subject} is not {excluded}"
            distractors = [f"{subject} is {excluded}", f"{subject} is {properties[(slot + 5) % len(properties)]}", "Nothing can be concluded"]
            options, key = _place_correct(answer, distractors, index)
            prompt = f"Exclusion {index}: no {category} {excluded}; {subject} is a {category[:-1]}. Which statement follows?"
            explanation = "Being in the category rules out the excluded property."
        elif mode == 2:
            condition = conditions[slot]
            consequence = consequences[slot]
            answer = consequence.capitalize()
            distractors = [f"{condition.capitalize()} is impossible", "The opposite must be true", "Nothing follows from the condition"]
            options, key = _place_correct(answer, distractors, index)
            prompt = f"Conditional reasoning {index}: if {condition}, then {consequence}. The fact is that {condition}. What follows?"
            explanation = "The fact satisfies the condition, so the stated consequence follows."
        else:
            condition = conditions[(slot + 2) % len(conditions)]
            consequence = consequences[(slot + 2) % len(consequences)]
            answer = f"{condition.capitalize()} is not established"
            distractors = [f"{condition.capitalize()} is certain", f"{consequence.capitalize()} is certain", "The two statements are identical"]
            options, key = _place_correct(answer, distractors, index)
            prompt = f"Careful inference {index}: if {condition}, then {consequence}. The consequence is not present. What is safest?"
            explanation = "The missing consequence does not prove the condition false; it only means the condition is not established."
        items.append(_item(f"LOG-{20 + index:03d}", "deductive_logic", family, prompt, options, key, explanation))
    return items


def numerical_items() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for index in range(1, GENERATED_PER_DOMAIN + 1):
        mode = index % 6
        family = f"numerical_factory_{index % 32:02d}"
        if mode == 0:
            start = 4 + index
            step = 3 + index % 9
            sequence = [start + step * offset for offset in range(4)]
            answer = sequence[-1] + step
            explanation = f"The constant difference is {step}."
        elif mode == 1:
            start = 5 + index
            base = 2 + index % 6
            gaps = [base, base + 2, base + 4]
            sequence = [start, start + gaps[0], start + gaps[0] + gaps[1], start + sum(gaps)]
            answer = sequence[-1] + base + 6
            explanation = f"The gaps increase by two: +{base}, +{base + 2}, +{base + 4}, then +{base + 6}."
        elif mode == 2:
            start = 2 + index % 19
            multiplier = 2 + index % 2
            sequence = [start * multiplier**offset for offset in range(4)]
            answer = sequence[-1] * multiplier
            explanation = f"Each term is multiplied by {multiplier}."
        elif mode == 3:
            start = 3 + index
            addition = 1 + index % 8
            sequence = [start]
            for _ in range(3):
                sequence.append(sequence[-1] * 2 + addition)
            answer = sequence[-1] * 2 + addition
            explanation = f"Each term is doubled and then {addition} is added."
        elif mode == 4:
            base = 3 + index % 23
            sequence = [(base + offset) ** 2 for offset in range(4)]
            answer = (base + 4) ** 2
            explanation = "The terms are consecutive square numbers."
        else:
            first = 2 + index % 13
            second = 3 + index % 11
            sequence = [first, second, first + second, second + first + second]
            answer = sequence[-1] + sequence[-2]
            explanation = "Each term after the first two is the sum of the previous two."
        options, key = _number_options(answer, max(1, 1 + index % 7), index)
        prompt = f"Number sequence {index}: {sequence[0]}, {sequence[1]}, {sequence[2]}, {sequence[3]}, ?. Which value completes it?"
        items.append(_item(f"NUM-{20 + index:03d}", "numerical_reasoning", family, prompt, options, key, explanation, "sequence"))
    return items


ANALOGIES = [
    ("compass", "direction", "thermometer", "temperature"), ("blueprint", "building", "recipe", "meal"),
    ("sculptor", "stone", "writer", "words"), ("key", "lock", "password", "account"),
    ("seed", "plant", "idea", "project"), ("lens", "focus", "filter", "selection"),
    ("map", "navigation", "score", "evaluation"), ("grammar", "sentence", "syntax", "program"),
    ("battery", "energy", "reservoir", "water"), ("bridge", "crossing", "translator", "language"),
    ("archive", "preservation", "sieve", "separation"), ("thermostat", "temperature", "timer", "duration"),
    ("evidence", "conclusion", "clue", "inference"), ("muscle", "movement", "engine", "motion"),
    ("calendar", "date", "odometer", "distance"), ("editor", "manuscript", "curator", "collection"),
    ("orbit", "planet", "path", "traveller"), ("recipe", "ingredients", "plan", "steps"),
    ("question", "answer", "problem", "solution"), ("nest", "bird", "web", "spider"),
    ("passport", "travel", "ticket", "entry"), ("contract", "agreement", "rule", "constraint"),
    ("signal", "message", "indicator", "status"), ("library", "books", "gallery", "artworks"),
    ("root", "tree", "foundation", "building"),
]

INFERENCE_CASES = [
    ("The studio opened early on Tuesday and attendance increased.", "Opening time and attendance were associated on Tuesday.", ["The earlier opening caused every visit.", "Attendance increased every day.", "The studio was full before opening."]),
    ("The team tested two materials before choosing the lighter one.", "The materials were tested before the choice.", ["The heavier material was unsafe.", "Only one material was available.", "The lighter material was cheaper."]),
    ("A student submitted a draft but not the final version.", "A draft was submitted.", ["The final version was rejected.", "The draft received a high mark.", "The project was cancelled."]),
    ("The train was delayed, so Noor arrived after the meeting began.", "The delay occurred before Noor arrived late.", ["Noor missed the entire meeting.", "The meeting was cancelled.", "Noor caused the delay."]),
    ("The report uses a small observational sample.", "Its findings should be read as limited evidence.", ["Its conclusion is universally true.", "The sample was randomly assigned.", "The report has no useful information."]),
    ("The garden received rain, but the new seedlings still wilted.", "Rain alone did not prevent the seedlings from wilting.", ["The rain damaged every plant.", "The seedlings were never watered.", "The garden had no soil."]),
    ("The app loaded faster after several images were compressed.", "Image compression coincided with faster loading.", ["Compression caused every performance change.", "The app was slower before images existed.", "The images were deleted."]),
    ("Luca checked the address twice before sending the parcel.", "Luca checked the address before sending it.", ["The parcel arrived safely.", "The address was incorrect.", "Luca sent two parcels."]),
    ("A survey had more responses from older students than younger students.", "The age groups were represented unequally.", ["Older students had stronger opinions.", "Younger students refused to answer.", "The survey was nationally representative."]),
    ("The machine stopped when its safety cover was opened.", "Opening the cover was followed by the machine stopping.", ["The machine was permanently broken.", "The cover was never opened.", "The safety system failed."]),
    ("The class reviewed examples and then solved a new problem.", "The examples came before the new problem.", ["Every student solved it correctly.", "The examples were unrelated.", "The problem was easier than the examples."]),
    ("A note says the parcel is fragile but does not list its value.", "The parcel is described as fragile; its value is unknown.", ["The parcel is expensive.", "The parcel is insured.", "The parcel contains glass."]),
    ("The research team changed the question after the pilot interview.", "The pilot interview happened before the question changed.", ["The pilot failed.", "The new question is better.", "No interview occurred."]),
    ("A path is shorter on the map but steeper in reality.", "Map distance alone does not describe the whole route.", ["The path is always faster.", "The path is impossible to walk.", "The map is inaccurate."]),
    ("Mara practised the piano twice and then recorded one take.", "Mara recorded after the practice sessions.", ["The recording was perfect.", "Mara practised every day.", "The first practice was recorded."]),
    ("The school added a quiet room and reported fewer hallway complaints.", "The change and fewer complaints occurred in the same period.", ["The quiet room caused every improvement.", "Hallway complaints disappeared permanently.", "Students stopped using the hallway."]),
    ("The package was marked delivered, although the recipient had not checked the door.", "Delivery was marked before the recipient checked the door.", ["The package was stolen.", "The courier left it outside.", "The recipient never ordered it."]),
    ("Two designs received the same rating but different written comments.", "Equal ratings can include different feedback.", ["The designs were identical.", "The comments were scored numerically.", "One design was rejected."]),
    ("The lamp works with a new bulb but not with the old one.", "The bulb may be relevant to the lamp's operation.", ["The lamp is new.", "The old bulb is broken.", "The socket has no electricity."]),
    ("The coach changed the practice order after observing the team.", "The observation happened before the order changed.", ["The team won the next match.", "The original order was wrong.", "The coach changed every exercise."]),
    ("A library reduced opening hours while renovation was underway.", "The reduced hours occurred during renovation.", ["The library will close forever.", "Renovation finished early.", "Readers opposed the renovation."]),
    ("A graph rises sharply, but its vertical axis begins at 90.", "The visual size of the rise may exaggerate the numerical change.", ["The data is false.", "The rise is exactly ten times larger.", "The graph has no axis."]),
    ("The group agreed on the goal but not on the timetable.", "Agreement on a goal does not imply agreement on timing.", ["The group abandoned the goal.", "The timetable was accepted.", "The goal was impossible."]),
    ("A student read the instructions and asked one clarifying question.", "The student encountered an issue requiring clarification.", ["The instructions were unreadable.", "The student ignored the instructions.", "The task was completed perfectly."]),
    ("The plant grew taller near the window, where it also received more light.", "Height and light exposure were associated in this observation.", ["Light definitely caused all growth.", "The plant cannot grow elsewhere.", "The window was open."]),
]

CLASSIFICATIONS = [
    ("granite", ["maple", "oak", "pine", "granite"]), ("easel", ["violin", "cello", "flute", "easel"]),
    ("mercury", ["iron", "copper", "silver", "mercury"]), ("triangle", ["circle", "square", "rectangle", "triangle"]),
    ("whale", ["sparrow", "eagle", "robin", "whale"]), ("rain", ["oak", "rose", "fern", "rain"]),
    ("kilometre", ["second", "hour", "minute", "kilometre"]), ("copper", ["plastic", "glass", "wood", "copper"]),
    ("January", ["March", "June", "October", "January"]), ("hammer", ["saw", "drill", "chisel", "hammer"]),
    ("oxygen", ["nitrogen", "helium", "carbon dioxide", "oxygen"]), ("novel", ["poem", "essay", "report", "novel"]),
    ("piano", ["violin", "trumpet", "drum", "piano"]), ("river", ["lake", "ocean", "pond", "river"]),
    ("blue", ["red", "green", "yellow", "blue"]), ("rectangle", ["cube", "sphere", "cone", "rectangle"]),
    ("lizard", ["salmon", "eagle", "frog", "lizard"]), ("Tuesday", ["Monday", "Wednesday", "Friday", "Tuesday"]),
    ("courage", ["honesty", "patience", "curiosity", "courage"]), ("satellite", ["comet", "asteroid", "planet", "satellite"]),
    ("kilogram", ["metre", "litre", "second", "kilogram"]), ("dictionary", ["atlas", "novel", "manual", "dictionary"]),
    ("screwdriver", ["wrench", "pliers", "spanner", "screwdriver"]), ("Venus", ["Mars", "Jupiter", "Saturn", "Venus"]),
    ("rectangle", ["triangle", "pentagon", "hexagon", "rectangle"]),
]

VOCABULARY = [
    ("precise", "exact", ["distant", "noisy", "temporary"]), ("brief", "short", ["heavy", "bright", "remote"]),
    ("reluctant", "hesitant", ["eager", "certain", "rapid"]), ("abundant", "plentiful", ["scarce", "fragile", "silent"]),
    ("inference", "conclusion from evidence", ["random guess", "visual design", "spoken greeting"]), ("adapt", "adjust to a change", ["repeat exactly", "remove entirely", "measure distance"]),
    ("contradict", "say the opposite", ["support strongly", "copy carefully", "arrive early"]), ("coherent", "logically connected", ["randomly coloured", "physically heavy", "nearly empty"]),
    ("allocate", "assign for a purpose", ["hide from view", "break apart", "speak loudly"]), ("diminish", "become smaller", ["become clearer", "move sideways", "remain equal"]),
    ("transparent", "easy to see through", ["difficult to hear", "likely to break", "full of sound"]), ("valid", "well supported", ["unrelated", "unfinished", "very old"]),
    ("obscure", "difficult to understand", ["obvious", "generous", "rectangular"]), ("retain", "keep", ["discard", "rotate", "announce"]),
    ("modify", "change partly", ["celebrate loudly", "copy without change", "measure twice"]), ("sufficient", "enough", ["missing", "opposite", "uncertain"]),
    ("derive", "obtain from a source", ["place underneath", "avoid entirely", "decorate brightly"]), ("explicit", "stated clearly", ["hidden", "accidental", "circular"]),
    ("consecutive", "following in order", ["far apart", "contradictory", "unrelated"]), ("robust", "strong and resilient", ["easily broken", "quietly spoken", "newly painted"]),
    ("constrain", "limit", ["expand freely", "explain simply", "travel quickly"]), ("evaluate", "judge using criteria", ["forget immediately", "draw randomly", "fold twice"]),
    ("ambiguous", "open to more than one meaning", ["perfectly measured", "very loud", "already finished"]), ("precede", "come before", ["come after", "remain beside", "grow within"]),
    ("notable", "worthy of attention", ["impossible to notice", "made of metal", "located below"]),
]


def verbal_items() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for index in range(1, GENERATED_PER_DOMAIN + 1):
        block = (index - 1) // 25
        slot = (index - 1) % 25
        family = f"verbal_factory_{index % 32:02d}"
        if block == 0:
            first, relation, third, correct = ANALOGIES[slot]
            distractors = [ANALOGIES[(slot + offset) % len(ANALOGIES)][3] for offset in (1, 2, 3)]
            options, key = _place_correct(correct, distractors, index)
            prompt = f"Analogy {index}: {first} is to {relation} as {third} is to…"
            explanation = f"The relationship from {first} to {relation} matches {third} to {correct}."
        elif block == 1:
            statement, correct, distractors = INFERENCE_CASES[slot]
            options, key = _place_correct(correct, distractors, index)
            prompt = f"Reading inference {index}: {statement} What is the safest conclusion?"
            explanation = "The correct response stays within what the statement supports and avoids an extra causal claim."
        elif block == 2:
            odd, group = CLASSIFICATIONS[slot]
            options, key = _place_correct(odd, [value for value in group if value != odd], index)
            prompt = f"Classification {index}: which item does not belong with the other three?"
            explanation = f"{odd.capitalize()} belongs to a different category from the other three choices."
        else:
            word, correct, distractors = VOCABULARY[slot]
            options, key = _place_correct(correct, distractors, index)
            prompt = f"Vocabulary {index}: which option is closest in meaning to “{word}”?"
            explanation = f"“{word.capitalize()}” is closest in meaning to “{correct}.”"
        items.append(_item(f"VRB-{20 + index:03d}", "verbal_reasoning", family, prompt, options, key, explanation))
    return items


def spatial_items() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    directions = ["north", "east", "south", "west"]
    positions = ["upper-left", "upper-right", "lower-right", "lower-left"]
    for index in range(1, GENERATED_PER_DOMAIN + 1):
        mode = index % 4
        family = f"spatial_factory_{index % 32:02d}"
        if mode == 0:
            start_index = (index * 2) % 4
            turns = 1 + index % 3
            target = directions[(start_index + turns) % 4]
            options, key = _place_correct(target, [direction for direction in directions if direction != target], index)
            prompt = f"Rotation {index}: a pointer faces {directions[start_index]}. Rotate it 90 degrees clockwise {turns} time(s). Where does it face?"
            explanation = f"The pointer moves {turns} quarter-turns clockwise to {target}."
        elif mode == 1:
            east = 2 + index % 8
            west = 1 + index % 5
            north = 2 + index % 7
            south = 1 + index % 4
            horizontal = east - west
            vertical = north - south
            horizontal_word = "east" if horizontal > 0 else "west" if horizontal < 0 else "no horizontal movement"
            vertical_word = "north" if vertical > 0 else "south" if vertical < 0 else "no vertical movement"
            correct = f"{abs(horizontal)} {horizontal_word}, {abs(vertical)} {vertical_word}"
            distractors = [f"{abs(horizontal) + 1} east, {abs(vertical)} north", f"{abs(horizontal)} west, {abs(vertical) + 1} south", "back at the start"]
            options, key = _place_correct(correct, distractors, index)
            prompt = f"Grid path {index}: move {east} squares east, {north} north, {west} west, and {south} south. Where are you from the start?"
            explanation = "Opposite horizontal and vertical movements cancel independently."
        elif mode == 2:
            start = positions[(index * 3) % 4]
            target = positions[positions.index(start) ^ 1]
            options, key = _place_correct(target, [position for position in positions if position != target], index)
            prompt = f"Reflection {index}: a dot starts in the {start} corner. Reflect the square across its vertical centre line. Where is the dot?"
            explanation = "A vertical reflection reverses left and right while keeping the vertical position."
        else:
            width = 3 + index % 9
            height = 2 + index % 5
            correct = f"{width} units tall and {height} units wide"
            distractors = [f"{width} units wide and {height} units tall", f"{width + height} units tall", "a square with equal sides"]
            options, key = _place_correct(correct, distractors, index)
            prompt = f"Rotation of a rectangle {index}: it is {width} units wide and {height} units tall. After a 90-degree turn, which description is correct?"
            explanation = "A quarter-turn swaps the rectangle's width and height."
        items.append(_item(f"SPA-{20 + index:03d}", "visual_spatial_reasoning", family, prompt, options, key, explanation))
    return items


def memory_items() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for index in range(1, GENERATED_PER_DOMAIN + 1):
        length = 5 + index % 2
        start = (index * 7) % 90
        step = 2 + index % 13
        sequence = [f"{(start + offset * step) % 100:02d}" for offset in range(length)]
        correct_value = " — ".join(sequence)
        rotated = sequence[1:] + sequence[:1]
        reversed_sequence = list(reversed(sequence))
        swapped = sequence[:2] + [sequence[3]] + [sequence[2]] + sequence[4:]
        distractors = [" — ".join(rotated), " — ".join(reversed_sequence), " — ".join(swapped)]
        options, key = _place_correct(correct_value, distractors, index)
        prompt = f"Memory trial {index}: remember this sequence, then choose the exact match: {correct_value}"
        explanation = "The correct response preserves every token and its position."
        items.append(_item(f"MEM-{20 + index:03d}", "working_memory", f"memory_factory_{index % 32:02d}", prompt, options, key, explanation, "memory"))
    return items


def speed_items() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for index in range(1, GENERATED_PER_DOMAIN + 1):
        target = f"{index:03d}{(index * 7 + 3) % 10}"
        variants = [target[::-1], f"{target[0]}{target[2]}{target[1]}{target[3]}", f"{target[:3]}{(int(target[3]) + 1) % 10}"]
        distractors: List[str] = []
        for variant in variants:
            if variant != target and variant not in distractors:
                distractors.append(variant)
        while len(distractors) < 3:
            candidate = f"{target[1:]}{len(distractors)}"
            if candidate != target and candidate not in distractors:
                distractors.append(candidate)
        options, key = _place_correct(target, distractors, index)
        prompt = f"Visual search {index}: find the exact match for target code {target}."
        explanation = "Only the exact match preserves every character in the same position."
        items.append(_item(f"SPD-{20 + index:03d}", "processing_speed", f"speed_factory_{index % 32:02d}", prompt, options, key, explanation, "speed"))
    return items


def _assert_unique(items: Iterable[Dict[str, Any]]) -> None:
    records = list(items)
    if len({item["id"] for item in records}) != len(records):
        raise ValueError("Generated item IDs must be unique")
    if len({item["prompt"] for item in records}) != len(records):
        raise ValueError("Generated prompts must be unique")


def generated_items() -> List[Dict[str, Any]]:
    all_items = abstract_items() + deductive_items() + numerical_items() + verbal_items() + spatial_items() + memory_items() + speed_items()
    _assert_unique(all_items)
    return all_items
