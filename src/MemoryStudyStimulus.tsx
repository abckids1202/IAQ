import type { Question } from './types'

export function MemoryStudyStimulus({ visual }: { visual: Question['visual'] }) {
  const data = visual && !Array.isArray(visual) ? visual : null
  const sequence = Array.isArray(visual) ? visual : Array.isArray(data?.sequence) ? data.sequence : null
  if (sequence) return <div className="memory-stimulus" aria-label="Sequence to study">{sequence.map((value, index) => <span key={index}>{String(value)}</span>)}</div>
  const size = Number(data?.grid_size)
  if (Number.isInteger(size) && size > 0 && size <= 8 && Array.isArray(data?.filled_cells)) {
    const filled = data.filled_cells as number[]
    return <div role="img" aria-label={`Study a ${size} by ${size} grid. Filled positions: ${filled.map((i) => i + 1).join(', ')}.`} style={{ display: 'grid', gridTemplateColumns: `repeat(${size}, 36px)`, gap: 4 }}>{Array.from({ length: size * size }, (_, index) => <span key={index} style={{ width: 36, height: 36, border: '1px solid #D7D2C7', background: filled.includes(index) ? '#0B1220' : '#fff' }} />)}</div>
  }
  return <p role="alert">Study stimulus unavailable. Please report this item.</p>
}
