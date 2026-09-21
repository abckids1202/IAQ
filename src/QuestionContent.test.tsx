import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { QuestionContent } from './QuestionContent'
import type { Question } from './types'

const verbal: Question = {
  id: 'verbal-test', domain: 'Verbal reasoning', type: 'choice',
  prompt: 'Which conclusion follows?', helper: 'Every visitor signed the register.',
  options: ['First', 'Second', 'Third', 'Fourth'],
}

describe('Assessment question content', () => {
  it('renders the verbal question and passage exactly once without an image', () => {
    const html = renderToStaticMarkup(<QuestionContent question={verbal} />)
    expect(html.match(/<h1>/g)).toHaveLength(1)
    expect(html.split(verbal.prompt)).toHaveLength(2)
    expect(html.split(verbal.helper!)).toHaveLength(2)
    expect(html).not.toContain('<img')
  })

  it('renders a single full visual image, not the fallback or a CSS marker', () => {
    const question = { ...verbal, domain: 'Abstract reasoning' as const, helper: undefined, imageUrl: '/assessment-stimuli/matrix.svg' }
    const html = renderToStaticMarkup(<QuestionContent question={question}><div>Fallback visual</div></QuestionContent>)
    expect(html.match(/<img /g)).toHaveLength(1)
    expect(html.match(/<h1>/g)).toHaveLength(1)
    expect(html).toContain('src="/assessment-stimuli/matrix.svg"')
    expect(html).not.toContain('Fallback visual')
  })

  it('keeps the deterministic fallback without duplicating its instructions', () => {
    const html = renderToStaticMarkup(<QuestionContent question={verbal}><svg aria-label="Legacy stimulus" /></QuestionContent>)
    expect(html.match(/<svg /g)).toHaveLength(1)
    expect(html.match(/<h1>/g)).toHaveLength(1)
  })
})
