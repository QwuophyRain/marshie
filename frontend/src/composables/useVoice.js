// Marshie's voice: she talks (server voice on the Pi, else the browser's) and listens (server mic, else the browser's).
import { reactive, ref } from 'vue'
import { api } from '../api'
import { settings } from '../settings'

export const caps = reactive({
  loaded: false,
  tts_server: false,
  stt_server: false,
  llm: false,
  on_vercel: false,
  persistent: true,
  secure: typeof window !== 'undefined' ? window.isSecureContext : true,
  recognition: typeof window !== 'undefined' && !!(window.SpeechRecognition || window.webkitSpeechRecognition),
  synth: typeof window !== 'undefined' && 'speechSynthesis' in window,
})

export async function loadCaps(health) {
  try {
    const h = health || await api.health()
    Object.assign(caps, h.capabilities, { on_vercel: h.on_vercel, persistent: h.persistent, loaded: true })
  } catch {
    caps.loaded = true
  }
}

export const mouth = ref(null)          // live loudness 0..1 while Marshie speaks, else null
export const listenLevel = ref(0)       // live loudness while she listens
export const liveText = ref('')         // the words she is hearing right now (browser listening only), shown as the child speaks

let audioCtx = null
function ctx() {
  if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)()
  if (audioCtx.state === 'suspended') audioCtx.resume().catch(() => {})
  return audioCtx
}
/** Call from a click/tap so browsers allow sound later. */
export function unlockAudio() {
  try { ctx() } catch { /* no audio */ }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

/** A soft two-note "bloop" so a child knows it is their turn to speak (like a phone assistant). */
export async function chime() {
  if (!settings.chime || !settings.voiceOn) return
  try {
    const c = ctx()
    const t = c.currentTime
    const gain = c.createGain()
    gain.connect(c.destination)
    gain.gain.setValueAtTime(0.0001, t)
    gain.gain.exponentialRampToValueAtTime(0.09, t + 0.02)
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.26)
    for (const [i, f] of [660, 990].entries()) {
      const o = c.createOscillator()
      o.type = 'sine'
      o.frequency.value = f
      o.connect(gain)
      o.start(t + i * 0.09)
      o.stop(t + 0.28)
    }
    await sleep(320)                       // let it finish, so the microphone does not hear it
  } catch { /* no audio */ }
}

// ----------------------------------------------------------------------------------------- talking
let stopCurrent = null
let speakSeq = 0            // bumps whenever speech is interrupted, so a stale "keep the face talking" pause gives up
export function stopSpeaking() {
  speakSeq += 1
  if (stopCurrent) stopCurrent()
  stopCurrent = null
  if (caps.synth) window.speechSynthesis.cancel()
}

function sentences(text) {
  const parts = (text.match(/[^.!?]+[.!?]*\s*/g) || [text]).map((s) => s.trim()).filter(Boolean)
  const out = []
  for (const p of parts) {
    if (out.length && out[out.length - 1].length < 40) out[out.length - 1] += ' ' + p
    else out.push(p)
  }
  return out
}

const FEMALE = /female|\+f\d|zira|samantha|karen|moira|tessa|fiona|victoria|jenny|aria|hazel|susan|ava|allison|ellen|serena|catherine|libby|sonia|natasha|google uk english female/i

// Voices that sound like a phone assistant. Apple's "Siri", "Premium" and "Enhanced" voices and Microsoft's "Natural"
// voices are the most lifelike; the plain built-in ones come next. Novelty voices (Zarvox, Bells...) are never chosen.
const QUALITY = [[/siri/i, 60], [/premium/i, 40], [/natural|neural|online/i, 36], [/enhanced/i, 30]]
const PREFERRED = [[/\bava\b/i, 14], [/samantha/i, 13], [/\baria\b/i, 13], [/jenny/i, 12], [/allison/i, 11], [/\bzoe\b/i, 10],
  [/nicky/i, 10], [/joelle/i, 9], [/susan/i, 8], [/google us english/i, 8], [/karen|moira|tessa|serena|fiona|catherine|libby|sonia|hazel/i, 6]]
const NOVELTY = /albert|bad news|bahh|bells|boing|bubbles|cellos|deranged|good news|hysterical|jester|organ|superstar|trinoids|whisper|wobble|zarvox|fred|junior|kathy|ralph|princess/i

export function voiceScore(v) {
  if (NOVELTY.test(v.name)) return -100
  let s = 0
  for (const [re, n] of QUALITY) if (re.test(v.name)) { s = Math.max(s, n) }
  for (const [re, n] of PREFERRED) if (re.test(v.name)) { s += n; break }
  if (/en[-_]US/i.test(v.lang)) s += 4
  else if (/en[-_]GB/i.test(v.lang)) s += 3
  if (FEMALE.test(v.name)) s += 2
  if (v.localService) s += 1
  return s
}

export function englishVoices() {
  if (!caps.synth) return []
  return window.speechSynthesis.getVoices().filter((v) => /^en/i.test(v.lang))
}
/** English voices on this computer, the most lifelike first. Used by the voice list in the Teacher panel. */
export function rankedVoices() {
  return englishVoices().map((v) => ({ v, score: voiceScore(v) })).sort((a, b) => b.score - a.score)
}
export function isFancyVoice(v) {
  return QUALITY.some(([re]) => re.test(v.name))
}
export function pickVoice() {
  const voices = englishVoices()
  if (!voices.length) return null
  if (settings.voiceName) {
    const exact = voices.find((v) => v.name === settings.voiceName)
    if (exact) return exact
  }
  if (settings.voiceStyle === 'girl') {
    return voices.find((v) => FEMALE.test(v.name)) || voices.find((v) => /en-(GB|US|GH|NG)/i.test(v.lang)) || voices[0]
  }
  return rankedVoices()[0].v
}

async function speakServer(text) {
  const chunks = sentences(text)
  const c = ctx()
  const pace = settings.voiceStyle === 'girl' ? 1.25 : 1.0          // 1.0 = a normal speaking pace
  const fetchChunk = (i) => api.tts(chunks[i], pace).then((buf) => c.decodeAudioData(buf.slice(0)))
  let cancelled = false
  stopCurrent = () => { cancelled = true }
  let next = fetchChunk(0)
  for (let i = 0; i < chunks.length && !cancelled; i++) {
    const audio = await next
    if (i + 1 < chunks.length) next = fetchChunk(i + 1)
    if (cancelled) break
    await new Promise((resolve) => {
      const src = c.createBufferSource()
      src.buffer = audio
      src.playbackRate.value = settings.serverPitch      // 1.0 = natural; higher = faster and higher, like a younger voice
      const analyser = c.createAnalyser()
      analyser.fftSize = 512
      src.connect(analyser)
      analyser.connect(c.destination)
      const data = new Uint8Array(analyser.fftSize)
      let raf = 0
      const tick = () => {
        analyser.getByteTimeDomainData(data)
        let sum = 0
        for (let k = 0; k < data.length; k++) { const v = (data[k] - 128) / 128; sum += v * v }
        mouth.value = Math.min(1, Math.sqrt(sum / data.length) * 5.5)
        raf = requestAnimationFrame(tick)
      }
      const done = () => { cancelAnimationFrame(raf); mouth.value = null; resolve() }
      src.onended = done
      stopCurrent = () => { cancelled = true; try { src.stop() } catch { /* already stopped */ } done() }
      src.start()
      tick()
    })
  }
}

function speakBrowser(text) {
  const synth = window.speechSynthesis
  const chunks = sentences(text)
  synth.cancel()
  return new Promise((resolve) => {
    let i = 0
    let finished = false
    let watchdog = null
    const end = () => { if (finished) return; finished = true; clearTimeout(watchdog); resolve() }
    stopCurrent = end
    const next = () => {
      if (finished) return
      if (i >= chunks.length) return end()
      const u = new SpeechSynthesisUtterance(chunks[i++])
      const v = pickVoice()
      if (v) { u.voice = v; u.lang = v.lang } else u.lang = 'en-GB'
      u.pitch = Math.max(0.1, Math.min(2, settings.pitch))
      u.rate = Math.max(0.5, Math.min(1.6, settings.rate))
      let started = false
      u.onstart = () => { started = true; clearTimeout(watchdog) }
      u.onend = next
      u.onerror = next
      synth.speak(u)
      // Some browsers silently drop speech. Never leave Marshie stuck "talking".
      clearTimeout(watchdog)
      watchdog = setTimeout(() => { if (!started) { synth.cancel(); next() } }, 3500)
    }
    next()
  })
}

/** Say something. Resolves when she has finished (or after a reading-time pause when muted). */
export async function speak(text) {
  stopSpeaking()
  const mine = speakSeq
  const readingTime = Math.min(7000, 700 + text.length * 42)
  if (!settings.voiceOn || !text) return sleep(readingTime)
  // Browsers with no voices installed (common on a fresh Raspberry Pi) "finish" instantly and silently.
  // Keep her face talking for a believable time anyway, unless she was interrupted.
  const started = Date.now()
  const minimum = Math.min(6000, 500 + text.length * 30)
  const settle = async () => {
    const left = minimum - (Date.now() - started)
    if (left > 0 && mine === speakSeq) await sleep(left)
  }
  try {
    if (caps.tts_server) { await speakServer(text); return settle() }
    if (caps.synth) { await speakBrowser(text); return settle() }
  } catch (e) {
    console.warn('[marshie] voice failed, falling back', e)
    try { if (caps.synth) { await speakBrowser(text); return settle() } } catch { /* ignore */ }
  }
  return sleep(readingTime)
}

// ----------------------------------------------------------------------------------------- listening
function downsample(float32, fromRate, toRate) {
  const ratio = fromRate / toRate
  const len = Math.floor(float32.length / ratio)
  const out = new Int16Array(len)
  for (let i = 0; i < len; i++) {
    const start = Math.floor(i * ratio)
    const end = Math.min(float32.length, Math.floor((i + 1) * ratio))
    let sum = 0
    for (let k = start; k < end; k++) sum += float32[k]
    const v = Math.max(-1, Math.min(1, sum / Math.max(1, end - start)))
    out[i] = v < 0 ? v * 0x8000 : v * 0x7fff
  }
  return out
}

async function listenServer(setStop) {
  if (!navigator.mediaDevices?.getUserMedia) throw new Error(micHelp())
  let stream
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } })
  } catch { throw new Error('I need to use the microphone. Please allow it, then tap the microphone again.') }
  const c = new (window.AudioContext || window.webkitAudioContext)()
  const source = c.createMediaStreamSource(stream)
  const proc = c.createScriptProcessor(4096, 1, 1)
  const chunks = []
  const started = Date.now()
  let heard = false
  let quietMs = 0
  let floor = 0.01
  let settled = false

  return new Promise((resolve, reject) => {
    const cleanup = () => {
      try { proc.disconnect(); source.disconnect() } catch { /* ignore */ }
      stream.getTracks().forEach((t) => t.stop())
      c.close().catch(() => {})
      listenLevel.value = 0
    }
    const finish = async (send) => {
      if (settled) return
      settled = true
      const rate = c.sampleRate
      cleanup()
      if (!send || !chunks.length) return resolve('')
      const total = chunks.reduce((n, a) => n + a.length, 0)
      const all = new Float32Array(total)
      let off = 0
      for (const a of chunks) { all.set(a, off); off += a.length }
      try { resolve(await api.stt(downsample(all, rate, 16000).buffer)) } catch (e) { reject(e) }
    }
    proc.onaudioprocess = (e) => {
      const d = e.inputBuffer.getChannelData(0)
      chunks.push(new Float32Array(d))
      let sum = 0
      for (let i = 0; i < d.length; i++) sum += d[i] * d[i]
      const rms = Math.sqrt(sum / d.length)
      listenLevel.value = Math.min(1, rms * 8)
      const threshold = Math.max(0.018, floor * 3)
      if (rms > threshold) { heard = true; quietMs = 0 }
      else {
        floor = floor * 0.95 + rms * 0.05
        if (heard) { quietMs += (d.length / c.sampleRate) * 1000; if (quietMs > 1400) finish(true) }
      }
      const elapsed = Date.now() - started
      if (!heard && elapsed > 7000) finish(false)
      if (elapsed > 15000) finish(heard)
    }
    source.connect(proc)
    proc.connect(c.destination)
    setStop(() => finish(heard))
  })
}

function listenBrowser(setStop) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!SR) return Promise.reject(new Error('This browser can’t listen yet. Please type your question.'))
  if (!window.isSecureContext) return Promise.reject(new Error(micHelp()))
  return new Promise((resolve, reject) => {
    let stopper = () => {}
    setStop(() => stopper())
    const run = (lang) => {
      const rec = new SR()
      rec.lang = lang
      rec.interimResults = true            // so the words appear on screen while the child is still speaking
      rec.maxAlternatives = 1
      rec.continuous = false
      let text = ''
      let retried = false
      liveText.value = ''
      rec.onresult = (e) => {
        text = Array.from(e.results).map((r) => r[0].transcript).join(' ').trim()
        liveText.value = text
      }
      rec.onerror = (e) => {
        liveText.value = ''
        if (e.error === 'language-not-supported' && lang !== 'en-US') { retried = true; return run('en-US') }
        if (e.error === 'no-speech' || e.error === 'aborted') return resolve('')
        if (e.error === 'not-allowed' || e.error === 'service-not-allowed') return reject(new Error('I need to use the microphone. Please allow it, then tap the microphone again.'))
        if (e.error === 'network') return reject(new Error('Listening needs the internet on this browser. You can type your question instead.'))
        reject(new Error('I couldn’t hear that. Please try again or type your question.'))
      }
      rec.onend = () => { if (!retried) { liveText.value = ''; resolve(text) } }
      stopper = () => { try { rec.stop() } catch { /* ignore */ } }
      try { rec.start() } catch { reject(new Error('I couldn’t start listening. Please try again.')) }
    }
    run(settings.lang || 'en-US')
  })
}

function micHelp() {
  return caps.secure
    ? 'This browser can’t use a microphone. Please type your question.'
    : 'The microphone only works on a secure address. Open Marshie at http://localhost:8000 on this computer, or ask your teacher to enable HTTPS.'
}

/** Returns { promise, stop }. The promise resolves with what the child said ('' if nothing). */
export function startListening() {
  stopSpeaking()
  let stop = () => {}
  const setStop = (fn) => { stop = fn }
  const promise = caps.stt_server ? listenServer(setStop) : listenBrowser(setStop)
  return { promise, stop: () => stop() }
}

export const canListen = () => caps.stt_server || (caps.recognition && caps.secure)
