// Checks the screen's words: every phrase written in English, French, Spanish and German, every placeholder the same
// in all four, every t('key') in the code defined, and a list of every tap-to-ask question for the API test.
// Run:  node frontend/scripts/check-i18n.mjs     (prints JSON; exit code 1 if anything is missing)
import { build } from 'esbuild'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const bundled = await build({
  stdin: {
    contents: "export * from './src/i18n.js'; export { ALL_CHIPS, TOPIC_IDS } from './src/topics.js'",
    resolveDir: root, loader: 'js',
  },
  bundle: true, write: false, format: 'esm', platform: 'node', logLevel: 'silent',
})
const code = bundled.outputFiles[0].text
const mod = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'))
const { TABLE, ALL_KEYS, LANGUAGES, ALL_CHIPS, TOPIC_IDS } = mod

const problems = []
const codes = Object.keys(LANGUAGES)
const holes = (v) => (Array.isArray(v) ? v.join(' ') : v).match(/\{\w+\}/g)?.sort().join(',') || ''

for (const key of ALL_KEYS) {
  const row = TABLE[key]
  for (const c of codes) {
    if (row[c] === undefined || row[c] === '' || (Array.isArray(row[c]) && !row[c].length)) problems.push(`${key}: missing ${c}`)
  }
  if (!codes.every((c) => row[c] !== undefined)) continue
  const kinds = new Set(codes.map((c) => Array.isArray(row[c])))
  if (kinds.size > 1) problems.push(`${key}: some languages have a list and some a sentence`)
  if (Array.isArray(row.en)) {
    for (const c of codes) if (row[c].length !== row.en.length) problems.push(`${key}: ${c} has ${row[c].length} lines, English has ${row.en.length}`)
  }
  const want = holes(row.en)
  for (const c of codes) if (holes(row[c]) !== want) problems.push(`${key}: ${c} uses ${holes(row[c]) || 'no'} placeholders, English uses ${want || 'none'}`)
  if (key.endsWith('.m') && !TABLE[key.slice(0, -2)]) problems.push(`${key}: boy wording without a base phrase`)
}

// every t('...') / tIn(x, '...') in the code must exist
const files = []
const walk = (dir) => {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name)
    if (statSync(p).isDirectory()) walk(p)
    else if (/\.(vue|js)$/.test(name)) files.push(p)
  }
}
walk(join(root, 'src'))
const used = new Set()
for (const f of files) {
  // leave out comment lines, which sometimes show an example call
  const text = readFileSync(f, 'utf8').split('\n').filter((line) => !/^\s*(\/\/|\*|\/\*)/.test(line)).join('\n')
  for (const m of text.matchAll(/\bt\(\s*'([\w.]+)'/g)) used.add(m[1])
  for (const m of text.matchAll(/\btIn\(\s*[\w.]+\s*,\s*'([\w.]+)'/g)) used.add(m[1])
}
for (const id of TOPIC_IDS) used.add(`topic.${id}`)
for (const mood of ['idle', 'listening', 'thinking', 'talking', 'hello', 'love', 'laugh', 'wow', 'celebrate', 'sad', 'unsure', 'sleepy']) used.add(`cap.${mood}`)
used.add('cap.asleep')
for (const key of used) if (!TABLE[key]) problems.push(`${key}: used in the code but not written`)

console.log(JSON.stringify({ keys: ALL_KEYS.length, used: used.size, problems, chips: ALL_CHIPS }))
process.exit(problems.length ? 1 : 0)
