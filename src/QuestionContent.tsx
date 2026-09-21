import type { ReactNode } from 'react'
import type { Question } from './types'

/** One copy of the instructions and passage, regardless of stimulus type. */
export function QuestionContent({ question, children }: { question: Question; children?: ReactNode }) {
  return <>
    <div className="question-copy">
      <h1>{question.prompt}</h1>
      {question.helper && <p>{question.helper}</p>}
    </div>
    {question.imageUrl
      ? <div className="assessment-image external-visual-image"><img src={question.imageUrl} alt="Visual reasoning stimulus with four answer panels" /></div>
      : children}
  </>
}
