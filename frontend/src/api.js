// Thin wrapper around Marshie's API. Same code runs on the Pi (served by FastAPI) and on Vercel (/api function).
const BASE = import.meta.env.VITE_API_BASE || ''

let adminToken = ''
try { adminToken = sessionStorage.getItem('marshie_admin') || '' } catch { /* private mode */ }

export function setAdminToken(token) {
  adminToken = token || ''
  try {
    if (token) sessionStorage.setItem('marshie_admin', token)
    else sessionStorage.removeItem('marshie_admin')
  } catch { /* ignore */ }
}
export const hasAdminToken = () => !!adminToken

async function request(path, { method = 'GET', body, form, raw, admin = false, signal } = {}) {
  const headers = {}
  if (admin && adminToken) headers['X-Admin-Token'] = adminToken
  let payload
  if (form) payload = form
  else if (raw !== undefined) { payload = raw; headers['Content-Type'] = 'application/octet-stream' }
  else if (body !== undefined) { payload = JSON.stringify(body); headers['Content-Type'] = 'application/json' }
  let res
  try {
    res = await fetch(BASE + path, { method, headers, body: payload, signal })
  } catch (e) {
    const err = new Error('I can’t reach my brain right now. Is the server running?')
    err.offline = true
    throw err
  }
  if (!res.ok) {
    let detail = ''
    try { detail = (await res.json()).detail } catch { /* not json */ }
    const err = new Error(typeof detail === 'string' && detail ? detail : `Something went wrong (${res.status}).`)
    err.status = res.status
    throw err
  }
  return res
}
const json = async (path, opts) => (await request(path, opts)).json()

export const api = {
  health: () => json('/api/health'),
  ask: (question, history = []) => json('/api/ask', { method: 'POST', body: { question, history } }),
  feedback: (p) => json('/api/feedback', { method: 'POST', body: p }),
  teach: (p) => json('/api/teach', { method: 'POST', body: p }),
  quiz: (category = '', level = 1) => json(`/api/quiz?category=${encodeURIComponent(category)}&level=${level}`),
  quizCheck: (p) => json('/api/quiz/check', { method: 'POST', body: p }),
  tts: async (text, lengthScale = 1.25) =>
    (await request('/api/tts', { method: 'POST', body: { text, length_scale: lengthScale } })).arrayBuffer(),
  stt: async (pcm) => (await json('/api/stt', { method: 'POST', raw: pcm })).text,

  login: (pin) => json('/api/admin/login', { method: 'POST', body: { pin } }),
  overview: () => json('/api/admin/overview', { admin: true }),
  setSettings: (s) => json('/api/admin/settings', { method: 'POST', body: s, admin: true }),
  ai: () => json('/api/admin/ai', { admin: true }),
  saveAi: (b) => json('/api/admin/ai', { method: 'PUT', body: b, admin: true }),
  testAi: (b) => json('/api/admin/ai/test', { method: 'POST', body: b, admin: true }),
  removeAi: () => json('/api/admin/ai', { method: 'DELETE', admin: true }),
  entries: (params) => json('/api/admin/entries?' + new URLSearchParams(params), { admin: true }),
  deleteEntry: (id) => json(`/api/admin/entries/${id}`, { method: 'DELETE', admin: true }),
  approveEntry: (id) => json(`/api/admin/entries/${id}/approve`, { method: 'POST', admin: true }),
  addEntry: (p) => json('/api/admin/entries', { method: 'POST', body: p, admin: true }),
  deleteDataset: (id) => json(`/api/admin/datasets/${id}`, { method: 'DELETE', admin: true }),
  upload: (file, commit) => {
    const form = new FormData()
    form.append('file', file)
    form.append('commit', commit ? 'true' : 'false')
    return json('/api/admin/upload', { method: 'POST', form, admin: true })
  },
  addMedia: (form) => json('/api/admin/media', { method: 'POST', form, admin: true }),
  addDocument: (form) => json('/api/admin/document', { method: 'POST', form, admin: true }),
  library: () => json('/api/admin/library', { admin: true }),
  deleteLibraryItem: (id) => json(`/api/admin/library/${id}`, { method: 'DELETE', admin: true }),
  undoUpload: (id) => json(`/api/admin/uploads/${id}/undo`, { method: 'POST', admin: true }),
  setLogo: (file) => {
    const form = new FormData()
    form.append('file', file)
    return json('/api/admin/logo', { method: 'POST', form, admin: true })
  },
  removeLogo: () => json('/api/admin/logo', { method: 'DELETE', admin: true }),
  restore: (file) => {
    const form = new FormData()
    form.append('file', file)
    return json('/api/admin/restore', { method: 'POST', form, admin: true })
  },
  // Downloads are plain links, so the token travels in the query string.
  downloadUrl: (path, params = {}) =>
    BASE + path + '?' + new URLSearchParams({ ...params, token: adminToken }).toString(),
}
