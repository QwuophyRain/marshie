<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../../api'
import { guard, loadOverview, overview, say, teachPrefill } from '../../composables/useTeacher'

const question = ref('')
const answer = ref('')
const category = ref('')
const keywords = ref('')
const short = ref('')
const lang = ref('en')
const LANGS = [['en', 'English'], ['fr', 'French (Français)'], ['es', 'Spanish (Español)'], ['de', 'German (Deutsch)']]
const saving = ref(false)
const problem = ref('')
const answerBox = ref(null)

const cats = computed(() => {
  const set = new Set(['Arithmetic', 'English', 'Science', 'Ghana History', 'Arts', 'Technology', 'Geography', 'General'])
  Object.keys(overview.value?.stats?.categories || {}).forEach((c) => set.add(c))
  return [...set].sort()
})

onMounted(() => {
  if (teachPrefill.value) {
    question.value = teachPrefill.value
    teachPrefill.value = ''
    answerBox.value?.focus()
  }
})

async function save() {
  problem.value = ''
  if (question.value.trim().length < 3 || answer.value.trim().length < 2) {
    problem.value = 'Write both a question and an answer.'
    return
  }
  saving.value = true
  const res = await guard(() => api.addEntry({
    question: question.value, answer: answer.value, category: category.value.trim() || 'General',
    keywords: keywords.value, short: short.value, lang: lang.value,
  }))
  saving.value = false
  if (!res) return
  if (!res.ok) { problem.value = res.message; return }
  say(res.message)
  question.value = answer.value = keywords.value = short.value = ''
  loadOverview()
}
</script>

<template>
  <form class="tp-section" @submit.prevent="save">
    <h3>Teach Marshie one thing</h3>
    <p class="hint">Marshie will say the answer out loud, so write it the way you would tell a child. Short and friendly works best.</p>
    <div class="tp-block">
      <div>
        <label class="lbl" for="t-q">Question</label>
        <input id="t-q" v-model="question" class="field" type="text" maxlength="300" placeholder="Who is the headteacher of our school?" />
      </div>
      <div>
        <label class="lbl" for="t-a">Answer</label>
        <textarea id="t-a" ref="answerBox" v-model="answer" class="field" rows="3" maxlength="1000"></textarea>
      </div>
      <div>
        <label class="lbl" for="t-lang">Language of the question and answer</label>
        <select id="t-lang" v-model="lang" class="field">
          <option v-for="[code, label] in LANGS" :key="code" :value="code">{{ label }}</option>
        </select>
        <p class="hint">Children who pick French, Spanish or German on the screen get the answers written in that language. Write the question and the answer in the same language.</p>
      </div>
      <div class="tp-row">
        <div>
          <label class="lbl" for="t-c">Subject</label>
          <input id="t-c" v-model="category" class="field" type="text" list="t-cats" placeholder="General" />
          <datalist id="t-cats"><option v-for="c in cats" :key="c" :value="c"></option></datalist>
        </div>
        <div>
          <label class="lbl" for="t-k">Other words that should find it (optional)</label>
          <input id="t-k" v-model="keywords" class="field" type="text" placeholder="head, principal, headmaster" />
        </div>
      </div>
      <div>
        <label class="lbl" for="t-s">Short answer for quizzes (optional)</label>
        <input id="t-s" v-model="short" class="field" type="text" maxlength="80" placeholder="Mrs Mensah" />
        <p class="hint">If you fill this in, Marshie can ask the question in quiz mode and check the answer.</p>
      </div>
      <p v-if="problem" class="tp-note bad" role="alert">{{ problem }}</p>
      <div><button class="btn green" type="submit" :disabled="saving">{{ saving ? 'Saving…' : 'Teach Marshie' }}</button></div>
    </div>
  </form>
</template>
