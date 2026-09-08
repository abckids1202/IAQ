import type { Domain, Major, Question } from './types'

export const domains: Domain[] = [
  'Abstract reasoning',
  'Deductive logic',
  'Numerical reasoning',
  'Verbal reasoning',
  'Visual-spatial reasoning',
  'Working memory',
  'Processing speed'
]

export const domainMeta: Record<Domain, { short: string; description: string; tone: string }> = {
  'Abstract reasoning': { short: 'Abstract', description: 'Inferring unfamiliar rules and relationships.', tone: 'blue' },
  'Deductive logic': { short: 'Logic', description: 'Moving from conditions to a sound conclusion.', tone: 'teal' },
  'Numerical reasoning': { short: 'Numerical', description: 'Recognising quantitative patterns and structure.', tone: 'orange' },
  'Verbal reasoning': { short: 'Verbal', description: 'Working with meaning, evidence and language.', tone: 'rose' },
  'Visual-spatial reasoning': { short: 'Spatial', description: 'Manipulating shape, position and visual systems.', tone: 'violet' },
  'Working memory': { short: 'Memory', description: 'Holding and updating information briefly.', tone: 'green' },
  'Processing speed': { short: 'Speed', description: 'Accurate visual attention under time pressure.', tone: 'yellow' }
}

export const questions: Question[] = [
  { id: 'abs-01', domain: 'Abstract reasoning', type: 'choice', prompt: 'Each tile changes by the same rule. Which tile completes the sequence?', helper: 'The visual is intentionally simple: look for the relationship across rows and columns.', options: ['A  ●●○', 'B  ○●●', 'C  ●○●', 'D  ○○●'], visual: ['◆ ○', '○ ◆', '◆ ?'] },
  { id: 'logic-01', domain: 'Deductive logic', type: 'choice', prompt: 'All red notebooks are archived. This notebook is red. What must be true?', options: ['It is archived', 'It is new', 'It is blue', 'Nothing can be concluded'] },
  { id: 'num-01', domain: 'Numerical reasoning', type: 'sequence', prompt: 'Complete the sequence: 3, 6, 12, 24, __', helper: 'You may use mental arithmetic or write a quick note.', options: ['30', '36', '42', '48'] },
  { id: 'verbal-01', domain: 'Verbal reasoning', type: 'choice', prompt: 'A map is to navigation as a score is to…', options: ['Music', 'Evaluation', 'Paper', 'Competition'] },
  { id: 'spatial-01', domain: 'Visual-spatial reasoning', type: 'choice', prompt: 'Imagine the L-shape rotates 90° clockwise. Which direction does its short arm point?', helper: 'Use the shape preview to anchor the rotation.', options: ['Up', 'Down', 'Left', 'Right'], visual: ['■ □', '■ ■'] },
  { id: 'memory-01', domain: 'Working memory', type: 'memory', prompt: 'Remember this sequence, then select it in the same order.', helper: 'The sequence will be hidden after a short moment.', options: ['7 — 2 — 9 — 4', '7 — 9 — 2 — 4', '2 — 7 — 4 — 9', '9 — 4 — 7 — 2'] },
  { id: 'speed-01', domain: 'Processing speed', type: 'speed', prompt: 'Find the only pair of matching symbols.', helper: 'Accuracy matters more than rushing. This is a baseline attention task.', options: ['△ ○  □', '◇ △  ○', '□ ◇  △', '○ □  ◇'] },
  { id: 'abs-02', domain: 'Abstract reasoning', type: 'choice', prompt: 'If ▲ becomes ▶, then ◀ becomes…', options: ['▲', '▼', '◆', '●'] },
  { id: 'logic-02', domain: 'Deductive logic', type: 'choice', prompt: 'If the studio is open, the green light is on. The green light is off. Which conclusion is safest?', options: ['The studio is closed', 'The studio is open', 'The light is broken', 'The studio is probably busy'] },
  { id: 'num-02', domain: 'Numerical reasoning', type: 'sequence', prompt: 'Which number is the outlier? 8, 16, 24, 31, 40', options: ['8', '16', '31', '40'] },
  { id: 'verbal-02', domain: 'Verbal reasoning', type: 'choice', prompt: 'Which statement is best supported? “The library added 20 study seats. Afternoon attendance rose.”', options: ['The new seats caused all growth', 'Afternoon attendance rose after the change', 'Morning attendance fell', 'Every student prefers the library'] },
  { id: 'spatial-02', domain: 'Visual-spatial reasoning', type: 'choice', prompt: 'Which pair has the same number of shaded cells as the reference?', options: ['A  ■□□■', 'B  ■■□□', 'C  □■■□', 'D  □□■■'], visual: ['■ □', '□ ■'] },
  { id: 'memory-02', domain: 'Working memory', type: 'memory', prompt: 'Keep the letters in mind. Which option reverses their order?', options: ['K — M — R — T', 'T — R — M — K', 'M — K — T — R', 'R — T — K — M'] },
  { id: 'speed-02', domain: 'Processing speed', type: 'speed', prompt: 'Which option contains the exact target pair: ○◆?', options: ['◆○  ◇□', '□◇  ○◆', '○◇  ◆□', '◇◆  □○'] }
]

export const majors: Major[] = [
  { name: 'Computer Science', family: 'Technology & systems', fit: 87, readiness: 72, feasibility: 'Build evidence', confidence: 79, reason: 'Your investigative interests and abstract + numerical profile align with computational problem-solving. Build more evidence through a small application.', tags: ['Investigative', 'Systems', 'Build'], accent: '#315CFF' },
  { name: 'Architecture', family: 'Design & built environment', fit: 82, readiness: 68, feasibility: 'Build evidence', confidence: 73, reason: 'Spatial reasoning and creative interests support this direction. Compare studio work with the mathematics and technical demands.', tags: ['Creative', 'Spatial', 'Design'], accent: '#F56B5D' },
  { name: 'Data Science', family: 'Technology & analysis', fit: 80, readiness: 64, feasibility: 'Needs preparation', confidence: 70, reason: 'Quantitative curiosity is promising; statistics foundations and a guided data project would make the fit more concrete.', tags: ['Analytical', 'Numbers', 'Evidence'], accent: '#1AAE91' },
  { name: 'Industrial Design', family: 'Design & making', fit: 78, readiness: 75, feasibility: 'Ready to explore', confidence: 68, reason: 'Making, visual thinking and user-focused problem solving are a good match. Try a short prototyping challenge.', tags: ['Creative', 'Making', 'People'], accent: '#8B5CF6' },
  { name: 'Psychology', family: 'People & behaviour', fit: 75, readiness: 77, feasibility: 'Ready to explore', confidence: 66, reason: 'Your interest in people and evidence-based questions could translate well. Read one introductory research paper and reflect.', tags: ['People', 'Research', 'Care'], accent: '#E5A43A' }
]

export const alternatives: Major[] = [
  { name: 'Information Systems', family: 'Technology & organisations', fit: 73, readiness: 76, feasibility: 'Ready to explore', confidence: 61, reason: 'A bridge between technology, process and people.', tags: ['Systems', 'Teams'], accent: '#315CFF' },
  { name: 'Environmental Engineering', family: 'Science & impact', fit: 70, readiness: 58, feasibility: 'Needs preparation', confidence: 55, reason: 'Explore if science and practical impact keep your interest.', tags: ['Science', 'Impact'], accent: '#1AAE91' },
  { name: 'Communication Design', family: 'Creative communication', fit: 68, readiness: 80, feasibility: 'Ready to explore', confidence: 54, reason: 'A practical direction for visual storytelling and problem framing.', tags: ['Creative', 'Story'], accent: '#F56B5D' }
]

export const recommendations = [
  { label: 'Try this week', title: 'Build a tiny data story', body: 'Use a public dataset, find one pattern, and explain it in three visuals.', icon: '↗' },
  { label: 'Strengthen', title: 'Quantitative foundations', body: 'Spend one focused session on ratios, functions, or introductory statistics.', icon: '＋' },
  { label: 'Talk to someone', title: 'Interview a CS student', body: 'Ask what a normal week looks like and which parts feel energising or difficult.', icon: '◌' }
]
