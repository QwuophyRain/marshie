import { reactive, watch } from 'vue'

const KEY = 'marshie_settings_v1'

/** The two ways Marshie can sound. "natural" is a calm, clear assistant voice; "girl" is higher and younger. */
export const VOICE_STYLES = {
  natural: { pitch: 1.0, rate: 1.0, serverPitch: 1.0 },
  girl: { pitch: 1.85, rate: 1.0, serverPitch: 1.22 },
}

const defaults = {
  // voice
  voiceOn: true,
  voiceStyle: 'natural', // natural | girl | custom (custom = the sliders were moved by hand)
  pitch: VOICE_STYLES.natural.pitch,           // browser voice pitch (0.1 - 2)
  rate: VOICE_STYLES.natural.rate,
  voiceName: '',        // '' = pick the best English voice on this computer automatically
  serverPitch: VOICE_STYLES.natural.serverPitch, // playback speed for the offline (Piper) voice, which also changes its pitch
  lang: 'en-GH',        // browser speech recognition language
  // talking back and forth
  autoTalk: false,      // start the hands-free conversation by herself right after she wakes up (good for a school kiosk)
  chime: true,          // a soft sound when she starts listening, so children know it is their turn
  // screen
  autoClearMinutes: 3,  // wipe the conversation after this long without anyone (0 = never)
  sleepSeconds: 45,     // Marshie dozes off after this long (0 = never)
  bigText: false,
}

function load() {
  let saved = {}
  try { saved = JSON.parse(localStorage.getItem(KEY) || '{}') } catch { /* private mode */ }
  // Settings saved before voice styles existed carried the old high "girl" pitch. Start those on the natural voice.
  if (saved && !saved.voiceStyle) for (const k of ['pitch', 'rate', 'serverPitch', 'voiceName']) delete saved[k]
  return saved
}

export const settings = reactive({ ...defaults, ...load() })

export function applyVoiceStyle(style) {
  const preset = VOICE_STYLES[style]
  if (!preset) return
  Object.assign(settings, preset, { voiceStyle: style })
}

watch(settings, (v) => {
  try { localStorage.setItem(KEY, JSON.stringify(v)) } catch { /* private mode */ }
}, { deep: true })

export function resetSettings() {
  Object.assign(settings, defaults)
}
