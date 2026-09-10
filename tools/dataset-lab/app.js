const state = {
  summary: null,
  item: null,
  selected: null,
  checked: false,
  seen: new Set(),
  attempted: 0,
  correct: 0,
  memory: {
    stage: 'study',
    config: null,
    response: [],
  },
}

const $ = (id) => document.getElementById(id)

function formatValue(value) {
  if (typeof value === 'string') return value
  if (value === null || value === undefined) return '—'
  return JSON.stringify(value)
}

function isBinaryMatrix(value) {
  return Array.isArray(value) && value.length > 0 && value.every((row) => Array.isArray(row) && row.length > 0 && row.every((cell) => cell === 0 || cell === 1))
}

function renderValue(value, parent, className = '') {
  if (isBinaryMatrix(value)) {
    const grid = document.createElement('span')
    grid.className = `mini-matrix ${className}`
    grid.style.gridTemplateColumns = `repeat(${value[0]?.length || 1}, 9px)`
    value.forEach((row) => row.forEach((cell) => {
      const square = document.createElement('i')
      square.className = cell ? 'filled' : 'empty'
      square.setAttribute('aria-hidden', 'true')
      grid.appendChild(square)
    }))
    parent.appendChild(grid)
    const accessible = document.createElement('span')
    accessible.className = 'sr-only'
    accessible.textContent = `Grid: ${formatValue(value)}`
    parent.appendChild(accessible)
    return
  }
  const text = document.createElement('span')
  text.className = className
  text.textContent = formatValue(value)
  parent.appendChild(text)
}

function setText(id, value) {
  $(id).textContent = value
}

function validation(item, key) {
  return item.validation?.[key] || []
}

function allDatasetStats() {
  const values = Object.values(state.summary?.datasets || {})
  return values.reduce((total, value) => ({
    count: total.count + value.count,
    with_images: total.with_images + value.with_images,
    reviewed: total.reviewed + value.reviewed,
    content_issues: total.content_issues + (value.content_issue_total || 0),
    review_warnings: total.review_warnings + (value.review_warning_total || 0),
    readiness_warnings: total.readiness_warnings + (value.readiness_warning_total || 0),
  }), { count: 0, with_images: 0, reviewed: 0, content_issues: 0, review_warnings: 0, readiness_warnings: 0 })
}

function updateSummary() {
  const stats = allDatasetStats()
  setText('stat-total', stats.count.toLocaleString())
  setText('stat-images', stats.with_images.toLocaleString())
  setText('stat-reviewed', stats.reviewed.toLocaleString())
  setText('stat-content-issues', stats.content_issues.toLocaleString())
  setText('stat-readiness', stats.readiness_warnings.toLocaleString())
  const dataset = $('dataset-select').value
  const selected = dataset === 'all' ? stats : state.summary.datasets[dataset]
  if (!selected) return
  const contentIssues = dataset === 'all' ? stats.content_issues : (selected.content_issue_total || 0)
  const reviewWarnings = dataset === 'all' ? stats.review_warnings : (selected.review_warning_total || 0)
  const readinessWarnings = dataset === 'all' ? stats.readiness_warnings : (selected.readiness_warning_total || 0)
  $('dataset-details').innerHTML = ''
  const lines = [
    `${selected.count.toLocaleString()} records loaded`,
    `${selected.with_images.toLocaleString()} image assets resolved`,
    `${selected.reviewed.toLocaleString()} marked human reviewed`,
    `${contentIssues.toLocaleString()} structural/content issues`,
    `${reviewWarnings.toLocaleString()} review warnings · ${readinessWarnings.toLocaleString()} readiness warnings`,
  ]
  if (dataset === 'all') lines.push('All mode: equal probability by domain, not raw source volume')
  lines.forEach((line) => {
    const p = document.createElement('p')
    p.textContent = line
    $('dataset-details').appendChild(p)
  })
}

async function loadSummary() {
  const response = await fetch('/api/summary')
  state.summary = await response.json()
  updateSummary()
}

function renderStatus(item) {
  const strip = $('status-strip')
  strip.innerHTML = ''
  const contentIssues = validation(item, 'content_issues')
  const reviewWarnings = validation(item, 'review_warnings')
  const readinessWarnings = validation(item, 'readiness_warnings')
  const statuses = [
    [item.review_status || 'unknown', item.review_status === 'reviewed' ? 'good' : 'warn'],
    [contentIssues.length ? `${contentIssues.length} content issue${contentIssues.length === 1 ? '' : 's'}` : 'No structural issues', contentIssues.length ? 'issue' : 'good'],
    [reviewWarnings.length ? `${reviewWarnings.length} review warning${reviewWarnings.length === 1 ? '' : 's'}` : 'Review status clear', reviewWarnings.length ? 'warn' : 'good'],
    [readinessWarnings.length ? `${readinessWarnings.length} readiness warning${readinessWarnings.length === 1 ? '' : 's'}` : 'Readiness clear', readinessWarnings.length ? 'warn' : 'good'],
  ]
  statuses.forEach(([label, tone]) => {
    const span = document.createElement('span')
    span.className = `status-chip ${tone}`
    span.textContent = label
    strip.appendChild(span)
  })
}

function renderTechnical(item) {
  const list = $('technical-list')
  list.innerHTML = ''
  const entries = [
    ['Record ID', item.id],
    ['Dataset', item.dataset_label],
    ['Source file', item.source_file],
    ['Family', item.family],
    ['Origin', item.origin],
    ['Presentation', item.presentation_mode],
    ['Response type', item.response_type],
    ['Stored options', item.option_count],
    ['Image', item.image_url ? 'Resolved' : 'Not provided'],
    ['Content checks', validation(item, 'content_issues').join(', ') || 'None'],
    ['Review warnings', validation(item, 'review_warnings').join(', ') || 'None'],
    ['Readiness warnings', validation(item, 'readiness_warnings').join(', ') || 'None'],
  ]
  entries.forEach(([key, value]) => {
    const dt = document.createElement('dt')
    dt.textContent = key
    const dd = document.createElement('dd')
    dd.textContent = value === 0 ? '0' : value || '—'
    list.append(dt, dd)
  })
}

function clearFeedback() {
  $('feedback').className = 'feedback hidden'
  $('feedback').innerHTML = ''
}

function renderOptionButton(index, contentRenderer) {
  const button = document.createElement('button')
  button.type = 'button'
  button.className = 'option-button'
  button.dataset.choiceIndex = String(index)
  button.setAttribute('role', 'radio')
  button.setAttribute('aria-checked', 'false')
  const letter = document.createElement('b')
  const choiceLabel = String.fromCharCode(65 + index)
  letter.textContent = choiceLabel
  const content = document.createElement('span')
  contentRenderer(content)
  button.append(letter, content)
  button.addEventListener('click', () => selectOption(index))
  return button
}

function renderVisualLabels(item) {
  const options = $('options')
  options.className = 'options visual-label-options'
  options.innerHTML = ''
  for (let index = 0; index < 4; index += 1) {
    const button = renderOptionButton(index, (content) => {
      content.className = 'label-only-option'
      content.textContent = `Choice ${String.fromCharCode(65 + index)}`
    })
    button.setAttribute('aria-label', `Choice ${String.fromCharCode(65 + index)} shown in the image`)
    if (item.option_count !== 4) button.disabled = true
    options.appendChild(button)
  }
  if (item.option_count !== 4) {
    const blocked = document.createElement('p')
    blocked.className = 'blocked-note visual-choice-warning'
    blocked.textContent = 'These four controls are shown for inspection, but checking is blocked because the record does not contain exactly four stored answer choices.'
    options.appendChild(blocked)
  }
}

function renderTextOptions(item) {
  const options = $('options')
  options.className = 'options'
  options.innerHTML = ''
  item.options.forEach((option, index) => {
    options.appendChild(renderOptionButton(index, (content) => renderValue(option, content)))
  })
}

function renderMemoryStudy(item) {
  const memoryStage = $('memory-stage')
  const recallButton = $('memory-recall-button')
  const recallPanel = $('memory-recall-panel')
  memoryStage.classList.remove('hidden')
  recallPanel.className = 'memory-recall-panel hidden'
  recallPanel.innerHTML = ''
  $('options').classList.add('hidden')
  setText('memory-phase-label', 'Study phase')
  setText('memory-protocol-note', item.protocol?.timing_status || 'Manual preview; timing is not standardized.')
  setText('memory-instructions', 'Study the stimulus. When you are ready, choose Begin recall. The stimulus will not return.')
  recallButton.classList.remove('hidden')
  recallButton.disabled = !item.can_check || !item.image_url
  recallButton.textContent = 'Begin recall'
  $('check-button').textContent = 'Check recall ✓'
}

function updateMemoryCheckState() {
  const config = state.memory.config
  if (!config) return
  let complete = false
  if (config.response_type === 'ordered_sequence') {
    const input = $('memory-sequence-input')
    const digits = (input?.value || '').replace(/\D/g, '')
    state.memory.response = digits.split('').map(Number)
    setText('memory-response-count', `${state.memory.response.length} / ${config.input_length} digits entered`)
    complete = state.memory.response.length === config.input_length
  } else {
    complete = state.memory.response.length > 0
    setText('memory-response-count', `${state.memory.response.length} / ${config.input_length} cells selected`)
  }
  $('check-button').disabled = !complete || state.checked
}

function renderMemoryRecall(config) {
  const recallPanel = $('memory-recall-panel')
  recallPanel.className = 'memory-recall-panel'
  recallPanel.innerHTML = ''
  state.memory.config = config
  state.memory.response = []
  $('options').classList.add('hidden')
  setText('memory-phase-label', 'Recall phase')
  setText('memory-protocol-note', 'The stimulus is hidden and cannot be replayed.')
  setText('memory-instructions', config.response_type === 'ordered_sequence'
    ? `Enter the ${config.input_length} digits in the required order.`
    : 'Select every cell that was filled in the study grid.')

  if (config.response_type === 'ordered_sequence') {
    const label = document.createElement('label')
    label.className = 'field-label'
    label.htmlFor = 'memory-sequence-input'
    label.textContent = 'Your recalled sequence'
    const input = document.createElement('input')
    input.id = 'memory-sequence-input'
    input.className = 'memory-sequence-input'
    input.type = 'text'
    input.inputMode = 'numeric'
    input.autoComplete = 'off'
    input.maxLength = config.input_length
    input.placeholder = 'Enter digits'
    input.setAttribute('aria-describedby', 'memory-response-count')
    input.addEventListener('input', () => {
      input.value = input.value.replace(/\D/g, '').slice(0, config.input_length)
      updateMemoryCheckState()
    })
    recallPanel.append(label, input)
  } else {
    const grid = document.createElement('div')
    grid.className = 'memory-recall-grid'
    grid.style.setProperty('--memory-grid-size', config.grid_size)
    grid.setAttribute('role', 'group')
    grid.setAttribute('aria-label', `Empty ${config.grid_size} by ${config.grid_size} recall grid`)
    for (let index = 0; index < config.grid_size * config.grid_size; index += 1) {
      const cell = document.createElement('button')
      cell.type = 'button'
      cell.className = 'memory-cell'
      cell.setAttribute('aria-label', `Cell ${index + 1}`)
      cell.setAttribute('aria-pressed', 'false')
      cell.addEventListener('click', () => {
        if (state.checked) return
        const selected = state.memory.response.includes(index)
        state.memory.response = selected
          ? state.memory.response.filter((value) => value !== index)
          : [...state.memory.response, index]
        cell.classList.toggle('selected', !selected)
        cell.setAttribute('aria-pressed', selected ? 'false' : 'true')
        updateMemoryCheckState()
      })
      grid.appendChild(cell)
    }
    recallPanel.appendChild(grid)
  }
  const count = document.createElement('p')
  count.id = 'memory-response-count'
  count.className = 'memory-response-count'
  count.textContent = config.response_type === 'ordered_sequence'
    ? `0 / ${config.input_length} digits entered`
    : `0 / ${config.input_length} cells selected`
  recallPanel.appendChild(count)
  $('memory-recall-button').classList.add('hidden')
  $('check-button').disabled = true
}

async function beginMemoryRecall() {
  if (!state.item || state.item.presentation_mode === 'visual_labels') return
  const response = await fetch(`/api/memory/recall?id=${encodeURIComponent(state.item.id)}`)
  const payload = await response.json()
  if (!response.ok) {
    showError(payload.error || 'This memory protocol cannot start.')
    return
  }
  state.memory.stage = 'recall'
  const imageWrap = $('question-image-wrap')
  imageWrap.classList.add('hidden')
  $('question-image').removeAttribute('src')
  renderMemoryRecall(payload.recall)
  $('answer-state').textContent = 'Recall is ready'
}

function renderItem(item) {
  state.item = item
  state.selected = null
  state.checked = false
  state.memory = { stage: 'study', config: null, response: [] }
  $('empty-state').classList.add('hidden')
  $('question-state').classList.remove('hidden')
  setText('question-dataset', `${item.dataset_label} · ${item.presentation_mode}`)
  setText('question-title', item.prompt || 'Untitled question')
  setText('question-index', item.id)
  setText('answer-instruction', item.presentation_mode.startsWith('memory_') ? 'Recall response' : 'Choose one answer')
  $('answer-state').textContent = 'Not answered'
  renderStatus(item)
  renderTechnical(item)

  const context = $('question-context')
  context.innerHTML = ''
  if (item.context) {
    const label = document.createElement('strong')
    label.textContent = 'Passage / context'
    const body = document.createElement('p')
    body.textContent = item.context
    context.append(label, body)
  }
  if (item.alternate_prompt && item.alternate_prompt !== item.prompt) {
    const alternate = document.createElement('small')
    alternate.textContent = `Alternate language record: ${item.alternate_prompt}`
    context.appendChild(alternate)
  }

  const imageWrap = $('question-image-wrap')
  const image = $('question-image')
  imageWrap.classList.toggle('hidden', !item.image_url)
  if (item.image_url) {
    image.src = item.image_url
    image.alt = `${item.dataset_label} stimulus for ${item.id}`
  } else {
    image.removeAttribute('src')
  }

  const stimulus = $('stimulus-preview')
  stimulus.innerHTML = ''
  stimulus.classList.add('hidden')
  if (item.stimulus && !item.image_url && item.presentation_mode !== 'memory_incomplete') {
    stimulus.classList.remove('hidden')
    const label = document.createElement('strong')
    label.textContent = 'Structured stimulus'
    stimulus.appendChild(label)
    const pre = document.createElement('pre')
    pre.textContent = JSON.stringify(item.stimulus, null, 2)
    stimulus.appendChild(pre)
  }

  $('memory-stage').classList.add('hidden')
  $('memory-recall-button').classList.remove('hidden')
  $('options').classList.remove('hidden')
  $('options').innerHTML = ''
  $('check-button').textContent = 'Check answer ✓'
  if (item.presentation_mode === 'memory_sequence' || item.presentation_mode === 'memory_grid' || item.presentation_mode === 'memory_incomplete') {
    renderMemoryStudy(item)
  } else if (item.presentation_mode === 'visual_labels' || item.kind === 'visual') {
    renderVisualLabels(item)
  } else {
    renderTextOptions(item)
  }
  $('check-button').disabled = !item.can_check || item.presentation_mode.startsWith('memory_')
  if (!item.can_check) {
    const blocked = document.createElement('p')
    blocked.className = 'blocked-note'
    blocked.textContent = 'Checking is blocked until the structural/content issues above are resolved.'
    $('feedback').className = 'feedback blocked-feedback'
    $('feedback').innerHTML = ''
    $('feedback').appendChild(blocked)
  } else {
    clearFeedback()
  }
}

function selectOption(index) {
  if (state.checked || !state.item?.can_check) return
  state.selected = index
  document.querySelectorAll('.option-button').forEach((button, buttonIndex) => {
    const selected = buttonIndex === index
    button.classList.toggle('selected', selected)
    button.setAttribute('aria-checked', selected ? 'true' : 'false')
  })
  $('answer-state').textContent = `Answer ${String.fromCharCode(65 + index)} selected`
  $('check-button').disabled = false
}

function appendResultLine(parent, label, value) {
  const row = document.createElement('div')
  const key = document.createElement('span')
  key.className = 'result-label'
  key.textContent = label
  const content = document.createElement('span')
  renderValue(value, content, 'result-value')
  row.append(key, content)
  parent.appendChild(row)
}

function renderFeedback(result) {
  state.checked = true
  state.attempted += 1
  if (result.correct) state.correct += 1
  $('answer-state').textContent = result.correct ? 'Correct' : 'Review the answer below'
  const feedback = $('feedback')
  feedback.className = `feedback ${result.correct ? 'correct-feedback' : 'incorrect-feedback'}`
  feedback.innerHTML = ''
  const heading = document.createElement('h3')
  heading.textContent = result.correct ? 'Correct answer' : 'Not this time'
  feedback.appendChild(heading)
  appendResultLine(feedback, 'Verified answer', result.answer)
  if (result.rule) appendResultLine(feedback, 'Rule / explanation', result.rule)
  else if (result.explanation) appendResultLine(feedback, 'Explanation', result.explanation)
  else appendResultLine(feedback, 'Explanation', 'No rule or explanation was supplied in this record. Human review needed.')
  if (result.issues?.length) appendResultLine(feedback, 'Review flags', result.issues.join(', '))
  const score = document.createElement('small')
  score.textContent = `Lab run: ${state.correct} correct out of ${state.attempted} checked. This is not an IQ score.`
  feedback.appendChild(score)
}

async function checkAnswer() {
  if (!state.item || state.checked) return
  let payload
  if (state.item.presentation_mode === 'memory_sequence' || state.item.presentation_mode === 'memory_grid') {
    if (state.memory.stage !== 'recall') return
    if (state.memory.config.response_type === 'ordered_sequence') {
      const input = $('memory-sequence-input')
      state.memory.response = (input?.value || '').replace(/\D/g, '').split('').map(Number)
    }
    payload = { id: state.item.id, response_type: state.memory.config.response_type, response: state.memory.response }
  } else {
    if (state.selected === null) return
    payload = { id: state.item.id, answer_index: state.selected }
  }
  $('check-button').disabled = true
  const response = await fetch('/api/check', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const result = await response.json()
  if (!response.ok) {
    showError(result.error || 'Could not check this item.')
    $('check-button').disabled = false
    return
  }
  if (state.item.presentation_mode === 'memory_grid') {
    const correctCells = new Set(result.answer || [])
    document.querySelectorAll('.memory-cell').forEach((cell, index) => {
      cell.disabled = true
      cell.classList.toggle('correct', correctCells.has(index))
      cell.classList.toggle('missed', correctCells.has(index) && !state.memory.response.includes(index))
    })
  }
  if (state.item.presentation_mode === 'memory_sequence') $('memory-sequence-input').disabled = true
  document.querySelectorAll('.option-button').forEach((button, index) => {
    button.disabled = true
    button.classList.toggle('correct', index === result.correct_index)
    button.classList.toggle('incorrect', index === state.selected && !result.correct)
  })
  renderFeedback(result)
}

async function loadNext() {
  const dataset = $('dataset-select').value
  const locale = $('locale-select').value
  const exclude = [...state.seen].join(',')
  $('next-button').disabled = true
  $('next-inline-button').disabled = true
  try {
    const response = await fetch(`/api/item?dataset=${encodeURIComponent(dataset)}&locale=${encodeURIComponent(locale)}&exclude=${encodeURIComponent(exclude)}`)
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.error || 'No question could be loaded.')
    state.seen.add(payload.item.id)
    renderItem(payload.item)
  } catch (error) {
    showError(error.message)
  } finally {
    $('next-button').disabled = false
    $('next-inline-button').disabled = false
  }
}

function showError(message) {
  const empty = $('empty-state')
  empty.classList.remove('hidden')
  empty.innerHTML = `<div class="empty-number">!</div><p class="eyebrow">Could not load</p><h2></h2><p></p>`
  empty.querySelector('h2').textContent = message
  empty.querySelector('p:last-child').textContent = 'Check that the local dataset folders are present, then try again.'
  $('question-state').classList.add('hidden')
}

function resetRun() {
  state.seen.clear()
  state.attempted = 0
  state.correct = 0
  $('empty-state').classList.remove('hidden')
  $('question-state').classList.add('hidden')
  $('empty-state').innerHTML = '<div class="empty-number">◎</div><p class="eyebrow">Run reset</p><h2>Load a fresh question.</h2><p>Seen items have been cleared for this inspection run.</p>'
}

$('dataset-select').addEventListener('change', updateSummary)
$('locale-select').addEventListener('change', () => { if (state.item) loadNext() })
$('next-button').addEventListener('click', loadNext)
$('next-inline-button').addEventListener('click', loadNext)
$('reset-button').addEventListener('click', resetRun)
$('check-button').addEventListener('click', checkAnswer)
$('memory-recall-button').addEventListener('click', beginMemoryRecall)

loadSummary().catch((error) => showError(error.message))
