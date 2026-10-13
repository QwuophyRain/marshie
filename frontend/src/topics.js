// Tap-to-ask ideas, so a child who doesn't know what to ask can still start straight away.
// Only questions Marshie's built-in knowledge can answer, in each of her four languages (backend/app/data/lang_*.json
// carries the French, Spanish and German answers). Teachers can add more in the Teacher panel.
import { lang as currentLang, t } from './i18n'

const COLOURS = {
  school: { color: 'var(--brand)', fg: '#ffffff' },
  maths: { color: 'var(--gold)' },
  english: { color: 'var(--pink)' },
  science: { color: 'var(--green)' },
  ghana: { color: '#e5484d' },
  arts: { color: '#b18cff' },
  tech: { color: '#5fb8e8' },
  fun: { color: 'var(--pink-deep)', fg: '#ffffff' },
}

const QUESTIONS = {
  en: {
    school: ['What does STEAM stand for?', 'Where is our school?', 'Who is the principal?', 'What clubs does the school have?', 'What sports do we play at school?'],
    maths: ['What is 12 times 7?', 'What is a prime number?', 'How many degrees are in a triangle?', 'What is a fraction?', 'Quiz me'],
    english: ['What is a noun?', 'What is a simile?', 'How do I say good morning in Twi?', 'What is a synonym?'],
    science: ['What is photosynthesis?', 'Why is the sky blue?', 'How many planets are there?', 'What is gravity?'],
    ghana: ['When did Ghana get independence?', 'Who was Yaa Asantewaa?', 'What is kente?', 'What is the Akosombo Dam?'],
    arts: ['What are the primary colours?', 'What is a talking drum?', 'Who painted the Mona Lisa?', 'What is highlife music?'],
    tech: ['What is a Raspberry Pi?', 'What is artificial intelligence?', 'How do I make a strong password?', 'What is coding?'],
    fun: ['Tell me a joke', 'Tell me a riddle', 'Tell me a fun fact', 'Quiz me'],
  },
  fr: {
    school: ['Que veut dire STEAM ?', 'Où est notre école ?', 'Qui est la directrice de l’école ?', 'Quels clubs a l’école ?', 'Quels sports pratique-t-on à l’école ?'],
    maths: ['Combien font 12 fois 7 ?', 'Qu’est-ce qu’un nombre premier ?', 'Combien de degrés y a-t-il dans un triangle ?', 'Qu’est-ce qu’une fraction ?', 'Fais-moi un quiz'],
    english: ['Qu’est-ce qu’un nom ?', 'Qu’est-ce qu’une comparaison ?', 'Comment dit-on bonjour en twi ?', 'Qu’est-ce qu’un synonyme ?'],
    science: ['Qu’est-ce que la photosynthèse ?', 'Pourquoi le ciel est-il bleu ?', 'Combien y a-t-il de planètes ?', 'Qu’est-ce que la gravité ?'],
    ghana: ['Quelle est la capitale du Ghana ?', 'Quand le Ghana est-il devenu indépendant ?', 'Qui était Yaa Asantewaa ?', 'Qu’est-ce que le kente ?', 'Qu’est-ce que le barrage d’Akosombo ?'],
    arts: ['Quelles sont les couleurs primaires ?', 'Qu’est-ce qu’un tambour parlant ?', 'Qui a peint la Joconde ?', 'Qu’est-ce que la musique highlife ?'],
    tech: ['Qu’est-ce qu’un Raspberry Pi ?', 'Qu’est-ce que l’intelligence artificielle ?', 'Comment faire un mot de passe solide ?', 'Qu’est-ce que coder ?'],
    fun: ['Raconte-moi une blague', 'Raconte-moi une devinette', 'Dis-moi un fait amusant', 'Fais-moi un quiz'],
  },
  es: {
    school: ['¿Qué significa STEAM?', '¿Dónde está nuestra escuela?', '¿Quién es la directora de la escuela?', '¿Qué clubes tiene la escuela?', '¿Qué deportes practicamos en la escuela?'],
    maths: ['¿Cuánto es 12 por 7?', '¿Qué es un número primo?', '¿Cuántos grados tiene un triángulo?', '¿Qué es una fracción?', 'Hazme un quiz'],
    english: ['¿Qué es un sustantivo?', '¿Qué es un símil?', '¿Cómo se dice buenos días en twi?', '¿Qué es un sinónimo?'],
    science: ['¿Qué es la fotosíntesis?', '¿Por qué el cielo es azul?', '¿Cuántos planetas hay?', '¿Qué es la gravedad?'],
    ghana: ['¿Cuál es la capital de Ghana?', '¿Cuándo se independizó Ghana?', '¿Quién fue Yaa Asantewaa?', '¿Qué es el kente?', '¿Qué es la presa de Akosombo?'],
    arts: ['¿Cuáles son los colores primarios?', '¿Qué es un tambor parlante?', '¿Quién pintó la Mona Lisa?', '¿Qué es la música highlife?'],
    tech: ['¿Qué es una Raspberry Pi?', '¿Qué es la inteligencia artificial?', '¿Cómo hago una contraseña segura?', '¿Qué es programar?'],
    fun: ['Cuéntame un chiste', 'Dime una adivinanza', 'Dime un dato curioso', 'Hazme un quiz'],
  },
  de: {
    school: ['Wofür steht STEAM?', 'Wo ist unsere Schule?', 'Wer ist die Schulleiterin?', 'Welche Clubs hat die Schule?', 'Welche Sportarten gibt es in der Schule?'],
    maths: ['Wie viel ist 12 mal 7?', 'Was ist eine Primzahl?', 'Wie viele Grad hat ein Dreieck?', 'Was ist ein Bruch?', 'Quiz mit mir'],
    english: ['Was ist ein Nomen?', 'Was ist ein Vergleich?', 'Wie sagt man Guten Morgen auf Twi?', 'Was ist ein Synonym?'],
    science: ['Was ist Photosynthese?', 'Warum ist der Himmel blau?', 'Wie viele Planeten gibt es?', 'Was ist Schwerkraft?'],
    ghana: ['Was ist die Hauptstadt von Ghana?', 'Wann wurde Ghana unabhängig?', 'Wer war Yaa Asantewaa?', 'Was ist Kente?', 'Was ist der Akosombo-Staudamm?'],
    arts: ['Was sind die Grundfarben?', 'Was ist eine Sprechtrommel?', 'Wer hat die Mona Lisa gemalt?', 'Was ist Highlife-Musik?'],
    tech: ['Was ist ein Raspberry Pi?', 'Was ist künstliche Intelligenz?', 'Wie mache ich ein sicheres Passwort?', 'Was ist Programmieren?'],
    fun: ['Erzähl mir einen Witz', 'Erzähl mir ein Rätsel', 'Sag mir einen lustigen Fakt', 'Quiz mit mir'],
  },
}

const STARTER_LIST = {
  en: ['Tell me a joke', 'Quiz me', 'What does STEAM stand for?', 'Tell me about our school'],
  fr: ['Raconte-moi une blague', 'Fais-moi un quiz', 'Que veut dire STEAM ?', 'Parle-moi de notre école'],
  es: ['Cuéntame un chiste', 'Hazme un quiz', '¿Qué significa STEAM?', 'Háblame de nuestra escuela'],
  de: ['Erzähl mir einen Witz', 'Quiz mit mir', 'Wofür steht STEAM?', 'Erzähl mir von unserer Schule'],
}

export const TOPIC_IDS = Object.keys(COLOURS)

/** The seven topics in the language the child picked (call inside a computed or template so it follows the language). */
export function topics(code = currentLang()) {
  return TOPIC_IDS.map((id) => ({
    id, label: t(`topic.${id}`), ...COLOURS[id], questions: QUESTIONS[code][id],
  }))
}
export const starters = (code = currentLang()) => STARTER_LIST[code]

/** Everything a test needs: every tap-to-ask question in every language. */
export const ALL_CHIPS = Object.fromEntries(
  Object.keys(QUESTIONS).map((code) => [code, [...Object.values(QUESTIONS[code]).flat(), ...STARTER_LIST[code]]]),
)
