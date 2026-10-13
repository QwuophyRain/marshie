<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  mood: { type: String, default: 'idle' },
  // 0..1, measured from the audio while Marshie speaks. When absent, a gentle random flap is used.
  mouthLevel: { type: Number, default: null },
  // little idle surprises: a wave, a wink, a hop, a look around. Off in the faces gallery.
  antics: { type: Boolean, default: true },
  // 'female' wears a bow on her head; 'male' wears a bow tie at his neck. It follows the voice a child picks.
  gender: { type: String, default: 'female' },
})

// What each feeling looks like. `speak` moods also move their mouth while she talks.
const CFG = {
  idle:      { eyes: 'open',  brows: 'none',   mouth: 'smile', cheeks: 1,   arms: 'rest',  fx: null,       label: 'smiling' },
  listening: { eyes: 'wide',  brows: 'raised', mouth: 'o',     cheeks: 1,   arms: 'ear',   fx: 'waves',    label: 'listening' },
  thinking:  { eyes: 'look',  brows: 'think',  mouth: 'hmm',   cheeks: 0.9, arms: 'chin',  fx: 'thought',  label: 'thinking' },
  talking:   { eyes: 'open',  brows: 'none',   mouth: 'talk',  cheeks: 1,   arms: 'talk',  fx: null,       label: 'talking', speak: true },
  hello:     { eyes: 'open',  brows: 'raised', mouth: 'talk',  cheeks: 1.2, arms: 'wave',  fx: 'sparkles', label: 'waving hello', speak: true, openMin: 0.18 },
  love:      { eyes: 'happy', brows: 'none',   mouth: 'talk',  cheeks: 1.8, arms: 'hug',   fx: 'hearts',   label: 'feeling loved', speak: true },
  laugh:     { eyes: 'happy', brows: 'none',   mouth: 'talk',  cheeks: 1.4, arms: 'tummy', fx: 'joy',      label: 'laughing', speak: true, openMin: 0.55 },
  wow:       { eyes: 'wide',  brows: 'high',   mouth: 'talk',  cheeks: 1,   arms: 'wow',   fx: 'sparkles', label: 'amazed', speak: true, openMin: 0.2 },
  celebrate: { eyes: 'happy', brows: 'none',   mouth: 'cheer', cheeks: 1.5, arms: 'up',    fx: 'confetti', label: 'celebrating' },
  sad:       { eyes: 'sad',   brows: 'sad',    mouth: 'frown', cheeks: 0.45, arms: 'down', fx: 'tears',    label: 'sad and sorry' },
  unsure:    { eyes: 'open',  brows: 'unsure', mouth: 'wavy',  cheeks: 1,   arms: 'shrug', fx: 'question', label: 'puzzled' },
  sleepy:    { eyes: 'closed', brows: 'none',  mouth: 'tiny',  cheeks: 0.8, arms: 'rest',  fx: 'zzz',      label: 'sleepy' },
}
const cfg = computed(() => CFG[props.mood] || CFG.idle)
const speaking = computed(() => !!cfg.value.speak)

// ---- mouth flapping while talking
const sim = ref(0)
let timer = null
function startSim() {
  stopSim()
  let t = 0
  timer = setInterval(() => {
    t += 1
    const target = 0.12 + Math.abs(Math.sin(t * 0.9)) * 0.55 + Math.random() * 0.25
    sim.value = sim.value * 0.4 + target * 0.6
  }, 110)
}
function stopSim() {
  if (timer) clearInterval(timer)
  timer = null
  sim.value = 0
}
watch(speaking, (on) => (on ? startSim() : stopSim()), { immediate: true })

const level = computed(() => {
  if (!speaking.value) return 0
  const live = props.mouthLevel ?? sim.value
  return Math.min(1, Math.max(cfg.value.openMin || 0, live))
})
const talkPath = computed(() => {
  const a = level.value
  if (a < 0.07) return null
  const w = 26 + 10 * a
  const y = 268
  const depth = 14 + 56 * a
  return `M${200 - w} ${y - 2} Q200 ${y + 4} ${200 + w} ${y - 2} Q${200 + w * 0.85} ${y + depth} 200 ${y + depth + 4} Q${200 - w * 0.85} ${y + depth} ${200 - w} ${y - 2} Z`
})

// ---- little idle surprises
const antic = ref('')
const lookX = ref(0)
const ANTICS = [['wave', 2000], ['wink', 1000], ['hop', 950], ['look', 1500], ['wiggle', 1000], ['twirl', 1000], ['hop', 950], ['look', 1500]]
let anticTimer = null
let anticEnd = null
function scheduleAntic() {
  clearTimeout(anticTimer)
  if (!props.antics) return
  anticTimer = setTimeout(() => {
    if (props.mood !== 'idle') return scheduleAntic()
    const [name, ms] = ANTICS[Math.floor(Math.random() * ANTICS.length)]
    antic.value = name
    if (name === 'look') lookX.value = Math.random() < 0.5 ? -9 : 9
    anticEnd = setTimeout(() => { antic.value = ''; lookX.value = 0; scheduleAntic() }, ms)
  }, 2600 + Math.random() * 3200)
}
function clearAntic() {
  clearTimeout(anticTimer)
  clearTimeout(anticEnd)
  antic.value = ''
  lookX.value = 0
}
watch(() => props.mood, (m) => { if (m !== 'idle') { clearAntic() } else scheduleAntic() })
onMounted(scheduleAntic)
onBeforeUnmount(() => { stopSim(); clearAntic() })

const winking = computed(() => antic.value === 'wink' && props.mood === 'idle')

// ---- effects with a fixed layout, so they are calm and predictable
const confetti = Array.from({ length: 26 }, (_, i) => {
  const side = i % 2 ? 1 : -1
  return {
    dx: side * (30 + ((i * 53) % 170)),
    dy: 30 + ((i * 67) % 270),
    rot: ((i * 97) % 520) - 260,
    delay: ((i * 0.13) % 1.4).toFixed(2),
    dur: (1.5 + ((i * 0.17) % 0.9)).toFixed(2),
    color: ['var(--c1)', 'var(--c2)', 'var(--c3)', 'var(--c4)', '#ffffff'][i % 5],
    round: i % 3 === 0,
  }
})
const HEART = 'M12 21 C5 15 2 11 2 7.5 C2 4.5 4.3 2.5 7 2.5 C9 2.5 10.7 3.6 12 5.4 C13.3 3.6 15 2.5 17 2.5 C19.7 2.5 22 4.5 22 7.5 C22 11 19 15 12 21 Z'
const hearts = [
  { x: 96, y: 118, s: 1.5, d: 0 }, { x: 292, y: 96, s: 1.9, d: 0.5 }, { x: 150, y: 70, s: 1.1, d: 1.0 },
  { x: 330, y: 190, s: 1.2, d: 1.5 }, { x: 60, y: 210, s: 1.3, d: 0.8 }, { x: 236, y: 52, s: 1.0, d: 1.2 },
]
const STAR = 'M0 -16 L4 -4 L16 0 L4 4 L0 16 L-4 4 L-16 0 L-4 -4 Z'
const stars = [
  { x: 60, y: 90, s: 1.2, d: 0 }, { x: 340, y: 70, s: 1.5, d: 0.3 }, { x: 354, y: 190, s: 0.9, d: 0.6 },
  { x: 40, y: 200, s: 1, d: 0.9 }, { x: 200, y: 14, s: 1.1, d: 0.45 },
]
</script>

<template>
  <svg
    class="marshie"
    :class="[`mood-${mood}`, antic && mood === 'idle' ? `antic-${antic}` : '']"
    viewBox="0 0 400 470"
    role="img"
    :aria-label="`Marshie the marshmallow, ${cfg.label}`"
    :data-antic="antic"
  >
    <defs>
      <radialGradient id="mm-body" cx="38%" cy="28%" r="85%">
        <stop offset="0" style="stop-color: #ffffff" />
        <stop offset="0.6" style="stop-color: #ffffff" />
        <stop offset="1" style="stop-color: var(--mm-shade)" />
      </radialGradient>
      <clipPath id="mm-mouth">
        <path d="M156 262 Q200 270 244 262 Q236 332 200 334 Q164 332 156 262 Z" />
      </clipPath>
      <clipPath id="mm-talk" v-if="talkPath">
        <path :d="talkPath" />
      </clipPath>
    </defs>

    <!-- ground shadow -->
    <ellipse class="shadow" cx="200" cy="450" rx="118" ry="13" style="fill: var(--ink)" opacity="0.14" />

    <!-- listening waves sit beside the body -->
    <g v-if="cfg.fx === 'waves'" class="fx waves" fill="none" style="stroke: var(--c2)" stroke-width="8" stroke-linecap="round">
      <path class="w1" d="M58 190 Q38 235 58 280" />
      <path class="w2" d="M34 165 Q2 235 34 305" />
      <path class="w1" d="M342 190 Q362 235 342 280" />
      <path class="w2" d="M366 165 Q398 235 366 305" />
    </g>

    <g class="hop">
      <g class="bob">
        <g class="tilt">
          <!-- feet -->
          <ellipse class="foot" cx="140" cy="430" rx="38" ry="19" style="fill: var(--mm-foot); stroke: var(--mm-line)" stroke-width="4" />
          <ellipse class="foot" cx="260" cy="430" rx="38" ry="19" style="fill: var(--mm-foot); stroke: var(--mm-line)" stroke-width="4" />

          <!-- body -->
          <path
            d="M66 160 C66 78 128 38 200 38 C272 38 334 78 334 160 L334 340 C334 400 282 432 200 432 C118 432 66 400 66 340 Z"
            fill="url(#mm-body)" style="stroke: var(--mm-line)" stroke-width="5" stroke-linejoin="round"
          />
          <path d="M90 128 Q80 240 90 352" fill="none" style="stroke: var(--mm-line)" stroke-width="3" stroke-linecap="round" opacity="0.5" />
          <path d="M310 128 Q320 240 310 352" fill="none" style="stroke: var(--mm-line)" stroke-width="3" stroke-linecap="round" opacity="0.5" />
          <ellipse cx="128" cy="104" rx="42" ry="20" transform="rotate(-24 128 104)" fill="#fff" opacity="0.8" />
          <g fill="#ffffff" opacity="0.9">
            <circle cx="104" cy="320" r="3" /><circle cx="290" cy="150" r="2.5" /><circle cx="300" cy="360" r="3" />
          </g>
          <g style="fill: var(--mm-line)" opacity="0.7">
            <circle cx="86" cy="200" r="2.5" /><circle cx="316" cy="268" r="2.5" /><circle cx="170" cy="410" r="2.5" /><circle cx="120" cy="388" r="2.5" /><circle cx="226" cy="396" r="2.5" />
          </g>

          <!-- arms (in front of the body, so a raised hand can wave beside her face) -->
          <g class="arm arm-l" :class="`arms-${cfg.arms}`">
            <ellipse cx="52" cy="262" rx="34" ry="17" style="fill: #ffffff; stroke: var(--mm-line)" stroke-width="4" />
          </g>
          <g class="arm arm-r" :class="`arms-${cfg.arms}`">
            <ellipse cx="348" cy="262" rx="34" ry="17" style="fill: #ffffff; stroke: var(--mm-line)" stroke-width="4" />
          </g>

          <!-- girl voice: a bow on her head, in the school's highlight colour, with a yellow button -->
          <g v-if="gender !== 'male'" class="bow">
            <path d="M258 58 C232 30 206 42 214 68 C220 86 246 72 258 62 Z" style="fill: var(--bow); stroke: var(--bow-dark)" stroke-width="3" stroke-linejoin="round" />
            <path d="M268 58 C294 30 322 42 312 68 C306 86 280 72 268 62 Z" style="fill: var(--bow); stroke: var(--bow-dark)" stroke-width="3" stroke-linejoin="round" />
            <ellipse cx="263" cy="60" rx="13" ry="12" style="fill: var(--bow); stroke: var(--bow-dark)" stroke-width="3" />
            <circle cx="263" cy="60" r="5.5" style="fill: var(--c2); stroke: var(--bow-dark)" stroke-width="1.5" />
          </g>
          <!-- boy voice: a bow tie under his chin, in the school's main colour, with a yellow knot -->
          <g v-else class="bowtie">
            <path d="M191 360 C176 348 156 341 139 337 C133 355 133 367 139 385 C156 381 176 373 191 360 Z" style="fill: var(--c1); stroke: var(--ink)" stroke-width="3.5" stroke-linejoin="round" />
            <path d="M209 360 C224 348 244 341 261 337 C267 355 267 367 261 385 C244 381 224 373 209 360 Z" style="fill: var(--c1); stroke: var(--ink)" stroke-width="3.5" stroke-linejoin="round" />
            <path d="M150 347 Q158 361 150 375 M250 347 Q242 361 250 375" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" opacity="0.45" />
            <rect x="187" y="347" width="26" height="26" rx="8" style="fill: var(--c2); stroke: var(--ink)" stroke-width="3.5" />
          </g>

          <!-- face -->
          <g class="face" :key="mood">
            <!-- cheeks -->
            <ellipse cx="116" cy="262" rx="25" ry="16" style="fill: var(--mm-cheek)" :opacity="Math.min(0.9, 0.55 * cfg.cheeks)" />
            <ellipse cx="284" cy="262" rx="25" ry="16" style="fill: var(--mm-cheek)" :opacity="Math.min(0.9, 0.55 * cfg.cheeks)" />

            <!-- eyes -->
            <g v-for="side in [-1, 1]" :key="side" class="eye-shift" :style="{ transform: `translate(${200 + side * 52 + lookX}px, 204px)` }">
              <path v-if="winking && side === 1" d="M-20 8 Q0 -22 20 8" fill="none" style="stroke: var(--ink)" stroke-width="8" stroke-linecap="round" />
              <g v-else-if="cfg.eyes === 'open' || cfg.eyes === 'wide' || cfg.eyes === 'look' || cfg.eyes === 'sad'"
                 class="eye" :class="`eye-${cfg.eyes}`">
                <ellipse :rx="cfg.eyes === 'wide' ? 21 : 18" :ry="cfg.eyes === 'wide' ? 29 : cfg.eyes === 'sad' ? 22 : 25" style="fill: var(--ink)" />
                <circle cx="-6" :cy="cfg.eyes === 'sad' ? -7 : -9" :r="cfg.eyes === 'sad' ? 8 : 6.5" fill="#fff" />
                <circle cx="7" cy="7" r="3" fill="#fff" />
                <ellipse v-if="cfg.eyes === 'sad'" cx="0" cy="15" rx="13" ry="4" fill="#8fd0f0" opacity="0.75" />
              </g>
              <path v-else-if="cfg.eyes === 'happy'" d="M-20 8 Q0 -22 20 8" fill="none" style="stroke: var(--ink)" stroke-width="8" stroke-linecap="round" />
              <path v-else d="M-19 0 Q0 13 19 0" fill="none" style="stroke: var(--ink)" stroke-width="7" stroke-linecap="round" />
            </g>

            <!-- brows -->
            <g fill="none" style="stroke: var(--ink)" stroke-width="5.5" stroke-linecap="round" v-if="cfg.brows !== 'none'">
              <template v-if="cfg.brows === 'raised'">
                <path d="M132 158 Q150 146 168 158" /><path d="M232 158 Q250 146 268 158" />
              </template>
              <template v-else-if="cfg.brows === 'high'">
                <path d="M130 146 Q150 130 170 146" /><path d="M230 146 Q250 130 270 146" />
              </template>
              <template v-else-if="cfg.brows === 'think'">
                <path d="M134 168 L166 162" /><path d="M234 150 Q252 138 268 152" />
              </template>
              <template v-else-if="cfg.brows === 'sad'">
                <path d="M134 176 L168 160" /><path d="M232 160 L266 176" />
              </template>
              <template v-else>
                <path d="M134 154 Q150 144 166 158" /><path d="M234 166 L266 160" />
              </template>
            </g>

            <!-- mouth -->
            <g class="mouth">
              <path v-if="cfg.mouth === 'smile'" d="M168 268 Q200 298 232 268" fill="none" style="stroke: var(--ink)" stroke-width="7" stroke-linecap="round" />
              <ellipse v-else-if="cfg.mouth === 'o'" cx="200" cy="284" rx="11" ry="14" fill="#6b1a3d" />
              <path v-else-if="cfg.mouth === 'hmm'" d="M176 286 Q188 276 200 286 T224 286" fill="none" style="stroke: var(--ink)" stroke-width="6.5" stroke-linecap="round" />
              <path v-else-if="cfg.mouth === 'frown'" d="M170 298 Q200 266 230 298" fill="none" style="stroke: var(--ink)" stroke-width="7" stroke-linecap="round" />
              <path v-else-if="cfg.mouth === 'wavy'" d="M172 286 Q186 272 200 286 T228 286" fill="none" style="stroke: var(--ink)" stroke-width="6.5" stroke-linecap="round" />
              <ellipse v-else-if="cfg.mouth === 'tiny'" cx="200" cy="284" rx="7" ry="6" fill="#6b1a3d" />
              <g v-else-if="cfg.mouth === 'cheer'">
                <path d="M156 262 Q200 270 244 262 Q236 332 200 334 Q164 332 156 262 Z" fill="#6b1a3d" />
                <ellipse cx="200" cy="326" rx="24" ry="14" style="fill: var(--mm-cheek)" clip-path="url(#mm-mouth)" />
              </g>
              <g v-else-if="cfg.mouth === 'talk'">
                <path v-if="!talkPath" d="M170 270 Q200 292 230 270" fill="none" style="stroke: var(--ink)" stroke-width="7" stroke-linecap="round" />
                <template v-else>
                  <path :d="talkPath" fill="#6b1a3d" />
                  <ellipse v-if="level > 0.35" cx="200" :cy="270 + 14 + 56 * level" rx="18" ry="10" style="fill: var(--mm-cheek)" clip-path="url(#mm-talk)" />
                </template>
              </g>
            </g>

            <!-- tears: she is sorry -->
            <g v-if="cfg.fx === 'tears'" class="fx">
              <path class="tear t1" d="M148 236 Q158 252 148 262 Q138 252 148 236 Z" fill="#8fd0f0" stroke="#5bb4de" stroke-width="2.5" />
              <path class="tear t2" d="M252 236 Q262 252 252 262 Q242 252 252 236 Z" fill="#8fd0f0" stroke="#5bb4de" stroke-width="2.5" />
            </g>
            <!-- tears of joy: she is laughing -->
            <g v-if="cfg.fx === 'joy'" class="fx">
              <path class="joy jl" d="M138 218 Q146 230 138 238 Q130 230 138 218 Z" fill="#8fd0f0" stroke="#5bb4de" stroke-width="2.5" />
              <path class="joy jr" d="M262 218 Q270 230 262 238 Q254 230 262 218 Z" fill="#8fd0f0" stroke="#5bb4de" stroke-width="2.5" />
            </g>
          </g>
        </g>
      </g>
    </g>

    <!-- thought bubble -->
    <g v-if="cfg.fx === 'thought'" class="fx thought">
      <circle cx="306" cy="108" r="6" fill="#fff" style="stroke: var(--mm-line)" stroke-width="3" />
      <circle cx="326" cy="86" r="10" fill="#fff" style="stroke: var(--mm-line)" stroke-width="3" />
      <ellipse cx="350" cy="46" rx="46" ry="30" fill="#fff" style="stroke: var(--mm-line)" stroke-width="3" />
      <circle class="d1" cx="330" cy="46" r="6" style="fill: var(--ink)" />
      <circle class="d2" cx="350" cy="46" r="6" style="fill: var(--c3)" />
      <circle class="d3" cx="370" cy="46" r="6" style="fill: var(--c4)" />
    </g>

    <!-- question mark -->
    <text v-if="cfg.fx === 'question'" class="fx qmark" x="334" y="86" font-size="76" text-anchor="middle" style="fill: var(--ink)">?</text>

    <!-- sleepy Zs -->
    <g v-if="cfg.fx === 'zzz'" class="fx zzz" style="fill: var(--ink)" font-weight="700">
      <text class="z1" x="318" y="110" font-size="30">z</text>
      <text class="z2" x="338" y="80" font-size="40">z</text>
      <text class="z3" x="362" y="44" font-size="52">z</text>
    </g>

    <!-- hearts float up when she is thanked -->
    <g v-if="cfg.fx === 'hearts'" class="fx hearts">
      <g v-for="(h, i) in hearts" :key="i" class="heart" :style="{ animationDelay: h.d + 's' }">
        <path :d="HEART" :transform="`translate(${h.x - 12 * h.s} ${h.y - 12 * h.s}) scale(${h.s})`" :style="{ fill: i % 2 ? 'var(--c3)' : 'var(--mm-cheek)' }" stroke="#fff" stroke-width="1.2" />
      </g>
    </g>

    <!-- stars twinkle when she says hello or is amazed -->
    <g v-if="cfg.fx === 'sparkles'" class="fx stars">
      <g v-for="(s, i) in stars" :key="i" class="star" :style="{ animationDelay: s.d + 's' }">
        <path :d="STAR" :transform="`translate(${s.x} ${s.y}) scale(${s.s})`" :style="{ fill: i % 2 ? 'var(--c2)' : 'var(--c4)' }" stroke="#fff" stroke-width="2" />
      </g>
    </g>

    <!-- confetti and sparkles -->
    <g v-if="cfg.fx === 'confetti'" class="fx confetti">
      <g v-for="(c, i) in confetti" :key="i" class="piece"
         :style="{ '--dx': c.dx + 'px', '--dy': c.dy + 'px', '--rot': c.rot + 'deg', animationDelay: c.delay + 's', animationDuration: c.dur + 's' }">
        <circle v-if="c.round" cx="200" cy="130" r="6" :style="{ fill: c.color }" />
        <rect v-else x="195" y="122" width="10" height="16" rx="2" :style="{ fill: c.color }" />
      </g>
      <g class="spark" stroke="#fff" stroke-width="2" style="fill: var(--c2)">
        <path class="s1" d="M40 90 l6 16 l16 6 l-16 6 l-6 16 l-6 -16 l-16 -6 l16 -6 z" />
        <path class="s2" d="M350 120 l5 13 l13 5 l-13 5 l-5 13 l-5 -13 l-13 -5 l13 -5 z" />
        <path class="s3" d="M330 20 l4 10 l10 4 l-10 4 l-4 10 l-4 -10 l-10 -4 l10 -4 z" />
      </g>
    </g>
  </svg>
</template>

<style scoped>
.marshie { width: 100%; height: 100%; overflow: visible; display: block; }
.marshie * { transform-box: view-box; }
.hop, .bob, .tilt { transform-origin: 200px 440px; }
.eye-shift { transition: transform .3s cubic-bezier(.3,1.3,.5,1); }

/* ---- body motion. Each feeling moves differently, so a child can read it without any words.
   .bob squashes and stretches (the bounce), .tilt leans, .hop is for the little surprises. */
.mood-idle .bob       { animation: bounceIdle 1.5s linear infinite; }
.mood-idle .tilt      { animation: sway 3s ease-in-out infinite; }
.mood-idle .shadow    { animation: shadowIdle 1.5s linear infinite; transform-origin: 200px 450px; }
.mood-talking .bob    { animation: bounceTalk .6s linear infinite; }
.mood-talking .tilt   { animation: tiltTalk 1.2s ease-in-out infinite; }
.mood-hello .bob      { animation: bounceIdle .8s linear infinite; }
.mood-hello .tilt     { animation: tiltTalk 1.6s ease-in-out infinite; }
.mood-love .bob       { animation: bounceTalk .9s linear infinite; }
.mood-love .tilt      { animation: tiltLove 1.8s ease-in-out infinite; }
.mood-laugh .bob      { animation: bounceTalk .38s linear infinite; }
.mood-laugh .tilt     { animation: shake .2s linear infinite; }
.mood-wow .bob        { animation: popUp .5s cubic-bezier(.3,1.6,.5,1) both, tremble 1.1s ease-in-out .5s infinite; }
.mood-listening .bob  { animation: listenBob 1.8s ease-in-out infinite; }
.mood-listening .tilt { animation: lean 2.4s ease-in-out infinite; }
.mood-thinking .tilt  { animation: sway 2.8s ease-in-out infinite; }
.mood-thinking .bob   { animation: breathe 2.8s ease-in-out infinite; }
.mood-celebrate .bob  { animation: jump .75s linear infinite; }
.mood-celebrate .tilt { animation: tiltCheer 1.5s ease-in-out infinite; }
.mood-celebrate .shadow { animation: shadowJump .75s linear infinite; transform-origin: 200px 450px; }
.mood-sad .bob        { animation: droop 3.2s ease-in-out infinite; }
.mood-sad .tilt       { animation: wobbleSlow 3.2s ease-in-out infinite; }
.mood-unsure .tilt    { animation: wobble 1.6s ease-in-out infinite; }
.mood-unsure .bob     { animation: breathe 3s ease-in-out infinite; }
.mood-sleepy .bob     { animation: breathe 4.2s ease-in-out infinite; }

/* a bounce has weight: it squashes on the ground, stretches going up, and slows at the top */
@keyframes bounceIdle {
  0%   { transform: translateY(0) scale(1.05, .94); animation-timing-function: cubic-bezier(.2, .7, .4, 1); }
  38%  { transform: translateY(-26px) scale(.97, 1.045); animation-timing-function: cubic-bezier(.6, 0, .8, .3); }
  76%  { transform: translateY(0) scale(1.05, .94); animation-timing-function: ease-out; }
  88%  { transform: translateY(-4px) scale(.99, 1.01); animation-timing-function: ease-in; }
  100% { transform: translateY(0) scale(1.05, .94); }
}
@keyframes shadowIdle { 0%, 76%, 100% { transform: scale(1); opacity: .16 } 38% { transform: scale(.78); opacity: .07 } 88% { transform: scale(.95); opacity: .13 } }
@keyframes bounceTalk {
  0%, 100% { transform: translateY(0) scale(1.03, .97); }
  45%      { transform: translateY(-12px) scale(.985, 1.025); }
}
@keyframes jump {
  0%   { transform: translateY(0) scale(1.08, .9); animation-timing-function: cubic-bezier(.2, .8, .35, 1); }
  40%  { transform: translateY(-62px) scale(.95, 1.07); animation-timing-function: cubic-bezier(.65, 0, .8, .35); }
  78%  { transform: translateY(0) scale(1.08, .9); animation-timing-function: ease-out; }
  100% { transform: translateY(0) scale(1.08, .9); }
}
@keyframes shadowJump { 0%, 78%, 100% { transform: scale(1) } 40% { transform: scale(.6); opacity: .06 } }
@keyframes popUp   { 0% { transform: scale(.9) translateY(6px) } 100% { transform: scale(1.04) translateY(-6px) } }
@keyframes tremble { 0%, 100% { transform: scale(1.04) translateY(-6px) rotate(0) } 25% { transform: scale(1.04) translateY(-8px) rotate(-.8deg) } 75% { transform: scale(1.04) translateY(-6px) rotate(.8deg) } }
@keyframes listenBob { 0%, 100% { transform: translateY(0) scale(1.01, .99) } 50% { transform: translateY(-7px) scale(.995, 1.01) } }
@keyframes sway    { 0%, 100% { transform: rotate(-2.2deg) } 50% { transform: rotate(2.2deg) } }
@keyframes tiltTalk { 0%, 100% { transform: rotate(-3deg) } 50% { transform: rotate(3deg) } }
@keyframes tiltLove { 0%, 100% { transform: rotate(-5deg) } 50% { transform: rotate(5deg) } }
@keyframes tiltCheer { 0%, 100% { transform: rotate(-5deg) } 50% { transform: rotate(5deg) } }
@keyframes shake   { 0%, 100% { transform: rotate(-2.6deg) } 50% { transform: rotate(2.6deg) } }
@keyframes lean    { 0%, 100% { transform: rotate(-4deg) } 50% { transform: rotate(-1.5deg) } }
@keyframes droop   { 0%, 100% { transform: translateY(14px) scale(1.02, .95) } 50% { transform: translateY(16px) scale(1.02, .94) } }
@keyframes wobbleSlow { 0%, 100% { transform: rotate(-1.5deg) } 50% { transform: rotate(1.5deg) } }
@keyframes wobble  { 0%, 100% { transform: rotate(-4deg) } 50% { transform: rotate(5deg) } }
@keyframes breathe { 0%, 100% { transform: translateY(6px) scale(1, .985) } 50% { transform: translateY(6px) scale(1.012, 1) } }

/* ---- idle surprises */
.antic-hop .hop     { animation: hopA .95s linear; }
.antic-wiggle .hop  { animation: wiggleA 1s ease-in-out; }
.antic-twirl .hop   { animation: twirlA 1s ease-in-out; }
@keyframes hopA {
  0%   { transform: translateY(0) scale(1.08, .92); animation-timing-function: cubic-bezier(.2, .8, .35, 1); }
  42%  { transform: translateY(-58px) scale(.95, 1.07); animation-timing-function: cubic-bezier(.65, 0, .8, .35); }
  80%  { transform: translateY(0) scale(1.08, .92); animation-timing-function: ease-out; }
  100% { transform: translateY(0) scale(1, 1); }
}
@keyframes wiggleA { 0%, 100% { transform: rotate(0) } 15% { transform: rotate(-7deg) } 35% { transform: rotate(7deg) } 55% { transform: rotate(-5deg) } 75% { transform: rotate(4deg) } }
@keyframes twirlA {
  0%   { transform: translateY(0) scaleX(1) }
  20%  { transform: translateY(-30px) scaleX(.05) }
  45%  { transform: translateY(-40px) scaleX(-1) }
  70%  { transform: translateY(-20px) scaleX(.05) }
  100% { transform: translateY(0) scaleX(1) }
}
.antic-wave .arm-r.arms-rest { animation: waveR .55s ease-in-out 3; }

/* ---- blinking */
.eye { transform-box: fill-box; transform-origin: center; animation: blink 4.6s infinite; }
.eye-look { transform: translate(9px, -9px); }
.eye-wide { animation: none; }
@keyframes blink { 0%, 93%, 100% { transform: scaleY(1) } 96% { transform: scaleY(.08) } }
.eye-look { animation: none; }

/* ---- arms. Left arms turn clockwise to go up, right arms turn the other way. */
.arm { transition: transform 0.35s cubic-bezier(.3, 1.4, .5, 1); }
.arm-l { transform-origin: 82px 262px; }
.arm-r { transform-origin: 318px 262px; }
.arm-l.arms-rest  { transform: rotate(-16deg) } .arm-r.arms-rest  { transform: rotate(16deg) }
.arm-l.arms-down  { transform: rotate(-42deg) } .arm-r.arms-down  { transform: rotate(42deg) }
.arm-l.arms-chin  { transform: rotate(-16deg) } .arm-r.arms-chin  { transform: rotate(-52deg) }
.arm-l.arms-ear   { transform: rotate(-16deg) } .arm-r.arms-ear   { animation: earR 1.6s ease-in-out infinite }
.arm-l.arms-talk  { animation: gestL 1.1s ease-in-out infinite } .arm-r.arms-talk { animation: gestR 1.1s ease-in-out .35s infinite }
.arm-l.arms-wave  { transform: rotate(-16deg) } .arm-r.arms-wave  { animation: waveR .55s ease-in-out infinite }
.arm-l.arms-hug   { animation: hugL 1.2s ease-in-out infinite } .arm-r.arms-hug { animation: hugR 1.2s ease-in-out infinite }
.arm-l.arms-tummy { animation: tummyL .4s ease-in-out infinite } .arm-r.arms-tummy { animation: tummyR .4s ease-in-out infinite }
.arm-l.arms-wow   { animation: wowL .5s ease-out both } .arm-r.arms-wow { animation: wowR .5s ease-out both }
.arm-l.arms-shrug { animation: shrugL 1.6s ease-in-out infinite } .arm-r.arms-shrug { animation: shrugR 1.6s ease-in-out infinite }
.arm-l.arms-up    { animation: cheerL .75s ease-in-out infinite } .arm-r.arms-up { animation: cheerR .75s ease-in-out infinite }
@keyframes cheerL { 0%, 100% { transform: rotate(62deg) } 50% { transform: rotate(84deg) } }
@keyframes cheerR { 0%, 100% { transform: rotate(-62deg) } 50% { transform: rotate(-84deg) } }
@keyframes waveR  { 0%, 100% { transform: rotate(-95deg) } 50% { transform: rotate(-135deg) } }
@keyframes earR   { 0%, 100% { transform: rotate(-98deg) } 50% { transform: rotate(-90deg) } }
@keyframes gestL  { 0%, 100% { transform: rotate(-16deg) } 50% { transform: rotate(-38deg) } }
@keyframes gestR  { 0%, 100% { transform: rotate(16deg) } 50% { transform: rotate(38deg) } }
@keyframes hugL   { 0%, 100% { transform: rotate(38deg) } 50% { transform: rotate(52deg) } }
@keyframes hugR   { 0%, 100% { transform: rotate(-38deg) } 50% { transform: rotate(-52deg) } }
@keyframes tummyL { 0%, 100% { transform: rotate(-60deg) } 50% { transform: rotate(-70deg) } }
@keyframes tummyR { 0%, 100% { transform: rotate(60deg) } 50% { transform: rotate(70deg) } }
@keyframes wowL   { from { transform: rotate(-16deg) } to { transform: rotate(70deg) } }
@keyframes wowR   { from { transform: rotate(16deg) } to { transform: rotate(-70deg) } }
@keyframes shrugL { 0%, 100% { transform: rotate(-4deg) } 40%, 60% { transform: rotate(34deg) } }
@keyframes shrugR { 0%, 100% { transform: rotate(4deg) } 40%, 60% { transform: rotate(-34deg) } }

.face { animation: pop 0.38s cubic-bezier(.3, 1.5, .5, 1); transform-origin: 200px 240px; }
@keyframes pop { from { transform: scale(.94) } to { transform: scale(1) } }

/* ---- effects */
.waves path { animation: pulse 1.3s ease-in-out infinite; }
.waves .w2 { animation-delay: 0.35s; }
@keyframes pulse { 0%, 100% { opacity: .15 } 50% { opacity: 1 } }

.tear { animation: tear 1.7s ease-in infinite; }
.tear.t2 { animation-delay: 0.7s; }
@keyframes tear { 0% { transform: translateY(0); opacity: 0 } 15% { opacity: 1 } 100% { transform: translateY(78px); opacity: 0 } }
.joy { animation: joyL .55s ease-out infinite; }
.joy.jr { animation-name: joyR; }
@keyframes joyL { 0% { transform: translate(0, 0); opacity: 0 } 20% { opacity: 1 } 100% { transform: translate(-26px, 30px); opacity: 0 } }
@keyframes joyR { 0% { transform: translate(0, 0); opacity: 0 } 20% { opacity: 1 } 100% { transform: translate(26px, 30px); opacity: 0 } }

.thought .d1, .thought .d2, .thought .d3 { animation: dots 1.2s infinite; }
.thought .d2 { animation-delay: 0.2s; } .thought .d3 { animation-delay: 0.4s; }
@keyframes dots { 0%, 100% { opacity: .2 } 40% { opacity: 1 } }

.qmark { font-family: var(--display); animation: qbob 1.6s ease-in-out infinite; transform-origin: 334px 60px; }
@keyframes qbob { 0%, 100% { transform: rotate(-8deg) translateY(0) } 50% { transform: rotate(10deg) translateY(-8px) } }

.zzz text { font-family: var(--display); animation: zfloat 2.8s ease-in-out infinite; }
.zzz .z2 { animation-delay: 0.5s } .zzz .z3 { animation-delay: 1s }
@keyframes zfloat { 0% { opacity: 0; transform: translateY(14px) } 30%, 70% { opacity: 1 } 100% { opacity: 0; transform: translateY(-14px) } }

.heart { animation: floatUp 2.4s ease-in infinite; opacity: 0; transform-box: fill-box; transform-origin: center; }
@keyframes floatUp { 0% { transform: translateY(24px) scale(.5); opacity: 0 } 20% { opacity: 1 } 100% { transform: translateY(-64px) scale(1.15); opacity: 0 } }
.star { animation: twinkleStar 1.1s ease-in-out infinite; transform-box: fill-box; transform-origin: center; }
.star path { transform-box: fill-box; transform-origin: center; }
@keyframes twinkleStar { 0%, 100% { transform: scale(.4) rotate(0); opacity: .3 } 50% { transform: scale(1.1) rotate(25deg); opacity: 1 } }

.piece { transform-origin: 200px 130px; animation: burst 2s ease-out infinite; opacity: 0; }
@keyframes burst {
  0%   { transform: translate(0, 0) rotate(0) scale(.3); opacity: 0 }
  12%  { opacity: 1 }
  100% { transform: translate(var(--dx), var(--dy)) rotate(var(--rot)) scale(1); opacity: 0 }
}
.spark path { transform-box: fill-box; transform-origin: center; animation: twinkle 1s ease-in-out infinite; }
.spark .s2 { animation-delay: .3s } .spark .s3 { animation-delay: .6s }
@keyframes twinkle { 0%, 100% { transform: scale(.5) rotate(0); opacity: .5 } 50% { transform: scale(1.1) rotate(20deg); opacity: 1 } }

@media (prefers-reduced-motion: reduce) {
  .hop, .bob, .tilt, .eye, .arm, .face, .fx *, .shadow, .piece { animation: none !important; }
  .piece, .heart { opacity: 0 !important; }
}
</style>
