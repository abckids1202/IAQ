import { useEffect, useState } from 'react'

export function MemorySequenceInput({ itemId, length, onChoose, disabled }: { itemId: string; length: number; onChoose: (value: string) => void; disabled: boolean }) {
  const [values, setValues] = useState<string[]>(() => Array(length).fill(''))
  useEffect(() => { setValues(Array(length).fill('')) }, [itemId, length])
  return <fieldset disabled={disabled}><legend>Enter one remembered number in each position</legend><div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>{values.map((value, index) => <label key={index}>Position {index + 1}<input style={{ width: 72 }} type="text" inputMode="text" autoComplete="off" value={value} maxLength={6} aria-label={`Recalled number ${index + 1}`} onChange={(event) => {
    const raw = event.target.value
    if (!/^-?\d{0,5}$/.test(raw)) return
    const next = [...values]; next[index] = raw; setValues(next)
    onChoose(next.every((part) => /^-?\d+$/.test(part)) ? JSON.stringify(next.map(Number)) : '')
  }} /></label>)}</div><small>{values.filter((value) => /^-?\d+$/.test(value)).length} / {length} numbers entered</small></fieldset>
}
