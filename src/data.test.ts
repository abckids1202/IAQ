import { describe, expect, it } from 'vitest'
import { domains, questions } from './data'

describe('IAQ baseline content', () => {
  it('covers every cognitive domain with a student-facing item', () => {
    const covered = new Set(questions.map((question) => question.domain))
    expect(domains.every((domain) => covered.has(domain))).toBe(true)
  })

  it('keeps the browser question contract free of answer keys', () => {
    expect(questions.every((question) => !Object.prototype.hasOwnProperty.call(question, 'answer'))).toBe(true)
  })
})
