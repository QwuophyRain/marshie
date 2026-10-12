// The conversation and Marshie's feelings in one place.
// mood: idle | listening | thinking | talking | hello | love | laugh | wow | celebrate | sad | unsure | sleepy
import { reactive } from 'vue'
import { api } from '../api'
import { settings } from '../settings'
import { brand } from '../brand'
import { canListen, caps, chime, speak, startListening, stopSpeaking, unlockAudio } from './useVoice'

// Feelings she can show while she talks (her mouth moves in all of them).
export const SPEAKING_MOODS = ['talking', 'hello', 'love', 'laugh', 'wow']

export const state = reactive({
  started: false,
  mood: 'idle',
  busy: false,
  listening: false,
  conversation: false, // hands-free: she listens, answers aloud, then listens again, until someone stops her
  messages: [],
  quiz: null,        // { score, total, streak, level, current, waiting }
  teach: null,       // { question } while the "teach me" form is open
  notice: '',        // friendly error line
})

let nextId = 1
let moodToken = 0          // lets a newer mood win over an older timer
let listener = null
let sleepTimer = null
let clearTimer = null

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

function setMood(mood) {
  moodToken += 1
  state.mood = mood
  return moodToken
}

function push(role, text, extra = {}) {
  const msg = { id: nextId++, role, text, ...extra }
  state.messages.push(msg)
  return msg
}

/** Any tap, key or word resets the sleepy and "start fresh" timers. */
export function touch() {
  clearTimeout(sleepTimer)
  clearTimeout(clearTimer)
  if (state.mood === 'sleepy') setMood('idle')
  if (settings.sleepSeconds > 0) {
    sleepTimer = setTimeout(() => {
      if (state.mood === 'idle' && !state.busy && !state.listening) setMood('sleepy')
    }, settings.sleepSeconds * 1000)
  }
  if (settings.autoClearMinutes > 0 && state.started) {
    clearTimer = setTimeout(() => {
      if (!state.busy && !state.listening && !state.teach) resetConversation()
    }, settings.autoClearMinutes * 60 * 1000)
  }
}

/** Marshie talks: face talks while the voice plays, then she relaxes. */
async function say(text, { mood = 'talking', spoken, after = 'idle' } = {}) {
  // celebrate / sad keep their face the whole time she speaks; plain answers use the talking face
  const token = setMood(mood)
  await speak(spoken || text)
  if (token === moodToken) {
    setMood(after)
    touch()                  // she has finished: start counting down to sleep and to "start fresh" from now
  }
}

export function resetConversation() {
  endConversation('')
  stopSpeaking()
  stopListeningNow()
  state.messages = []
  state.quiz = null
  state.teach = null
  state.notice = ''
  state.busy = false
  setMood('idle')
  greet(false)
}

/** The school's introduction. It is shown in the chat, and spoken (with names spelled the way they sound) when she wakes. */
function greet(speakIt) {
  push('bot', brand.greeting, { kind: 'greeting' })
  if (speakIt) return say(brand.greeting, { mood: 'hello', spoken: brand.greetingSpoken || undefined })
  return Promise.resolve()
}

let pokes = 0
/** Tapping Marshie tickles her: she giggles, waves, gasps or blushes. */
export function poke() {
  touch()
  if (state.conversation && SPEAKING_MOODS.includes(state.mood) && !state.busy) {     // tap while she talks = "let me speak"
    stopSpeaking()
    return
  }
  if (state.busy || state.listening || state.teach) return
  if (state.mood !== 'idle') return
  const mood = ['laugh', 'hello', 'wow', 'love'][pokes++ % 4]
  const token = setMood(mood)
  setTimeout(() => { if (token === moodToken) setMood('idle') }, 1600)
}

export function begin() {
  if (state.started) return
  unlockAudio()
  state.started = true
  state.messages = []
  const hello = greet(true)
  touch()
  if (settings.autoTalk && canListen()) hello.then(() => { if (state.started && !state.conversation) startConversation() })
}

// ------------------------------------------------------------------------------------------------ asking
function history() {
  return state.messages
    .filter((m) => m.kind !== 'greeting' && m.text)
    .slice(-8)
    .map((m) => ({ role: m.role === 'user' ? 'user' : 'assistant', content: m.text }))
}

export async function ask(text) {
  const question = text.trim()
  if (!question) return
  touch()
  stopSpeaking()
  state.notice = ''
  push('user', question)
  state.busy = true
  setMood('thinking')
  const t0 = Date.now()
  let reply
  try {
    reply = await api.ask(question, history().slice(0, -1))
  } catch (e) {
    state.busy = false
    state.notice = e.message
    push('bot', e.message, { kind: 'error' })
    setMood('unsure')
    await sleep(1800)
    setMood('idle')
    return
  }
  const wait = 900 - (Date.now() - t0)               // let children see her thinking, even when she is fast
  if (wait > 0) await sleep(wait)

  state.busy = false
  if (reply.quiz) {                                  // "quiz me" typed in the chat starts quiz mode
    await startQuiz(reply.quiz)
    return
  }
  const msg = push('bot', reply.answer, {
    question, entryId: reply.entry_id, source: reply.source, canTeach: reply.can_teach,
    media: reply.media || [], origin: reply.origin || '',
    alternatives: reply.alternatives || [], feedback: null,
    rateable: ['knowledge', 'llm', 'math', 'dataset'].includes(reply.source),
  })
  if (reply.mood === 'unsure') {
    setMood('unsure')
    await sleep(1000)
  }
  await say(reply.answer, { mood: SPEAKING_MOODS.includes(reply.mood) ? reply.mood : 'talking', spoken: reply.spoken })
  return msg
}

// ------------------------------------------------------------------------------------------------ listening
function stopListeningNow() {
  if (listener) listener.stop()
  listener = null
  state.listening = false
}

export async function toggleListening() {
  touch()
  if (state.conversation) return endConversation('Okay, I’ll stop listening.')
  if (state.listening) {
    stopListeningNow()
    return
  }
  state.notice = ''
  stopSpeaking()
  setMood('listening')
  state.listening = true
  listener = startListening()
  let heard = ''
  try {
    heard = await listener.promise
  } catch (e) {
    state.listening = false
    listener = null
    state.notice = e.message
    push('bot', e.message, { kind: 'error' })
    setMood('unsure')
    await sleep(1500)
    setMood('idle')
    return
  }
  state.listening = false
  listener = null
  if (!heard) {
    state.notice = 'I didn’t hear anything. Tap the microphone and try again.'
    setMood('unsure')
    await say('I didn’t hear anything. Tap the microphone and try again, or type your question.', { mood: 'unsure', after: 'idle' })
    return
  }
  return send(heard)
}

/** Typed or spoken text goes through here, so quiz answers are routed correctly. */
export function send(text) {
  if (state.quiz?.current && !state.quiz.waiting) return answerQuiz(text)
  return ask(text)
}

// ------------------------------------------------------------------------------------------------ talking back and forth
// Hands-free conversation: listen, answer out loud, listen again. It stops when someone says "stop" or "goodbye",
// taps the button, or when nobody has spoken for a while. She never listens while she is talking, so she cannot hear herself.
const STOP_WORDS = /^(stop|stop listening|stop talking|be quiet|quiet|enough|cancel|pause|end|quit|exit)$/
const BYE_WORDS = /^(bye|bye bye|goodbye|good bye|see you|see you later|see you soon|that is all|that is it|i am done|we are done|good night|thats all|i have to go)$/
const MAX_QUIET_TURNS = 4

let convoRun = 0

function plain(text) {
  return text.toLowerCase().replace(/['’]/g, '').replace(/[^a-z ]+/g, ' ').replace(/\s+/g, ' ').trim()
}

export function endConversation(line = '') {
  if (!state.conversation) return
  convoRun += 1
  state.conversation = false
  stopListeningNow()
  stopSpeaking()
  if (line) {
    push('bot', line, { kind: 'info' })
    return say(line, { mood: 'talking' })
  }
  setMood('idle')
  touch()
}

export function toggleConversation() {
  touch()
  return state.conversation ? endConversation('Okay, I’ll stop listening. Tap Talk with me whenever you want to chat again.') : startConversation()
}

export async function startConversation() {
  if (state.conversation) return
  if (!canListen()) {
    state.notice = 'This browser can’t listen yet, so please type your question.'
    return
  }
  unlockAudio()
  stopSpeaking()
  state.notice = ''
  state.conversation = true
  const run = ++convoRun
  touch()
  await converse(run)
}

async function converse(run) {
  const alive = () => state.conversation && run === convoRun
  let quiet = 0
  while (alive()) {
    // wait while she is busy, or while someone is typing a lesson for her in the teach box
    while (alive() && (state.busy || state.teach)) await sleep(300)
    if (!alive()) break
    await sleep(450)                                   // a breath after she stops talking, so the room is quiet
    if (!alive()) break
    await chime()
    if (!alive()) break

    stopSpeaking()
    setMood('listening')
    state.listening = true
    listener = startListening()
    let heard = ''
    try {
      heard = await listener.promise
    } catch (e) {
      state.listening = false
      listener = null
      if (!alive()) break
      state.conversation = false
      convoRun += 1
      state.notice = e.message
      push('bot', e.message, { kind: 'error' })
      setMood('unsure')
      await sleep(1500)
      setMood('idle')
      return
    }
    state.listening = false
    listener = null
    if (!alive()) break

    if (!heard) {
      quiet += 1
      setMood('idle')
      if (quiet >= MAX_QUIET_TURNS) {
        await endConversation('I’ll take a little rest now. Tap Talk with me when you want to chat again.')
        return
      }
      if (quiet === 2) {
        const line = 'Are you still there? Just talk to me, or tap Stop.'
        push('bot', line, { kind: 'info' })
        await say(line, { mood: 'talking' })
      }
      continue
    }
    quiet = 0
    touch()

    const said = plain(heard)
    if (BYE_WORDS.test(said)) {
      push('user', heard)
      await endConversation('Goodbye! It was lovely talking with you. Come and chat again soon.')
      return
    }
    if (STOP_WORDS.test(said)) {
      if (state.quiz) { push('user', heard); await stopQuiz(); continue }
      push('user', heard)
      await endConversation('Okay, I’ll stop listening. Tap Talk with me whenever you want to chat again.')
      return
    }
    await send(heard)                                  // resolves when she has finished speaking her answer
  }
  if (!state.conversation) setMood('idle')
}

// ------------------------------------------------------------------------------------------------ feedback & teaching
export async function rate(msg, good) {
  if (msg.feedback) return
  touch()
  msg.feedback = good ? 'good' : 'bad'
  stopSpeaking()
  let res
  try {
    res = await api.feedback({ question: msg.question, entry_id: msg.entryId, good })
  } catch (e) {
    msg.feedback = null
    state.notice = e.message
    return
  }
  if (good) {
    await say(res.message, { mood: 'celebrate' })
  } else {
    state.teach = { question: msg.question }
    await say(res.message, { mood: 'sad' })
  }
}

export function openTeach(question = '') {
  touch()
  state.teach = { question }
}
export function closeTeach() {
  state.teach = null
}

export async function submitTeach({ question, answer, taught_by }) {
  touch()
  let res
  try {
    res = await api.teach({ question, answer, taught_by })
  } catch (e) {
    return { ok: false, message: e.message }
  }
  if (res.ok) {
    state.teach = null
    push('bot', res.message, { kind: 'thanks' })
    await say(res.message, { mood: 'celebrate' })
  }
  return res
}

// ------------------------------------------------------------------------------------------------ quiz
function startQuiz(first) {
  state.quiz = { score: 0, total: 0, streak: 0, level: 1, current: null, waiting: false }
  return presentQuestion(first, true)
}

async function presentQuestion(q, isFirst = false) {
  state.quiz.current = q
  state.quiz.waiting = false
  const text = isFirst ? `Let's play! ${q.question}` : q.question
  push('bot', text, { kind: 'quiz' })
  await say(q.question)
}

async function nextQuestion() {
  if (!state.quiz) return
  try {
    const q = await api.quiz('', state.quiz.level)
    if (!state.quiz) return
    await presentQuestion(q)
  } catch (e) {
    stopQuiz()
  }
}

export async function answerQuiz(text) {
  const quiz = state.quiz
  if (!quiz?.current) return ask(text)
  touch()
  stopSpeaking()
  push('user', text)
  quiz.waiting = true
  setMood('thinking')
  let result
  try {
    result = await api.quizCheck({
      kind: quiz.current.kind, response: text, question: quiz.current.question,
      token: quiz.current.token || '', entry_id: quiz.current.entry_id || '',
    })
  } catch (e) {
    quiz.waiting = false
    state.notice = e.message
    setMood('idle')
    return
  }
  quiz.total += 1
  let line
  if (result.correct) {
    quiz.score += 1
    quiz.streak += 1
    if (quiz.streak % 3 === 0 && quiz.level < 3) quiz.level += 1
    line = ['Yes! That’s right!', 'Brilliant! You got it!', 'Hooray, correct!'][quiz.total % 3]
  } else {
    quiz.streak = 0
    let reveal = result.answer && result.answer !== 'Not quite' ? result.answer : ''
    if (!reveal && quiz.current.kind === 'math') {
      try { reveal = (await api.ask(quiz.current.question)).answer } catch { /* skip */ }
    }
    line = `Not quite. ${reveal ? 'The answer is: ' + reveal : ''}`.trim()
  }
  push('bot', line, { kind: 'quiz-result', correct: result.correct })
  await say(line, { mood: result.correct ? 'celebrate' : 'sad' })
  if (state.quiz === quiz) {
    await sleep(500)
    if (state.quiz === quiz) await nextQuestion()
  }
}

export async function stopQuiz() {
  const quiz = state.quiz
  if (!quiz) return
  state.quiz = null
  stopSpeaking()
  const good = quiz.total > 0 && quiz.score / quiz.total >= 0.5
  const line = quiz.total
    ? `Quiz finished! You got ${quiz.score} out of ${quiz.total}. ${good ? 'Well done!' : 'Good try! Let’s practise again soon.'}`
    : 'Okay, we can play another time!'
  push('bot', line, { kind: 'quiz-end' })
  await say(line, { mood: good ? 'celebrate' : 'talking' })
}

export { caps }
