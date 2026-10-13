// Marshie's voice: she talks (server voice on the Pi, else the browser's) and listens (server mic, else the browser's).
import { reactive, ref } from 'vue'
import { api } from '../api'
import { settings, VOICE_STYLES } from '../settings'
import { LANGUAGES, lang as currentLang, t } from '../i18n'

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

const FEMALE = new RegExp([
  'female|\\+f\\d|zira|samantha|karen|moira|tessa|fiona|victoria|jenny|aria|hazel|susan|ava|allison|ellen|serena|catherine|libby|sonia|natasha',
  'google uk english female',
  'am[eé]lie|audrey|marie|virginie|denise|eloise|brigitte|c[eé]line|julie',              // French
  'm[oó]nica|paulina|helena|elvira|luc[ií]a|sabina|laura|carmen|conchita|marisol|esperanza',  // Spanish
  'anna|petra|katja|marlene|vicki|hedda|amala|seraphina|klara|vicki',                     // German
].join('|'), 'i')

// Voices that sound like a phone assistant. Apple's "Siri", "Premium" and "Enhanced" voices and Microsoft's "Natural"
// voices are the most lifelike; the plain built-in ones come next. Novelty voices (Zarvox, Bells...) are never chosen.
const QUALITY = [[/siri/i, 60], [/premium/i, 40], [/natural|neural|online/i, 36], [/enhanced/i, 30]]
const PREFERRED = [[/\bava\b/i, 14], [/samantha/i, 13], [/\baria\b/i, 13], [/jenny/i, 12], [/allison/i, 11], [/\bzoe\b/i, 10],
  [/nicky/i, 10], [/joelle/i, 9], [/susan/i, 8], [/google us english/i, 8], [/karen|moira|tessa|serena|fiona|catherine|libby|sonia|hazel/i, 6],
  // her other three languages
  [/am[eé]lie|denise|elvira|\banna\b|katja/i, 13], [/audrey|paulina|m[oó]nica|helena|seraphina|amala|marlene/i, 11],
  [/google (fran[cç]ais|espa[nñ]ol|deutsch)/i, 8], [/virginie|eloise|luc[ií]a|sabina|petra|vicki|hedda/i, 7]]
// The home accent of each language scores highest, so a French child hears France, not Canada, when both are installed.
const HOME = [[/en[-_]US/i, 4], [/en[-_]GB/i, 3], [/fr[-_]FR/i, 4], [/es[-_]ES/i, 4], [/es[-_](MX|US)/i, 3], [/de[-_]DE/i, 4]]
// Boy voices (used when a child picks the bow tie): the names of male voices on Mac, Windows, Android and in Chrome.
const MALE = new RegExp([
  '\\bmale\\b|\\+m\\d|daniel|\\balex\\b|aaron|arthur|oliver|\\bguy\\b|ryan|george|david|\\bmark\\b|james|brian|christopher|eric|roger|steffan|william|liam|nathan|gordon|rishi|evan',
  'thomas|nicolas|henri|claude|paul|jorge|diego|juan|pablo|enrique|carlos|alvaro|markus|stefan|yannick|hans|conrad|killian|florian|jonas|stefan',
].join('|'), 'i')
const PREFERRED_MALE = [[/daniel/i, 14], [/\balex\b/i, 13], [/\bguy\b/i, 13], [/ryan/i, 12], [/aaron/i, 11], [/arthur/i, 10],
  [/google uk english male/i, 8], [/thomas|oliver|george|david|brian|eric|roger|steffan|liam|nathan|william|james|\bmark\b/i, 6],
  [/thomas|nicolas|jorge|diego|juan|markus|stefan|jonas|conrad|killian/i, 11], [/henri|pablo|enrique|carlos|florian|yannick|hans/i, 7]]
const NOVELTY = /albert|bad news|bahh|bells|boing|bubbles|cellos|deranged|good news|hysterical|jester|organ|superstar|trinoids|whisper|wobble|zarvox|fred|junior|kathy|ralph|princess/i

export const isBoy = () => settings.voiceGender === 'male'

export function voiceScore(v) {
  if (NOVELTY.test(v.name)) return -100
  const boy = isBoy()
  const female = FEMALE.test(v.name)
  const male = MALE.test(v.name) && !female
  let s = 0
  for (const [re, n] of QUALITY) if (re.test(v.name)) { s = Math.max(s, n) }
  for (const [re, n] of (boy ? PREFERRED_MALE : PREFERRED)) if (re.test(v.name)) { s += n; break }
  for (const [re, n] of HOME) if (re.test(v.lang)) { s += n; break }
  if (boy) s += male ? 8 : female ? -12 : 0         // a boy gets a boy's voice when the computer has one
  else s += female ? 2 : male ? -6 : 0
  if (v.localService) s += 1
  return s
}

/** How loud-high and how fast she speaks. The boy voice is lower, whatever the "young girl" sliders say. */
function tuning() {
  if (!isBoy()) return { pitch: settings.pitch, rate: settings.rate, serverPitch: settings.serverPitch, pace: settings.voiceStyle === 'girl' ? 1.25 : 1.0 }
  const base = settings.voiceStyle === 'girl' ? VOICE_STYLES.natural : settings
  return { pitch: Math.max(0.1, base.pitch * 0.92), rate: base.rate, serverPitch: Math.min(base.serverPitch, 1) * 0.86, pace: 1.0 }
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
/** Voices installed on this computer for French, Spanish or German ('fr', 'es', 'de'). */
export function voicesFor(code) {
  if (!caps.synth || !code) return []
  return window.speechSynthesis.getVoices().filter((v) => v.lang && v.lang.toLowerCase().replace('_', '-').startsWith(code))
}

/** The voice for a language. English honours the voice a teacher picked; the others pick the best female voice installed. */
export function pickVoice(code = 'en') {
  if (code !== 'en') {
    const ranked = voicesFor(code).map((v) => ({ v, score: voiceScore(v) })).sort((a, b) => b.score - a.score)
    return ranked.length && ranked[0].score > -50 ? ranked[0].v : null
  }
  const voices = englishVoices()
  if (!voices.length) return null
  if (settings.voiceName) {
    const exact = voices.find((v) => v.name === settings.voiceName)
    if (exact) return exact
  }
  if (settings.voiceStyle === 'girl' && !isBoy()) {
    return voices.find((v) => FEMALE.test(v.name)) || voices.find((v) => /en-(GB|US|GH|NG)/i.test(v.lang)) || voices[0]
  }
  return rankedVoices()[0].v
}

async function speakServer(text) {
  const chunks = sentences(text)
  const c = ctx()
  const tune = tuning()
  const pace = tune.pace                                             // 1.0 = a normal speaking pace
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
      src.playbackRate.value = tune.serverPitch          // 1.0 = natural; higher = faster and higher, like a younger voice
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

function speakBrowser(text, code = 'en') {
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
      const v = pickVoice(code)
      if (v) { u.voice = v; u.lang = v.lang } else u.lang = code === 'en' ? 'en-GB' : LANGUAGES[code].speech
      const tune = tuning()
      u.pitch = Math.max(0.1, Math.min(2, tune.pitch))
      u.rate = Math.max(0.5, Math.min(1.6, tune.rate))
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

/**
 * Say something. Resolves when she has finished (or after a reading-time pause when muted).
 * `lang` is the language of the text; `parts` is a list of { text, lang } when one answer mixes two languages
 * (a French child asking about something she only knows in English hears each part in its own voice).
 */
export async function speak(text, opts = {}) {
  stopSpeaking()
  const mine = speakSeq
  const parts = (Array.isArray(opts.parts) && opts.parts.length ? opts.parts : [{ text, lang: opts.lang }])
    .map((p) => ({ text: p.text, lang: LANGUAGES[p.lang] ? p.lang : currentLang() }))
    .filter((p) => p.text)
  const all = parts.map((p) => p.text).join(' ')
  const readingTime = Math.min(7000, 700 + all.length * 42)
  if (!settings.voiceOn || !all) return sleep(readingTime)
  // Browsers with no voices installed (common on a fresh Raspberry Pi) "finish" instantly and silently.
  // Keep her face talking for a believable time anyway, unless she was interrupted.
  const started = Date.now()
  const minimum = Math.min(6000, 500 + all.length * 30)
  const settle = async () => {
    const left = minimum - (Date.now() - started)
    if (left > 0 && mine === speakSeq) await sleep(left)
  }
  const sayOne = async (part) => {
    // The offline (Piper) voice speaks English only; every other language uses the browser's voices.
    if (caps.tts_server && part.lang === 'en') return speakServer(part.text)
    if (caps.synth) return speakBrowser(part.text, part.lang)
    throw new Error('no voice')
  }
  try {
    for (const part of parts) {
      if (mine !== speakSeq) return
      await sayOne(part)
    }
    return settle()
  } catch (e) {
    if (e.message !== 'no voice') console.warn('[marshie] voice failed, falling back', e)
    try {
      if (caps.synth) {
        for (const part of parts) { if (mine !== speakSeq) return; await speakBrowser(part.text, part.lang) }
        return settle()
      }
    } catch { /* ignore */ }
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
  } catch { throw new Error(t('err.micServer')) }
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

/** What went wrong the last time the browser tried to listen. The Teacher panel explains it in plain words. */
export const listenIssue = reactive({ code: '', at: 0 })

/** Which browser this is, and whether it can use the speech service that listening needs. */
export function browserInfo() {
  const ua = typeof navigator !== 'undefined' ? navigator.userAgent || '' : ''
  if (typeof navigator !== 'undefined' && navigator.brave) {
    return { id: 'brave', name: 'Brave', works: false,
      note: 'Brave switches off the Google speech service that listening needs, so listening fails here even when you are online. Open Marshie in Google Chrome or Microsoft Edge, or install the offline listener below.' }
  }
  if (/Firefox\//.test(ua)) {
    return { id: 'firefox', name: 'Firefox', works: false, note: 'Firefox cannot listen to speech. Use Google Chrome or Microsoft Edge, or install the offline listener below.' }
  }
  if (/Edg\//.test(ua)) return { id: 'edge', name: 'Microsoft Edge', works: true, note: '' }
  if (/OPR\/|Vivaldi|SamsungBrowser/.test(ua)) {
    return { id: 'other', name: 'this browser', works: false,
      note: 'Opera, Vivaldi and some other browsers do not include the speech service. Use Google Chrome or Microsoft Edge, or install the offline listener below.' }
  }
  if (/Chrome\//.test(ua)) return { id: 'chrome', name: 'Chrome', works: true, note: '' }
  if (/Safari\//.test(ua)) {
    return { id: 'safari', name: 'Safari', works: false,
      note: 'Safari only listens when Dictation is switched on (System Settings, Keyboard, Dictation) and is often unreliable. Use Google Chrome, or install the offline listener below.' }
  }
  return { id: 'unknown', name: 'this browser', works: true, note: '' }
}

/** Plain words for the Teacher panel about why listening failed. */
export function listenAdvice(code) {
  const b = browserInfo()
  if (code === 'network') {
    return b.note || 'The browser could not reach its speech service. This is not your internet being down: a VPN, a firewall or school network, a privacy or ad blocker, or a browser that does not include the service (such as Brave, Arc or Chromium) can stop it. Try Google Chrome without a VPN, or install the offline listener below.'
  }
  if (code === 'service-not-allowed') return b.note || 'The browser refused to use speech recognition. Try Google Chrome, or install the offline listener below.'
  if (code === 'not-allowed') return 'The microphone is blocked. Click the padlock or microphone icon in the address bar, choose Allow for the microphone, then reload. On a Mac also check System Settings, Privacy & Security, Microphone, and switch the browser on.'
  return ''
}

/** The language the browser should listen for: the child's own for French, Spanish and German; Ghana English for English. */
function recognitionLang() {
  const code = currentLang()
  return code === 'en' ? (settings.lang || 'en-US') : LANGUAGES[code].speech
}

function listenBrowser(setStop) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!SR) return Promise.reject(new Error(t('mic.cantListen')))
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
        // Some voice-recognition services do not know every variety (such as Ghana English): try the plain version once
        // (US English, or just "fr", "es", "de").
        const plainLang = currentLang() === 'en' ? 'en-US' : currentLang()
        if ((e.error === 'language-not-supported' || e.error === 'network') && lang !== plainLang) { retried = true; return run(plainLang) }
        if (e.error === 'no-speech' || e.error === 'aborted') return resolve('')
        listenIssue.code = e.error
        listenIssue.at = Date.now()
        if (e.error === 'not-allowed') return reject(new Error(t('err.micBrowser')))
        if (e.error === 'service-not-allowed' || e.error === 'network') return reject(new Error(t('err.listenBroken')))
        reject(new Error(t('err.couldntHear')))
      }
      rec.onend = () => { if (!retried) { liveText.value = ''; resolve(text) } }
      stopper = () => { try { rec.stop() } catch { /* ignore */ } }
      try { rec.start() } catch { reject(new Error(t('err.couldntStart'))) }
    }
    run(recognitionLang())
  })
}

function micHelp() {
  return caps.secure ? t('err.noMic') : t('err.insecure')
}

/** Returns { promise, stop }. The promise resolves with what the child said ('' if nothing). */
export function startListening() {
  stopSpeaking()
  let stop = () => {}
  const setStop = (fn) => { stop = fn }
  // The offline listener (Vosk) understands English only. The other languages need the browser's own listening.
  const promise = useServerEars() ? listenServer(setStop) : listenBrowser(setStop)
  return { promise, stop: () => stop() }
}

const browserEars = () => caps.recognition && caps.secure
const useServerEars = () => caps.stt_server && currentLang() === 'en'
/** Can she listen right now, in the language that is on screen? */
export const canListen = () => browserEars() || (caps.stt_server && currentLang() === 'en')
