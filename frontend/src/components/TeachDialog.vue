<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { state, closeTeach, submitTeach, touch } from '../composables/useMarshie'
import { canListen, startListening } from '../composables/useVoice'

const question = ref(state.teach?.question || '')
const answer = ref('')
const name = ref('')
const problem = ref('')
const saving = ref(false)
const dictating = ref(false)
const answerBox = ref(null)
const questionBox = ref(null)
let listener = null

onMounted(() => {
  (question.value ? answerBox : questionBox).value?.focus()
})
onBeforeUnmount(() => listener?.stop())

async function save() {
  problem.value = ''
  if (question.value.trim().length < 3) { problem.value = 'Please write the question first.'; return }
  if (answer.value.trim().length < 2) { problem.value = 'Please write the answer so I can learn it.'; return }
  saving.value = true
  const res = await submitTeach({ question: question.value, answer: answer.value, taught_by: name.value.trim() })
  saving.value = false
  if (!res.ok) problem.value = res.message
}

async function dictate() {
  touch()
  if (dictating.value) { listener?.stop(); return }
  problem.value = ''
  dictating.value = true
  listener = startListening()
  try {
    const heard = await listener.promise
    if (heard) answer.value = (answer.value ? answer.value.trim() + ' ' : '') + heard
    else problem.value = 'I didn’t hear anything. Tap “Say it” and try again.'
  } catch (e) {
    problem.value = e.message
  } finally {
    dictating.value = false
    listener = null
  }
}
</script>

<template>
  <div class="backdrop" @keydown.esc="closeTeach" @pointerdown.self="closeTeach">
    <form class="dialog" role="dialog" aria-modal="true" aria-labelledby="teach-title" @submit.prevent="save" @input="touch">
      <h2 id="teach-title">Teach Marshie</h2>
      <p class="lead">I want to learn! Tell me the right answer and I will remember it.</p>

      <div class="group">
        <label class="lbl" for="teach-q">The question</label>
        <input id="teach-q" ref="questionBox" v-model="question" class="field" type="text" maxlength="300" autocomplete="off" />
      </div>

      <div class="group">
        <label class="lbl" for="teach-a">The right answer</label>
        <textarea id="teach-a" ref="answerBox" v-model="answer" class="field" rows="3" maxlength="1000" placeholder="Write a short, true answer"></textarea>
        <button v-if="canListen()" type="button" class="btn small white say" :class="{ live: dictating }" @click="dictate">
          {{ dictating ? 'Stop' : 'Say it' }}
        </button>
      </div>

      <div class="group">
        <label class="lbl" for="teach-n">Your first name (optional)</label>
        <input id="teach-n" v-model="name" class="field" type="text" maxlength="40" autocomplete="off" />
      </div>

      <p v-if="problem" class="problem" role="alert">{{ problem }}</p>

      <div class="buttons">
        <button type="button" class="btn white" @click="closeTeach">Not now</button>
        <button type="submit" class="btn green" :disabled="saving">{{ saving ? 'Learning…' : 'Teach Marshie' }}</button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.backdrop {
  position: fixed; inset: 0; z-index: 30; display: grid; place-items: center; padding: 1rem;
  background: rgba(2, 35, 45, .55); overflow-y: auto;
}
.dialog {
  width: min(34rem, 100%); background: var(--paper); border: 4px solid var(--ink); border-radius: 32px;
  box-shadow: 0 8px 0 var(--ink); padding: 1.6rem 1.7rem 1.5rem; display: flex; flex-direction: column; gap: 1rem;
}
.dialog h2 { font-size: 2rem; }

/* Keep Marshie's face (her sad "I'm sorry" moment) in view: on wide screens the form sits beside her, on tall ones below. */
@media (min-width: 901px) and (orientation: landscape) {
  .backdrop { place-items: center end; padding-right: 1.4rem; background: linear-gradient(90deg, transparent 28%, rgba(2, 35, 45, .5) 50%); }
  .dialog { width: min(34rem, 52vw); }
}
@media (max-width: 900px), (orientation: portrait) {
  .backdrop { place-items: end center; background: linear-gradient(180deg, transparent 20%, rgba(2, 35, 45, .55) 45%); }
}
.lead { font-size: 1.1rem; }
.group { position: relative; }
.say { position: absolute; right: .5rem; bottom: .55rem; min-height: 2.1rem; padding: .2rem .8rem; }
.say.live { background: var(--berry); color: #fff; }
textarea.field { padding-bottom: 2.9rem; }
.problem { color: #a2252a; font-weight: 700; }
.buttons { display: flex; justify-content: flex-end; gap: .8rem; flex-wrap: wrap; margin-top: .3rem; }
</style>
