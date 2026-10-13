// Who Marshie is and whose school she belongs to. Filled in from /api/health, with sensible words until it arrives.
import { reactive } from 'vue'
import { api } from './api'
import { applyTheme, SCHOOL_COLOURS } from './theme'
import { tIn } from './i18n'

export const brand = reactive({
  loaded: false,
  name: 'Marshie',
  school: 'Ecole Ronsard',
  event: 'STEAM Program 2026',
  greeting: 'Hello! My name is Marshie, your friendly educative chatbot for the Ecole Ronsard STEAM (Science, Technology, English, Agriculture & Arts, and Mathematics) Program 2026. How may I be of assistance?',
  greetingSpoken: '',
  theme: { ...SCHOOL_COLOURS },
  logo: '',                       // a logo a teacher uploaded; blank = the bundled Ecole Ronsard logo
  schoolUrl: '',
})

export const bundledLogo = './ecole-ronsard-logo.png'
export const bundledWordmark = './ecole-ronsard-wordmark.png'

const CACHE = 'marshie_theme_v1'

/** Colours from the last visit are applied at once, so the screen never flashes the wrong colours. */
export function applyCachedTheme() {
  try {
    const saved = JSON.parse(localStorage.getItem(CACHE) || 'null')
    if (saved) { Object.assign(brand.theme, saved); applyTheme(brand.theme) } else applyTheme(brand.theme)
  } catch { applyTheme(brand.theme) }
}

export function setTheme(theme) {
  Object.assign(brand.theme, { ...SCHOOL_COLOURS, ...theme })
  applyTheme(brand.theme)
  try { localStorage.setItem(CACHE, JSON.stringify(brand.theme)) } catch { /* private mode */ }
}

/** Try colours on this screen without keeping them (the Teacher panel's colour pickers). */
export function previewTheme(theme) {
  applyTheme({ ...SCHOOL_COLOURS, ...theme })
}

export async function loadBrand() {
  try {
    const h = await api.health()
    brand.name = h.name || brand.name
    brand.school = h.school || brand.school
    brand.event = h.event || brand.event
    if (h.greeting) brand.greeting = h.greeting
    brand.greetingSpoken = h.greeting_spoken || ''
    brand.logo = h.logo || ''
    brand.schoolUrl = h.school_url || ''
    setTheme(h.theme || {})
    brand.loaded = true
    return h
  } catch {
    brand.loaded = true
    return null
  }
}

// ---- the greeting in each language. English is the school's own (a teacher may have rewritten it); the other three
// come ready-made from the server. Until one has arrived, the built-in line is used, so waking her never has to wait.
const greetings = reactive({})

export function greetingFor(lang) {
  if (lang === 'en') return { text: brand.greeting, spoken: brand.greetingSpoken }
  const g = greetings[lang]
  if (g) return g
  return { text: tIn(lang, 'greeting.fallback', { name: brand.name, school: brand.school }), spoken: '' }
}

export async function loadGreeting(lang) {
  if (lang === 'en' || greetings[lang]) return
  try {
    const g = await api.greeting(lang)
    if (g?.text) greetings[lang] = { text: g.text, spoken: g.spoken || '' }
  } catch { /* offline: the built-in line is used */ }
}
