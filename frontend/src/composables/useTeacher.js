// Shared state for the Teacher panel: who is signed in, the latest overview, and little "saved" messages.
import { ref } from 'vue'
import { api, hasAdminToken, setAdminToken } from '../api'

export const authed = ref(hasAdminToken())
export const loginNote = ref('')
export const overview = ref(null)
export const toast = ref({ text: '', bad: false })
export const teachPrefill = ref('')      // a question the teacher wants to answer, sent from the "to learn" list

let timer = null
export function say(text, bad = false) {
  toast.value = { text, bad }
  clearTimeout(timer)
  timer = setTimeout(() => { toast.value = { text: '', bad: false } }, bad ? 7000 : 4000)
}

export function signedIn(token) {
  setAdminToken(token)
  authed.value = true
  loginNote.value = ''
}

export function logout(note = '') {
  setAdminToken('')
  authed.value = false
  overview.value = null
  loginNote.value = note
}

/** Runs an admin call. A wrong or expired sign-in sends the teacher back to the PIN screen. */
export async function guard(fn) {
  try {
    return await fn()
  } catch (e) {
    if (e.status === 401) logout('Please enter the PIN again.')
    else say(e.message, true)
    return undefined
  }
}

export async function loadOverview() {
  const o = await guard(() => api.overview())
  if (o) overview.value = o
  return o
}

export const when = (ts) => {
  try { return new Date(ts * 1000).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) } catch { return '' }
}
