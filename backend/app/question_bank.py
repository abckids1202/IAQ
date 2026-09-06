"""Original IAQ pilot question bank.

The items below are authored for this project from common reasoning formats,
not copied from a commercial test. They are deliberately marked PILOT: their
actual difficulty, discrimination, fairness, and reliability still require
real response data and psychometric review.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

from .item_factory import generated_items


def _item(item_id: str, domain: str, family: str, prompt: str, options: List[str], answer: str, explanation: str, kind: str = "choice") -> Dict[str, Any]:
    return {
        "id": item_id,
        "item_family_id": family,
        "construct_id": family,
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
        "data_origin": "REVIEWED_CONTENT",
        "content_version": 1,
        "generation_run_id": None,
        "generation_parameters": None,
        "provenance": "Original IAQ reviewed pilot item; not copied from a commercial test.",
        "language": "en",
    }


ABSTRACT: List[Dict[str, Any]] = [
    _item("ABS-001", "abstract_reasoning", "symbol_transform", "A symbol turns 90° clockwise and gains one dot at every step. Which option follows a left-pointing arrow with two dots?", ["A. ↑ with 3 dots", "B. ↓ with 3 dots", "C. → with 3 dots", "D. → with 1 dot"], "C. → with 3 dots", "The rotation is left → up → right and the count increases from two to three."),
    _item("ABS-002", "abstract_reasoning", "symbol_transform", "Across each row, the third tile combines the shape from tile one with the fill pattern from tile two. Which result fits?", ["A. hollow triangle", "B. filled circle", "C. filled triangle", "D. hollow square"], "C. filled triangle", "The third tile keeps the first shape and takes the second tile's fill."),
    _item("ABS-003", "abstract_reasoning", "matrix_count", "A 3×3 grid adds one corner to each shape moving right, then removes one corner moving down. A two-corner shape is at row two, column two. How many corners belong in row three, column three?", ["A. 0", "B. 1", "C. 2", "D. 4"], "B. 1", "The rightward increase and downward decrease cancel once at the diagonal, leaving one corner."),
    _item("ABS-004", "abstract_reasoning", "alternating_rules", "The sequence alternates: mirror horizontally, then rotate 180°. If the current mark is ↗, what is the result after the third transformation?", ["A. ↖", "B. ↙", "C. ↘", "D. ↗"], "B. ↙", "The first mirror gives ↘, the second rotation gives ↖, and the third mirror gives ↙."),
    _item("ABS-005", "abstract_reasoning", "analogy", "Complete the visual analogy: ▲ : ▲▲○ :: ■ : ?", ["A. ■□○", "B. ■■○", "C. □■□", "D. ■○○"], "B. ■■○", "The original shape is repeated, then a hollow circle is appended."),
    _item("ABS-006", "abstract_reasoning", "sequence", "A line moves one position clockwise around a four-sided frame while the number of interior marks follows 1, 2, 4, 7. What is the next mark count?", ["A. 9", "B. 10", "C. 11", "D. 12"], "C. 11", "The increases are +1, +2, +3, so the next increase is +4."),
    _item("ABS-007", "abstract_reasoning", "matrix_count", "In each column, the top symbol is transformed by adding the number of sides shown in the middle symbol. A triangle above a square produces a shape with how many sides?", ["A. 5", "B. 6", "C. 7", "D. 8"], "C. 7", "A triangle has three sides and the square contributes four: 3 + 4 = 7."),
    _item("ABS-008", "abstract_reasoning", "odd_one_out", "Four strings follow the same rule: the second symbol is the first symbol rotated 90°. Which string breaks the rule?", ["A. ↑ →", "B. → ↓", "C. ↓ ←", "D. ← ↑"], "B. → ↓", "A clockwise turn from right points down; the other options are counterclockwise turns."),
    _item("ABS-009", "abstract_reasoning", "symbol_transform", "A pair changes from ○● to ●○, then from ●○ to ○○, then from ○○ to ○●. Which pair comes next if the first symbol cycles ○, ●, ○, ●?", ["A. ○●", "B. ●○", "C. ●●", "D. ○○"], "B. ●○", "The pair shift repeats a three-state cycle; the next state after ○● is ●○."),
    _item("ABS-010", "abstract_reasoning", "matrix_count", "A tile contains 2 triangles and 1 dot. Each step swaps the triangle count and dot count, then adds one dot. What does the next tile contain?", ["A. 1 triangle, 3 dots", "B. 2 triangles, 2 dots", "C. 3 triangles, 1 dot", "D. 1 triangle, 2 dots"], "A. 1 triangle, 3 dots", "Swap 2 and 1, then add one to the new dot count: 1 triangle and 3 dots."),
    _item("ABS-011", "abstract_reasoning", "analogy", "Complete the rule: ◇ is to ◆ as □ is to…", ["A. ○", "B. ■", "C. △", "D. ▽"], "B. ■", "The outline is converted to a filled version of the same shape."),
    _item("ABS-012", "abstract_reasoning", "alternating_rules", "The sequence is: 1 stripe, 2 dots, 3 stripes, 4 dots. Which option is next?", ["A. 5 dots", "B. 5 stripes", "C. 6 stripes", "D. 4 stripes"], "B. 5 stripes", "The count rises by one while the feature alternates stripes, dots, stripes, dots."),
    _item("ABS-013", "abstract_reasoning", "sequence", "Each card has one more side than the previous card and alternates filled, outline, filled, outline. What is card five?", ["A. filled pentagon", "B. outline pentagon", "C. filled hexagon", "D. outline hexagon"], "A. filled pentagon", "Five sides and the fifth position returns to filled."),
    _item("ABS-014", "abstract_reasoning", "odd_one_out", "Which pair is different from the others?", ["A. 2 circles + 1 square", "B. 3 triangles + 1 square", "C. 4 squares + 1 circle", "D. 5 stars + 1 square"], "C. 4 squares + 1 circle", "The other pairs have a different count of the repeated shape and one square as the extra; C repeats squares instead."),
    _item("ABS-015", "abstract_reasoning", "symbol_transform", "A vertical line becomes a horizontal line, then a diagonal line rising right. Following the same 45° turns, what comes next?", ["A. diagonal falling right", "B. vertical line", "C. horizontal line", "D. a circle"], "A. diagonal falling right", "The orientation turns by 45° each step: vertical → horizontal → rising diagonal → falling diagonal."),
    _item("ABS-016", "abstract_reasoning", "matrix_count", "The third row of a grid follows 3, 5, 7, ?. What belongs in the fourth position if the pattern continues?", ["A. 5", "B. 7", "C. 9", "D. 11"], "C. 9", "The row increases by two each time: 3, 5, 7, 9."),
    _item("ABS-017", "abstract_reasoning", "analogy", "A black circle becomes a white square. If the same rule changes a white triangle, what should it become?", ["A. black square", "B. black circle", "C. white square", "D. black triangle"], "A. black square", "The rule swaps fill and moves one step around the shape cycle circle → square → triangle."),
    _item("ABS-018", "abstract_reasoning", "alternating_rules", "A four-symbol code reads ABBC, BCCD, C D D E. Which code continues the pattern?", ["A. DEEF", "B. DDEE", "C. EFFG", "D. CCDD"], "A. DEEF", "Each block advances every symbol by one letter and repeats the middle symbol."),
    _item("ABS-019", "abstract_reasoning", "sequence", "A shape gains 2 marks, loses 1, gains 2, loses 1. Starting at 6 marks, how many marks are in the fifth shape?", ["A. 7", "B. 8", "C. 9", "D. 10"], "B. 8", "The states are 6 → 8 → 7 → 9 → 8."),
    _item("ABS-020", "abstract_reasoning", "odd_one_out", "Which sequence breaks the repeating rule ‘rotate, fill, rotate, fill’ when starting from an outline triangle?", ["A. rotate, fill, rotate, fill", "B. fill, rotate, fill, rotate", "C. rotate, fill, fill, rotate", "D. fill, rotate, fill, rotate"], "C. rotate, fill, fill, rotate", "Only C repeats the same operation twice in the middle."),
]

DEDUCTIVE: List[Dict[str, Any]] = [
    _item("LOG-001", "deductive_logic", "conditional", "Every amber file is reviewed. No reviewed file is deleted. File Q is amber. What must be true?", ["A. Q is deleted", "B. Q is reviewed and not deleted", "C. Q is not amber", "D. Q is archived only"], "B. Q is reviewed and not deleted", "Amber implies reviewed; reviewed excludes deleted."),
    _item("LOG-002", "deductive_logic", "conditional", "If the sensor is active, the green light is on. The green light is off. What follows, assuming the rule is reliable?", ["A. The sensor is active", "B. The sensor is not active", "C. The light is broken", "D. The sensor is red"], "B. The sensor is not active", "This is the contrapositive of active → green light."),
    _item("LOG-003", "deductive_logic", "ordering", "Mira presents before Oki. Oki presents before Sari. Tono presents after Mira but before Oki. Who must present second?", ["A. Mira", "B. Tono", "C. Oki", "D. Sari"], "B. Tono", "The order is Mira, Tono, Oki, Sari."),
    _item("LOG-004", "deductive_logic", "set_relations", "All poets are readers. Some readers are coders. Which conclusion is guaranteed?", ["A. All coders are poets", "B. Some poets are coders", "C. Every poet is a reader", "D. No coder is a reader"], "C. Every poet is a reader", "Only the first universal statement guarantees a conclusion about poets."),
    _item("LOG-005", "deductive_logic", "constraint", "A code has three different letters. K is before M. R is not first. Which code is possible?", ["A. RKM", "B. MKR", "C. KRM", "D. MRK"], "C. KRM", "K is before M and R is in the middle, satisfying both constraints."),
    _item("LOG-006", "deductive_logic", "conditional", "If a student chooses music, they attend rehearsal. Hana does not attend rehearsal. What can be concluded?", ["A. Hana chooses music", "B. Hana does not choose music", "C. Hana attends another club", "D. Nothing about music can be concluded"], "B. Hana does not choose music", "Not attending rehearsal rules out choosing music under the stated rule."),
    _item("LOG-007", "deductive_logic", "ordering", "Five cards are ordered. P is immediately before Q. Q is immediately before R. Which statement must be true?", ["A. P is first", "B. R is last", "C. P is two places before R", "D. Q is first"], "C. P is two places before R", "The consecutive block P-Q-R fixes the distance between P and R."),
    _item("LOG-008", "deductive_logic", "set_relations", "No silver tools are fragile. Some tools are silver. What must be true of those silver tools?", ["A. They are fragile", "B. They are not fragile", "C. They are wooden", "D. They are unused"], "B. They are not fragile", "The universal exclusion applies to every silver tool."),
    _item("LOG-009", "deductive_logic", "constraint", "A project uses exactly two of red, blue, and green. It cannot use red with blue. Which pair is possible?", ["A. red and blue", "B. red and green", "C. blue and red", "D. all three"], "B. red and green", "Red-green is the only listed pair that obeys the exclusion and two-item rule."),
    _item("LOG-010", "deductive_logic", "conditional", "Either the key is in the drawer or it is in the bag, but not both. It is not in the drawer. Where must it be?", ["A. In the bag", "B. On the desk", "C. In both", "D. Nowhere"], "A. In the bag", "The exclusive-or condition leaves the bag as the only remaining location."),
    _item("LOG-011", "deductive_logic", "ordering", "N is taller than P. P is taller than Q. R is taller than N. Who is shortest?", ["A. N", "B. P", "C. Q", "D. R"], "C. Q", "The chain is R > N > P > Q."),
    _item("LOG-012", "deductive_logic", "set_relations", "Every ceramic object is breakable. Some breakable objects are valuable. Which is valid?", ["A. All valuable objects are ceramic", "B. Some ceramic objects are valuable", "C. Every ceramic object is breakable", "D. No ceramic object is valuable"], "C. Every ceramic object is breakable", "The other statements reverse or overextend the given relationships."),
    _item("LOG-013", "deductive_logic", "constraint", "A four-digit lock uses 1, 2, 3, and 4 once each. 1 is not first, 4 is after 2, and 3 is before 1. Which code works?", ["A. 1234", "B. 2314", "C. 3124", "D. 4213"], "B. 2314", "2 < 3 < 1 < 4 meets every condition."),
    _item("LOG-014", "deductive_logic", "conditional", "All approved projects have a reviewer. Project L has no reviewer. What must be true?", ["A. L is approved", "B. L is not approved", "C. L is complete", "D. L is high quality"], "B. L is not approved", "No reviewer is incompatible with the necessary condition for approval."),
    _item("LOG-015", "deductive_logic", "ordering", "J sits left of K. L sits right of K. M sits left of J. Which item is second from the left?", ["A. M", "B. J", "C. K", "D. L"], "B. J", "The only possible order is M, J, K, L."),
    _item("LOG-016", "deductive_logic", "set_relations", "Some athletes are artists. All artists are observant. What must be true about some athletes?", ["A. They are observant", "B. They are not artists", "C. All athletes are observant", "D. No athlete is observant"], "A. They are observant", "The athletes who are artists inherit the artist property."),
    _item("LOG-017", "deductive_logic", "constraint", "A team has exactly one captain and one recorder. Lina cannot be captain. Omar cannot be recorder. Which assignment is possible?", ["A. Lina captain, Omar recorder", "B. Omar captain, Lina recorder", "C. Lina both roles", "D. Omar both roles"], "B. Omar captain, Lina recorder", "Both role exclusions are satisfied."),
    _item("LOG-018", "deductive_logic", "conditional", "If the alarm sounds, the building is evacuated. The building was not evacuated. Which must be true?", ["A. The alarm sounded", "B. The alarm did not sound", "C. The building was empty", "D. The alarm was silent and broken"], "B. The alarm did not sound", "The contrapositive rules out an alarm when no evacuation occurred."),
    _item("LOG-019", "deductive_logic", "ordering", "A, B, C, and D are ranked. A is higher than C. D is lower than B but higher than C. Which ranking is possible?", ["A. C-D-B-A", "B. B-A-D-C", "C. A-C-D-B", "D. D-C-B-A"], "B. B-A-D-C", "A > C and B > D > C both hold in B."),
    _item("LOG-020", "deductive_logic", "set_relations", "No blueprints are digital. All plans are blueprints. Which must be true?", ["A. No plans are digital", "B. Some plans are digital", "C. All digital things are plans", "D. Some blueprints are not plans"], "A. No plans are digital", "Plans inherit the non-digital property of blueprints."),
]

NUMERICAL: List[Dict[str, Any]] = [
    _item("NUM-001", "numerical_reasoning", "sequence", "Complete the sequence: 4, 7, 13, 25, 49, ?", ["A. 73", "B. 85", "C. 97", "D. 101"], "C. 97", "Each term is doubled, then one is subtracted."),
    _item("NUM-002", "numerical_reasoning", "sequence", "Complete the sequence: 2, 6, 12, 20, 30, ?", ["A. 36", "B. 40", "C. 42", "D. 44"], "C. 42", "The differences are +4, +6, +8, +10, then +12."),
    _item("NUM-003", "numerical_reasoning", "sequence", "Complete the sequence: 81, 27, 9, 3, ?", ["A. 0", "B. 1", "C. 2", "D. 6"], "B. 1", "Each term is divided by three."),
    _item("NUM-004", "numerical_reasoning", "sequence", "Complete the sequence: 5, 8, 14, 26, 50, ?", ["A. 74", "B. 86", "C. 98", "D. 102"], "C. 98", "Each term doubles and subtracts two."),
    _item("NUM-005", "numerical_reasoning", "fibonacci", "Complete the sequence: 2, 3, 5, 8, 13, ?", ["A. 18", "B. 20", "C. 21", "D. 22"], "C. 21", "Each term is the sum of the two previous terms."),
    _item("NUM-006", "numerical_reasoning", "sequence", "Complete the sequence: 7, 10, 16, 28, 52, ?", ["A. 76", "B. 88", "C. 100", "D. 104"], "C. 100", "The differences double: +3, +6, +12, +24, then +48."),
    _item("NUM-007", "numerical_reasoning", "sequence", "Complete the sequence: 1, 4, 10, 22, 46, ?", ["A. 70", "B. 82", "C. 94", "D. 96"], "C. 94", "Each term doubles and adds two."),
    _item("NUM-008", "numerical_reasoning", "squares", "Complete the sequence: 144, 121, 100, 81, ?", ["A. 64", "B. 66", "C. 68", "D. 72"], "A. 64", "These are descending squares: 12², 11², 10², 9², 8²."),
    _item("NUM-009", "numerical_reasoning", "powers", "Complete the sequence: 3, 9, 27, 81, ?", ["A. 162", "B. 189", "C. 243", "D. 324"], "C. 243", "Each term is multiplied by three."),
    _item("NUM-010", "numerical_reasoning", "differences", "Complete the sequence: 11, 14, 20, 29, 41, ?", ["A. 53", "B. 54", "C. 56", "D. 58"], "C. 56", "The differences are +3, +6, +9, +12, then +15."),
    _item("NUM-011", "numerical_reasoning", "sequence", "Complete the sequence: 2, 5, 11, 23, 47, ?", ["A. 71", "B. 83", "C. 94", "D. 95"], "D. 95", "Each term doubles and adds one."),
    _item("NUM-012", "numerical_reasoning", "division", "Complete the sequence: 96, 48, 24, 12, ?", ["A. 3", "B. 4", "C. 6", "D. 8"], "C. 6", "Each term is halved."),
    _item("NUM-013", "numerical_reasoning", "sequence", "Complete the sequence: 4, 9, 19, 39, ?", ["A. 59", "B. 69", "C. 79", "D. 89"], "C. 79", "Each term doubles and adds one."),
    _item("NUM-014", "numerical_reasoning", "sequence", "Complete the sequence: 6, 13, 27, 55, ?", ["A. 83", "B. 101", "C. 109", "D. 111"], "D. 111", "Each term doubles and adds one."),
    _item("NUM-015", "numerical_reasoning", "factorial", "Complete the sequence: 1, 2, 6, 24, ?", ["A. 60", "B. 96", "C. 100", "D. 120"], "D. 120", "Multiply successively by 2, 3, 4, then 5."),
    _item("NUM-016", "numerical_reasoning", "differences", "Complete the sequence: 12, 17, 27, 42, 62, ?", ["A. 82", "B. 85", "C. 87", "D. 92"], "C. 87", "The differences are +5, +10, +15, +20, then +25."),
    _item("NUM-017", "numerical_reasoning", "powers", "Complete the sequence: 1, 8, 27, 64, ?", ["A. 81", "B. 100", "C. 125", "D. 144"], "C. 125", "These are consecutive cubes: 1³, 2³, 3³, 4³, 5³."),
    _item("NUM-018", "numerical_reasoning", "sequence", "Complete the sequence: 2, 4, 10, 28, 82, ?", ["A. 164", "B. 208", "C. 244", "D. 246"], "C. 244", "Each term is multiplied by three and then two is subtracted."),
    _item("NUM-019", "numerical_reasoning", "differences", "Complete the sequence: 50, 45, 37, 26, 12, ?", ["A. -3", "B. -5", "C. -7", "D. 0"], "B. -5", "The differences are -5, -8, -11, -14, then -17: 12 - 17 = -5."),
    _item("NUM-020", "numerical_reasoning", "sequence", "Complete the sequence: 2, 7, 17, 37, 77, ?", ["A. 137", "B. 147", "C. 157", "D. 167"], "C. 157", "Each term doubles and adds three."),
]

VERBAL: List[Dict[str, Any]] = [
    _item("VRB-001", "verbal_reasoning", "analogy", "Compass is to direction as thermometer is to…", ["A. weather", "B. temperature", "C. glass", "D. pressure"], "B. temperature", "A compass measures or indicates direction; a thermometer indicates temperature."),
    _item("VRB-002", "verbal_reasoning", "analogy", "Blueprint is to building as outline is to…", ["A. essay", "B. pencil", "C. paper", "D. library"], "A. essay", "An outline structures an essay in the way a blueprint structures a building."),
    _item("VRB-003", "verbal_reasoning", "inference", "The museum extended its evening hours. Attendance after 6 p.m. rose by 30%. Which statement is best supported?", ["A. All visitors prefer evenings", "B. Evening access became more popular after the extension", "C. Morning attendance fell", "D. The museum became free"], "B. Evening access became more popular after the extension", "The data supports a change in evening attendance, not the stronger universal claims."),
    _item("VRB-004", "verbal_reasoning", "classification", "Which word does not belong with the others?", ["A. cautious", "B. prudent", "C. reckless", "D. careful"], "C. reckless", "The other three describe careful decision-making."),
    _item("VRB-005", "verbal_reasoning", "analogy", "Scarce is to abundant as rigid is to…", ["A. narrow", "B. flexible", "C. heavy", "D. formal"], "B. flexible", "The relationship is opposites."),
    _item("VRB-006", "verbal_reasoning", "inference", "A notice says: ‘The trail is open, but the northern bridge is closed.’ Which route is definitely unavailable?", ["A. the southern trail", "B. the northern bridge", "C. the whole trail", "D. every bridge"], "B. the northern bridge", "Only the northern bridge is explicitly closed."),
    _item("VRB-007", "verbal_reasoning", "classification", "Which pair has the same relationship as seed : tree?", ["A. page : book", "B. egg : bird", "C. wheel : road", "D. paint : brush"], "B. egg : bird", "A seed can develop into a tree as an egg can develop into a bird."),
    _item("VRB-008", "verbal_reasoning", "inference", "A study group meets on Tuesday unless the library closes early. The library closed early Tuesday. What can be inferred?", ["A. The group definitely met", "B. The group may not have met", "C. The library was open all day", "D. The group moved to Friday"], "B. The group may not have met", "The early closure creates a possible exception but does not prove what the group did."),
    _item("VRB-009", "verbal_reasoning", "analogy", "Edit is to manuscript as debug is to…", ["A. program", "B. keyboard", "C. screen", "D. password"], "A. program", "Both are processes for finding and correcting issues in a work."),
    _item("VRB-010", "verbal_reasoning", "classification", "Which word is closest in meaning to ‘subtle’?", ["A. obvious", "B. delicate", "C. enormous", "D. noisy"], "B. delicate", "Subtle can mean not obvious, fine, or delicate."),
    _item("VRB-011", "verbal_reasoning", "inference", "A cafe sold more tea after adding a quiet study area. Which conclusion is cautious and supported?", ["A. The study area may have attracted tea customers", "B. Tea caused every visitor to study", "C. Coffee sales fell to zero", "D. All customers prefer silence"], "A. The study area may have attracted tea customers", "The association supports a possible explanation, not certainty about every customer."),
    _item("VRB-012", "verbal_reasoning", "analogy", "Archive is to preserve as filter is to…", ["A. remove", "B. collect", "C. enlarge", "D. colour"], "A. remove", "An archive preserves selected material; a filter removes what does not meet a criterion."),
    _item("VRB-013", "verbal_reasoning", "classification", "Which statement is most precise?", ["A. Some metals conduct electricity", "B. All metals are magnets", "C. Every metal is liquid", "D. No metal conducts heat"], "A. Some metals conduct electricity", "The statement is plausible and appropriately limited rather than universal."),
    _item("VRB-014", "verbal_reasoning", "inference", "The first draft received clear feedback, but the final version was not submitted. What is certain?", ["A. The draft was perfect", "B. The writer received feedback", "C. The final version was rejected", "D. The project was cancelled"], "B. The writer received feedback", "Only the feedback is explicitly established."),
    _item("VRB-015", "verbal_reasoning", "analogy", "Motive is to action as premise is to…", ["A. conclusion", "B. question", "C. colour", "D. audience"], "A. conclusion", "A motive supports an action; a premise supports a conclusion."),
    _item("VRB-016", "verbal_reasoning", "classification", "Which word is the odd one out?", ["A. violin", "B. cello", "C. flute", "D. easel"], "D. easel", "The first three are musical instruments; an easel is not."),
    _item("VRB-017", "verbal_reasoning", "inference", "‘The team tested the prototype twice before changing the material.’ What does this imply?", ["A. The material was changed before any testing", "B. Testing happened before the material change", "C. The prototype was never tested", "D. The material was unchanged"], "B. Testing happened before the material change", "The sentence gives a clear sequence."),
    _item("VRB-018", "verbal_reasoning", "analogy", "Transparent is to visible as audible is to…", ["A. spoken", "B. hearable", "C. written", "D. silent"], "B. hearable", "Both pairs connect a quality with the sense that can detect it."),
    _item("VRB-019", "verbal_reasoning", "classification", "Which pair are closest opposites?", ["A. expand / contract", "B. ask / wonder", "C. repair / build", "D. watch / see"], "A. expand / contract", "These words have directly opposite meanings."),
    _item("VRB-020", "verbal_reasoning", "inference", "A report says: ‘Students who used the planner completed more tasks; the study was observational.’ What is the safest reading?", ["A. The planner definitely caused completion", "B. Planner use was associated with more completed tasks", "C. The planner never helps", "D. Students were randomly assigned"], "B. Planner use was associated with more completed tasks", "Observational evidence supports association, not a causal claim."),
]

SPATIAL: List[Dict[str, Any]] = [
    _item("SPA-001", "visual_spatial_reasoning", "rotation", "An L-shape points up with its short arm to the right. Rotate it 90° clockwise. Where does the short arm point?", ["A. up", "B. down", "C. left", "D. right"], "B. down", "A clockwise rotation moves the short arm from right to down."),
    _item("SPA-002", "visual_spatial_reasoning", "reflection", "A dot is in the upper-left corner of a square. Reflect the square across its vertical centre line. Where is the dot?", ["A. upper-left", "B. upper-right", "C. lower-left", "D. lower-right"], "B. upper-right", "A vertical reflection reverses left and right but keeps height."),
    _item("SPA-003", "visual_spatial_reasoning", "cube", "A cube has a star on top and a dot on the front. It is rolled forward once. Which face is now on top?", ["A. the star face", "B. the dot face", "C. the bottom face", "D. the back face"], "B. the dot face", "Rolling forward brings the former front face to the top."),
    _item("SPA-004", "visual_spatial_reasoning", "folding", "A strip is folded in half twice. A hole is punched through the folded strip. How many holes appear when it is opened?", ["A. 1", "B. 2", "C. 3", "D. 4"], "D. 4", "Two folds stack four layers, so one punch makes four matching holes."),
    _item("SPA-005", "visual_spatial_reasoning", "rotation", "A triangle with a mark on its left side is rotated 180°. Where is the mark relative to the triangle?", ["A. still left", "B. right", "C. above", "D. below"], "B. right", "A half-turn swaps left and right."),
    _item("SPA-006", "visual_spatial_reasoning", "net", "Which set of four faces can form a tetrahedron?", ["A. four triangles", "B. three squares and a circle", "C. two triangles and two circles", "D. one square and three circles"], "A. four triangles", "A tetrahedron has four triangular faces."),
    _item("SPA-007", "visual_spatial_reasoning", "grid_path", "On a grid, move 2 squares east, 1 north, 2 west, and 3 south. Where are you relative to the start?", ["A. 2 north", "B. 2 south", "C. 1 north", "D. 1 south"], "B. 2 south", "East and west cancel; north 1 and south 3 leave two south."),
    _item("SPA-008", "visual_spatial_reasoning", "reflection", "A diagonal arrow points up-right. Reflect it across a horizontal line. Which way does it point?", ["A. up-left", "B. down-right", "C. down-left", "D. up-right"], "B. down-right", "Horizontal reflection reverses vertical direction but keeps horizontal direction."),
    _item("SPA-009", "visual_spatial_reasoning", "rotation", "A clock hand points at 2. Rotate the clock hand 180°. Which number does it point toward?", ["A. 6", "B. 7", "C. 8", "D. 10"], "C. 8", "A half-turn from 2 lands at 8."),
    _item("SPA-010", "visual_spatial_reasoning", "cube", "Opposite faces on a cube are paired 1–6, 2–5, and 3–4. Which face is opposite 5?", ["A. 1", "B. 2", "C. 3", "D. 6"], "B. 2", "The given pairing directly identifies the opposite face."),
    _item("SPA-011", "visual_spatial_reasoning", "folding", "A rectangular sheet is folded once vertically and once horizontally. A corner is cut away from the folded packet. How many matching cut-outs appear when opened?", ["A. 2", "B. 3", "C. 4", "D. 8"], "C. 4", "Two independent folds create four layers."),
    _item("SPA-012", "visual_spatial_reasoning", "grid_path", "A token moves north, east, east, south, west. What is its final position relative to the start?", ["A. one east and one north", "B. one east and one south", "C. one west and one north", "D. back at the start"], "A. one east and one north", "The two east moves minus one west leave one east; north minus south leaves one north."),
    _item("SPA-013", "visual_spatial_reasoning", "net", "A cube net has four squares in a row. A square is attached above the second square and another below the third. Which shape can close into a cube?", ["A. the described net", "B. six triangles", "C. five squares only", "D. a circle with five squares"], "A. the described net", "Six connected squares in this cross-like arrangement form a standard cube net."),
    _item("SPA-014", "visual_spatial_reasoning", "reflection", "A pattern has black cells at top-left and bottom-right. Reflect it across the main diagonal. What changes?", ["A. the pattern stays the same", "B. both cells move to the other diagonal", "C. only the top-left cell moves", "D. both cells disappear"], "A. the pattern stays the same", "Cells on the main diagonal stay fixed under that reflection."),
    _item("SPA-015", "visual_spatial_reasoning", "rotation", "A rectangle is twice as wide as it is tall. After a 90° rotation, which description is correct?", ["A. twice as wide", "B. twice as tall", "C. square", "D. same orientation"], "B. twice as tall", "Width and height swap after a quarter-turn."),
    _item("SPA-016", "visual_spatial_reasoning", "cube", "A cube is painted on every outside face and cut into 27 equal small cubes. How many small cubes have paint on exactly two faces?", ["A. 8", "B. 12", "C. 16", "D. 24"], "B. 12", "The edge-center cubes contribute 12 cubes with exactly two painted faces."),
    _item("SPA-017", "visual_spatial_reasoning", "grid_path", "From the origin, travel 3 north, 4 east, 3 south, and 1 west. What is the shortest direct distance back to the origin?", ["A. 2", "B. 3", "C. 4", "D. 5"], "B. 3", "The final position is 3 east of the origin."),
    _item("SPA-018", "visual_spatial_reasoning", "folding", "A paper strip is folded into thirds, creating three layers. Two holes are punched through the packet. If the punches are far apart, how many holes are visible when opened?", ["A. 2", "B. 3", "C. 5", "D. 6"], "D. 6", "Each punch passes through three layers and the holes do not overlap."),
    _item("SPA-019", "visual_spatial_reasoning", "reflection", "A capital letter F is reflected across a vertical mirror. Which feature changes?", ["A. its height", "B. its top bar moves to the bottom", "C. its vertical stem moves to the opposite side", "D. nothing"], "C. its vertical stem moves to the opposite side", "A vertical mirror reverses left and right."),
    _item("SPA-020", "visual_spatial_reasoning", "rotation", "A compass arrow points north-east. Rotate it 270° clockwise. Which direction does it point?", ["A. north-west", "B. south-west", "C. south-east", "D. north-east"], "B. south-west", "Three clockwise quarter-turns from north-east land on south-west."),
]

MEMORY: List[Dict[str, Any]] = [
    _item("MEM-001", "working_memory", "sequence_recall", "Remember the order 7 — 2 — 9 — 4. Which option matches it?", ["A. 7 — 2 — 9 — 4", "B. 7 — 9 — 2 — 4", "C. 2 — 7 — 4 — 9", "D. 9 — 4 — 7 — 2"], "A. 7 — 2 — 9 — 4", "The correct response preserves all four positions.", "memory"),
    _item("MEM-002", "working_memory", "sequence_recall", "Remember K — M — R — T. Which option reverses the sequence?", ["A. K — M — R — T", "B. T — R — M — K", "C. M — K — T — R", "D. R — T — K — M"], "B. T — R — M — K", "Reversal reads the last item first and the first item last.", "memory"),
    _item("MEM-003", "working_memory", "updating", "Start with 4. Add 3, double the result, then subtract 2. What is the final number?", ["A. 10", "B. 11", "C. 12", "D. 16"], "C. 12", "4 + 3 = 7; 7 × 2 = 14; 14 − 2 = 12.", "memory"),
    _item("MEM-004", "working_memory", "sequence_recall", "Remember red — blue — green — yellow — black. Which colour was third?", ["A. red", "B. blue", "C. green", "D. black"], "C. green", "Green occupies the third position.", "memory"),
    _item("MEM-005", "working_memory", "updating", "Begin at 10. Subtract 4, add 6, subtract 3, then add 2. What remains?", ["A. 9", "B. 10", "C. 11", "D. 12"], "C. 11", "10 − 4 + 6 − 3 + 2 = 11.", "memory"),
    _item("MEM-006", "working_memory", "sequence_recall", "Remember 3 — 8 — 1 — 6 — 4. Which number was immediately after 1?", ["A. 3", "B. 8", "C. 6", "D. 4"], "C. 6", "The sequence places 6 immediately after 1.", "memory"),
    _item("MEM-007", "working_memory", "updating", "Start at 2. Multiply by 3, add 4, halve the result, then add 1. What is the final number?", ["A. 6", "B. 7", "C. 8", "D. 9"], "A. 6", "2 × 3 = 6; +4 = 10; halving gives 5; +1 = 6.", "memory"),
    _item("MEM-008", "working_memory", "sequence_recall", "Remember north — east — south — west — north. How many times does north appear?", ["A. 1", "B. 2", "C. 3", "D. 4"], "B. 2", "North appears at the beginning and end.", "memory"),
    _item("MEM-009", "working_memory", "updating", "Keep 5, 8, and 2 in mind. Add the first and third, then multiply by the second. What is the result?", ["A. 26", "B. 42", "C. 56", "D. 64"], "C. 56", "(5 + 2) × 8 = 56."),
    _item("MEM-010", "working_memory", "sequence_recall", "Remember 14 — 6 — 11 — 3 — 9. Which option lists the second and fourth numbers?", ["A. 14 — 11", "B. 6 — 3", "C. 11 — 9", "D. 3 — 14"], "B. 6 — 3", "Positions two and four are 6 and 3.", "memory"),
    _item("MEM-011", "working_memory", "updating", "Start at 9. Double it, subtract 6, then divide by 2. What is the result?", ["A. 4", "B. 5", "C. 6", "D. 7"], "C. 6", "9 × 2 = 18; 18 − 6 = 12; 12 ÷ 2 = 6."),
    _item("MEM-012", "working_memory", "sequence_recall", "Remember A — C — F — B — D. Which letter was between F and D?", ["A. A", "B. C", "C. B", "D. D"], "C. B", "B sits after F and before D.", "memory"),
    _item("MEM-013", "working_memory", "updating", "Start at 3. Add 4, multiply by 2, subtract 5, add 6. What is the result?", ["A. 15", "B. 17", "C. 19", "D. 21"], "A. 15", "3 + 4 = 7; ×2 = 14; −5 = 9; +6 = 15."),
    _item("MEM-014", "working_memory", "sequence_recall", "Remember 2 — 5 — 7 — 1 — 8 — 4. Which two numbers are at the ends?", ["A. 2 and 8", "B. 5 and 4", "C. 2 and 4", "D. 7 and 1"], "C. 2 and 4", "The first and last entries are 2 and 4.", "memory"),
    _item("MEM-015", "working_memory", "updating", "Hold 12. Replace it with 12 minus 5, then replace the result with three times itself. What is held?", ["A. 7", "B. 15", "C. 21", "D. 36"], "C. 21", "12 − 5 = 7; 7 × 3 = 21.", "memory"),
    _item("MEM-016", "working_memory", "sequence_recall", "Remember circle — triangle — star — square. Which shape was immediately before star?", ["A. circle", "B. triangle", "C. star", "D. square"], "B. triangle", "Triangle comes immediately before star.", "memory"),
    _item("MEM-017", "working_memory", "updating", "Start with 1, 4, and 6. Subtract the first from the last, then add the middle. What is the result?", ["A. 7", "B. 8", "C. 9", "D. 10"], "C. 9", "6 − 1 + 4 = 9."),
    _item("MEM-018", "working_memory", "sequence_recall", "Remember 9 — 2 — 5 — 8 — 1. Which option contains the sequence with the middle item removed?", ["A. 9 — 2 — 8 — 1", "B. 9 — 5 — 8 — 1", "C. 2 — 5 — 8 — 1", "D. 9 — 2 — 5 — 1"], "A. 9 — 2 — 8 — 1", "Removing the middle item, 5, leaves 9, 2, 8, 1.", "memory"),
    _item("MEM-019", "working_memory", "updating", "Begin with 20. Halve it, add 9, then subtract 4. What is the final value?", ["A. 12", "B. 14", "C. 15", "D. 16"], "C. 15", "20 ÷ 2 + 9 − 4 = 15.", "memory"),
    _item("MEM-020", "working_memory", "sequence_recall", "Remember B — 4 — Q — 7 — M. Which entry was fourth?", ["A. B", "B. 4", "C. Q", "D. 7"], "D. 7", "The fourth entry is 7.", "memory"),
]

SPEED: List[Dict[str, Any]] = [
    _item("SPD-001", "processing_speed", "visual_search", "Find the only exact match for the target pair ◇◆.", ["A. ◆◇", "B. ◇◆", "C. ◇◇", "D. ◆◆"], "B. ◇◆", "Only B preserves both symbol identity and order.", "speed"),
    _item("SPD-002", "processing_speed", "symbol_match", "Which row contains two identical symbols next to each other?", ["A. △ ○ □", "B. ○ □ △", "C. □ □ ◇", "D. ◇ △ ○"], "C. □ □ ◇", "The square pair appears only in C.", "speed"),
    _item("SPD-003", "processing_speed", "visual_search", "Target: 731. Which option matches exactly?", ["A. 713", "B. 731", "C. 371", "D. 733"], "B. 731", "Only B matches all three positions.", "speed"),
    _item("SPD-004", "processing_speed", "symbol_match", "Which option is different from the other three?", ["A. ▲●▲", "B. ▲●▲", "C. ▲○▲", "D. ▲●▲"], "C. ▲○▲", "C uses a hollow circle where the others use a filled circle.", "speed"),
    _item("SPD-005", "processing_speed", "visual_search", "Find the pair with the same outer shape and opposite fill.", ["A. ■ / □", "B. ○ / ◇", "C. △ / ◆", "D. ★ / ☆"], "A. ■ / □", "A keeps the square shape and changes only fill.", "speed"),
    _item("SPD-006", "processing_speed", "symbol_match", "Which sequence contains exactly one triangle?", ["A. ○ □ ◇", "B. △ □ ○", "C. △ △ ○", "D. ◇ □ ○"], "B. △ □ ○", "B contains one triangle; C contains two and the others none.", "speed"),
    _item("SPD-007", "processing_speed", "visual_search", "Target: ABBA. Which option is the exact reverse?", ["A. ABBA", "B. BAAB", "C. ABBB", "D. BABA"], "A. ABBA", "ABBA reads the same forward and backward.", "speed"),
    _item("SPD-008", "processing_speed", "symbol_match", "Which row has the symbols in alphabetical order by their labels: circle, square, triangle?", ["A. ○ □ △", "B. △ ○ □", "C. □ △ ○", "D. ○ △ □"], "A. ○ □ △", "The requested order is circle, square, triangle.", "speed"),
    _item("SPD-009", "processing_speed", "visual_search", "Which number appears twice in the row 4 8 2 9 6 8 1?", ["A. 4", "B. 6", "C. 8", "D. 9"], "C. 8", "Eight is the only repeated number.", "speed"),
    _item("SPD-010", "processing_speed", "symbol_match", "Which pair differs only by a 180° rotation?", ["A. ↑ / ↓", "B. → / ↑", "C. ◇ / □", "D. ○ / ●"], "A. ↑ / ↓", "Opposite arrows are related by a half-turn.", "speed"),
    _item("SPD-011", "processing_speed", "visual_search", "Find the option with exactly two vowels:", ["A. RST", "B. IDEA", "C. BRK", "D. CLOUD"], "B. IDEA", "IDEA contains I and E; CLOUD contains three vowels.", "speed"),
    _item("SPD-012", "processing_speed", "symbol_match", "Which option repeats the first and last symbol?", ["A. ● △ ●", "B. ● △ ○", "C. □ ○ △", "D. △ □ ○"], "A. ● △ ●", "Only A starts and ends with the same symbol.", "speed"),
    _item("SPD-013", "processing_speed", "visual_search", "Target: 5-2-8. Which code is missing the middle digit?", ["A. 5-8", "B. 2-8", "C. 5-2", "D. 8-2"], "A. 5-8", "Removing 2 from 5-2-8 leaves 5-8.", "speed"),
    _item("SPD-014", "processing_speed", "symbol_match", "Which group has the greatest number of four-sided shapes?", ["A. □ □ ○", "B. △ □ ○", "C. □ ◇ □", "D. ○ △ ◇"], "C. □ ◇ □", "C has three quadrilateral shapes: square, diamond, square.", "speed"),
    _item("SPD-015", "processing_speed", "visual_search", "Which word is identical to the target ‘MIRROR’?", ["A. MIRROR", "B. MIRR0R", "C. MIRORR", "D. MIRRORR"], "A. MIRROR", "Only A matches every character.", "speed"),
    _item("SPD-016", "processing_speed", "symbol_match", "Which pair has matching inner symbols?", ["A. [○] / [○]", "B. [□] / [◇]", "C. [△] / [○]", "D. [★] / [☆]"], "A. [○] / [○]", "The two inner symbols are exactly the same in A.", "speed"),
    _item("SPD-017", "processing_speed", "visual_search", "Which row contains the sequence 2, 4, 6 in that order?", ["A. 2 6 4", "B. 4 2 6", "C. 2 4 6", "D. 6 4 2"], "C. 2 4 6", "Only C preserves the target order.", "speed"),
    _item("SPD-018", "processing_speed", "symbol_match", "Which item has an odd number of marks?", ["A. ••••", "B. •••", "C. ••••", "D. ••••"], "B. •••", "B contains three marks; the other options contain four.", "speed"),
    _item("SPD-019", "processing_speed", "visual_search", "Which option contains two consecutive letters followed by a number?", ["A. A7BC", "B. AB7C", "C. A7B8", "D. 7ABC"], "B. AB7C", "A and B are consecutive letters at the start, followed by 7.", "speed"),
    _item("SPD-020", "processing_speed", "symbol_match", "Which line has the same symbol at positions two and four?", ["A. ○ △ □ △", "B. □ ○ △ ○", "C. △ □ ○ △", "D. ◇ ○ □ △"], "A. ○ △ □ △", "A has triangles at positions two and four.", "speed"),
]


MINIMUM_ITEMS_PER_DOMAIN = 20
TARGET_ITEMS_PER_DOMAIN = 120

QUESTION_BANK: List[Dict[str, Any]] = ABSTRACT + DEDUCTIVE + NUMERICAL + VERBAL + SPATIAL + MEMORY + SPEED + generated_items()


def bank_counts(items: Iterable[Dict[str, Any]] = QUESTION_BANK) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in items:
        counts[item["domain"]] = counts.get(item["domain"], 0) + 1
    return counts


def bank_is_ready(items: Iterable[Dict[str, Any]] = QUESTION_BANK, minimum_per_domain: int = 20) -> bool:
    counts = bank_counts(items)
    return len(counts) == 7 and all(value >= minimum_per_domain for value in counts.values())
