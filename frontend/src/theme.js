// School colours -> every colour on screen.
// A school gives four colours (the main one, a button colour, a highlight, a "good job" colour). Everything else is
// worked out here, so any colours a teacher picks still give readable text and clear buttons.

const clamp = (n, lo = 0, hi = 255) => Math.max(lo, Math.min(hi, n))

export const isHex = (v) => typeof v === 'string' && /^#[0-9a-f]{6}$/i.test(v)

export function toRgb(hex) {
  const n = parseInt(hex.slice(1), 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}
export function toHex([r, g, b]) {
  return '#' + [r, g, b].map((v) => clamp(Math.round(v)).toString(16).padStart(2, '0')).join('')
}
/** mix(a, b, t): t = 0 gives a, t = 1 gives b */
export function mix(a, b, t) {
  const x = toRgb(a)
  const y = toRgb(b)
  return toHex(x.map((v, i) => v * (1 - t) + y[i] * t))
}
/** The same hue, but pale: `l` is how light (0..1), `satCap` the most colour allowed (0..1). Keeps tints fresh, not grey. */
export function tint(hex, l, satCap = 0.6) {
  const [r, g, b] = toRgb(hex).map((v) => v / 255)
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  const d = max - min
  let h = 0
  if (d) h = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4
  h = (h * 60 + 360) % 360
  const lum = (max + min) / 2
  const s = d ? Math.min(satCap, d / (1 - Math.abs(2 * lum - 1))) : 0
  const c = (1 - Math.abs(2 * l - 1)) * s
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1))
  const m = l - c / 2
  const [r1, g1, b1] = h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x] : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x]
  return toHex([(r1 + m) * 255, (g1 + m) * 255, (b1 + m) * 255])
}

function luminance(hex) {
  const [r, g, b] = toRgb(hex).map((v) => {
    const c = v / 255
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}
export function contrast(a, b) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((p, q) => q - p)
  return (hi + 0.05) / (lo + 0.05)
}
/** Darken `hex` until it reads on `bg` with at least `min` contrast. */
function darkenFor(hex, bg, min) {
  let out = hex
  for (let i = 0; i < 20 && contrast(out, bg) < min; i++) out = mix(out, '#000000', 0.12)
  return out
}

export const SCHOOL_COLOURS = { primary: '#045870', button: '#fae240', highlight: '#e80075', success: '#74bd54' }

/** Every CSS variable the screens use, from the four school colours. */
export function themeVars(input) {
  const t = { ...SCHOOL_COLOURS }
  for (const k of Object.keys(t)) if (isHex(input?.[k])) t[k] = input[k].toLowerCase()
  const white = '#ffffff'
  const black = '#000000'
  const ink = darkenFor(mix(t.primary, black, 0.6), white, 12)
  const sky = tint(t.primary, 0.9, 0.6)
  const gold = t.button
  const green = t.success
  const onGold = contrast(ink, gold) >= contrast(white, gold) ? ink : white
  const onGreen = contrast(ink, green) >= contrast(white, green) ? ink : white
  const highlight = t.highlight
  return {
    '--brand': t.primary,
    '--ink': ink,
    '--ink-soft': darkenFor(mix(t.primary, black, 0.15), sky, 5.5),
    '--sky': sky,
    '--sky-deep': tint(t.primary, 0.76, 0.5),
    '--paper': tint(t.primary, 0.975, 0.6),
    '--line': tint(t.primary, 0.8, 0.35),
    '--pink': tint(highlight, 0.8, 0.9),
    '--pink-deep': highlight,
    '--pink-wash': tint(highlight, 0.94, 0.9),
    '--gold': gold,
    '--green': green,
    '--on-gold': onGold,
    '--on-green': onGreen,
    '--note': tint(gold, 0.86, 0.95),
    '--good-bg': tint(green, 0.84, 0.6),
    '--berry': '#cf2f3a',
    // Marshie herself: a white marshmallow, outlined softly in the main colour, with a bow in the highlight colour
    '--mm-line': tint(t.primary, 0.66, 0.4),
    '--mm-shade': tint(t.primary, 0.9, 0.4),
    '--mm-foot': tint(t.primary, 0.95, 0.4),
    '--mm-cheek': tint(highlight, 0.72, 0.9),
    '--bow': highlight,
    '--bow-dark': mix(highlight, black, 0.3),
    '--c1': t.primary, '--c2': gold, '--c3': highlight, '--c4': green,
  }
}

export function applyTheme(theme) {
  const vars = themeVars(theme)
  const root = document.documentElement
  for (const [k, v] of Object.entries(vars)) root.style.setProperty(k, v)
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.setAttribute('content', vars['--sky'])
  return vars
}

// ------------------------------------------------------------------------------------------ colours from a logo
/** Look at a picture and suggest the four colours. Returns null when it has no clear colours. */
export async function paletteFromImage(src) {
  const img = await new Promise((resolve, reject) => {
    const el = new Image()
    el.onload = () => resolve(el)
    el.onerror = () => reject(new Error('I could not open that picture.'))
    el.src = src
  })
  const scale = Math.min(1, 480 / Math.max(img.naturalWidth, img.naturalHeight))
  const w = Math.max(1, Math.round(img.naturalWidth * scale))
  const h = Math.max(1, Math.round(img.naturalHeight * scale))
  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  ctx.drawImage(img, 0, 0, w, h)
  const { data } = ctx.getImageData(0, 0, w, h)

  const hueOf = (r, g, b) => {
    const max = Math.max(r, g, b); const d = max - Math.min(r, g, b)
    if (!d) return 0
    const hh = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4
    return (hh * 60 + 360) % 360
  }
  const gap = (a, b) => { const d = Math.abs(a - b) % 360; return d > 180 ? 360 - d : d }

  // Count the strong colours. Soft edges (anti-aliasing) and greys are skipped; similar shades are grouped.
  const buckets = new Map()
  let counted = 0
  for (let i = 0; i < data.length; i += 4) {
    if (data[i + 3] < 200) continue
    const r = data[i]; const g = data[i + 1]; const b = data[i + 2]
    const max = Math.max(r, g, b)
    const min = Math.min(r, g, b)
    const sat = max === 0 ? 0 : (max - min) / max
    if (sat < 0.55 || max < 90) continue
    counted += 1
    const key = ((r >> 5) << 6) | ((g >> 5) << 3) | (b >> 5)
    const e = buckets.get(key) || { n: 0, r: 0, g: 0, b: 0 }
    e.n += 1; e.r += r; e.g += g; e.b += b
    buckets.set(key, e)
  }
  if (counted < 40) return null

  const list = [...buckets.values()]
    .map((e) => { const rgb = [e.r / e.n, e.g / e.n, e.b / e.n]; return { n: e.n, rgb, hue: hueOf(...rgb) } })
    .filter((e) => e.n >= Math.max(6, counted * 0.0015))
    .sort((a, b) => b.n - a.n)
  const chosen = []
  for (const c of list) {
    if (chosen.every((o) => gap(c.hue, o.hue) >= 28)) chosen.push(c)       // one colour per hue, the most used shade of it
    if (chosen.length === 4) break
  }
  if (!chosen.length) return null

  const inHue = (c, lo, hi) => c.hue >= lo && c.hue <= hi
  const out = { primary: toHex(chosen[0].rgb) }
  let rest = chosen.slice(1)
  const take = (test) => { const i = rest.findIndex(test); return i >= 0 ? toHex(rest.splice(i, 1)[0].rgb) : undefined }
  out.button = take((c) => inHue(c, 20, 70))                                  // yellow or orange suits big buttons
  out.success = take((c) => inHue(c, 70, 170))                               // green
  out.highlight = take((c) => c.hue >= 280 || c.hue < 20)                    // pink, red, magenta or purple
  rest.sort((a, b) => luminance(toHex(b.rgb)) - luminance(toHex(a.rgb)))
  for (const role of ['button', 'highlight', 'success']) if (!out[role] && rest.length) out[role] = toHex(rest.shift().rgb)
  for (const role of Object.keys(out)) if (!out[role]) delete out[role]
  return out
}
