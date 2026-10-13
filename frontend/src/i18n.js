// Every word a child sees or hears from the screen itself, in English, French, Spanish and German.
// (What Marshie ANSWERS comes from the server; the greeting, quiz lines and buttons live here.)
// `t('key', { name })` is reactive: it reads settings.language, so the whole screen changes when a child picks a language.
import { settings } from './settings'

export const LANGUAGES = {
  en: { code: 'en', native: 'English', english: 'English', speech: 'en-US' },
  fr: { code: 'fr', native: 'Français', english: 'French', speech: 'fr-FR' },
  es: { code: 'es', native: 'Español', english: 'Spanish', speech: 'es-ES' },
  de: { code: 'de', native: 'Deutsch', english: 'German', speech: 'de-DE' },
}
export const LANGUAGE_LIST = Object.values(LANGUAGES)

export const lang = () => (LANGUAGES[settings.language] ? settings.language : 'en')

const S = {
  // ---- how Marshie looks while she feels something
  'cap.idle': { en: 'Hi! Ask me anything.', fr: 'Salut ! Pose-moi une question.', es: '¡Hola! Pregúntame lo que quieras.', de: 'Hallo! Frag mich etwas.' },
  'cap.listening': { en: 'I’m listening…', fr: 'Je t’écoute…', es: 'Te escucho…', de: 'Ich höre zu …' },
  'cap.thinking': { en: 'Let me think…', fr: 'Laisse-moi réfléchir…', es: 'Déjame pensar…', de: 'Lass mich überlegen …' },
  'cap.talking': { en: 'Here’s what I know!', fr: 'Voilà ce que je sais !', es: '¡Esto es lo que sé!', de: 'Das weiß ich!' },
  'cap.hello': { en: 'Hello, friend!', fr: 'Bonjour, mon ami !', es: '¡Hola, amigo!', de: 'Hallo, Freund!' },
  'cap.love': { en: 'Aww, thank you!', fr: 'Oh, merci !', es: '¡Ay, gracias!', de: 'Oh, danke!' },
  'cap.laugh': { en: 'Hehe!', fr: 'Hihi !', es: '¡Jeje!', de: 'Hihi!' },
  'cap.wow': { en: 'Wow!', fr: 'Waouh !', es: '¡Guau!', de: 'Wow!' },
  'cap.celebrate': { en: 'Yay!', fr: 'Hourra !', es: '¡Hurra!', de: 'Juhu!' },
  'cap.sad': { en: 'Oh no, I’m sorry!', fr: 'Oh non, je suis désolée !', es: '¡Oh no, lo siento!', de: 'Oh nein, das tut mir leid!' },
  'cap.sad.m': { en: 'Oh no, I’m sorry!', fr: 'Oh non, je suis désolé !', es: '¡Oh no, lo siento!', de: 'Oh nein, das tut mir leid!' },
  'cap.unsure': { en: 'Hmm…', fr: 'Hmm…', es: 'Mmm…', de: 'Hmm …' },
  'cap.sleepy': { en: 'Zzz… tap to wake me', fr: 'Zzz… réveille-moi', es: 'Zzz… despiértame', de: 'Zzz … weck mich auf' },
  'cap.asleep': { en: 'Zzz… I’m sleeping', fr: 'Zzz… je dors', es: 'Zzz… estoy durmiendo', de: 'Zzz … ich schlafe' },
  'face.aria': { en: '{name} the marshmallow', fr: '{name}, la guimauve', es: '{name}, el malvavisco', de: '{name}, das Marshmallow' },
  'face.wake': { en: 'Wake {name} up', fr: 'Réveiller {name}', es: 'Despertar a {name}', de: '{name} aufwecken' },
  'face.tickle': { en: 'Tickle {name}', fr: 'Chatouiller {name}', es: 'Hacerle cosquillas a {name}', de: '{name} kitzeln' },

  // ---- the sleeping screen
  'wake.title': { en: 'Hello, friend!', fr: 'Bonjour, mon ami !', es: '¡Hola, amigo!', de: 'Hallo, Freund!' },
  'wake.intro': {
    en: 'I’m {name}, the helper for the {school} {event}. Ask me about maths, science, Ghana, art and lots more.',
    fr: 'Je suis {name}, l’assistante de {school} pour {event}. Pose-moi des questions sur les maths, les sciences, le Ghana, l’art et bien plus.',
    es: 'Soy {name}, la ayudante de {school} para {event}. Pregúntame sobre matemáticas, ciencias, Ghana, arte y mucho más.',
    de: 'Ich bin {name}, die Helferin von {school} für {event}. Frag mich nach Mathe, Naturwissenschaften, Ghana, Kunst und vielem mehr.',
  },
  'wake.intro.m': {
    en: 'I’m {name}, the helper for the {school} {event}. Ask me about maths, science, Ghana, art and lots more.',
    fr: 'Je suis {name}, l’assistant de {school} pour {event}. Pose-moi des questions sur les maths, les sciences, le Ghana, l’art et bien plus.',
    es: 'Soy {name}, el ayudante de {school} para {event}. Pregúntame sobre matemáticas, ciencias, Ghana, arte y mucho más.',
    de: 'Ich bin {name}, der Helfer von {school} für {event}. Frag mich nach Mathe, Naturwissenschaften, Ghana, Kunst und vielem mehr.',
  },
  'wake.button': { en: 'Wake {name} up', fr: 'Réveiller {name}', es: 'Despertar a {name}', de: '{name} aufwecken' },
  'wake.hint': { en: 'You can talk to me or type to me.', fr: 'Tu peux me parler ou m’écrire.', es: 'Puedes hablarme o escribirme.', de: 'Du kannst mit mir sprechen oder mir schreiben.' },
  'wake.language': { en: 'Choose a language', fr: 'Choisis une langue', es: 'Elige un idioma', de: 'Wähle eine Sprache' },
  'greeting.fallback': {
    en: 'Hello! My name is {name}, your friendly educative chatbot for the {school} STEAM (Science, Technology, English, Agriculture & Arts, and Mathematics) Program 2026. How may I be of assistance?',
    fr: 'Bonjour ! Je m’appelle {name}, ton chatbot éducatif et amical pour le programme STEAM 2026 à {school} (Sciences, Technologie, Anglais, Agriculture et Arts, et Mathématiques). Comment puis-je t’aider ?',
    es: '¡Hola! Me llamo {name}, tu chatbot educativo y amigable para el Programa STEAM 2026 de {school} (Ciencias, Tecnología, Inglés, Agricultura y Artes, y Matemáticas). ¿En qué puedo ayudarte?',
    de: 'Hallo! Ich heiße {name}, dein freundlicher Lern-Chatbot für das STEAM-Programm 2026 der {school} (Naturwissenschaften, Technologie, Englisch, Landwirtschaft und Kunst sowie Mathematik). Wie kann ich dir helfen?',
  },

  // ---- the small menu box
  'menu.open': { en: 'Menu', fr: 'Menu', es: 'Menú', de: 'Menü' },
  'menu.close': { en: 'Close', fr: 'Fermer', es: 'Cerrar', de: 'Schließen' },
  'menu.back': { en: 'Back', fr: 'Retour', es: 'Atrás', de: 'Zurück' },
  'menu.language': { en: 'Language', fr: 'Langue', es: 'Idioma', de: 'Sprache' },
  'menu.ask': { en: 'Ask me about', fr: 'Pose-moi des questions sur', es: 'Pregúntame sobre', de: 'Frag mich zu' },
  'menu.how': { en: 'How to use me', fr: 'Comment m’utiliser', es: 'Cómo usarme', de: 'So geht’s' },
  'menu.voice': { en: 'Voice', fr: 'Voix', es: 'Voz', de: 'Stimme' },
  'voice.girl': { en: 'Girl', fr: 'Fille', es: 'Niña', de: 'Mädchen' },
  'voice.boy': { en: 'Boy', fr: 'Garçon', es: 'Niño', de: 'Junge' },
  'voice.girlNote': { en: 'a bow on her head', fr: 'un nœud sur la tête', es: 'un lazo en la cabeza', de: 'eine Schleife auf dem Kopf' },
  'voice.boyNote': { en: 'a bow tie on his neck', fr: 'un nœud papillon au cou', es: 'una pajarita en el cuello', de: 'eine Fliege am Hals' },
  'menu.soundOn': { en: 'Sound on', fr: 'Son activé', es: 'Sonido activado', de: 'Ton an' },
  'menu.soundOff': { en: 'Sound off', fr: 'Son coupé', es: 'Sonido apagado', de: 'Ton aus' },
  'menu.fullscreen': { en: 'Full screen', fr: 'Plein écran', es: 'Pantalla completa', de: 'Vollbild' },
  'menu.fullscreenExit': { en: 'Exit full screen', fr: 'Quitter le plein écran', es: 'Salir de pantalla completa', de: 'Vollbild beenden' },
  'menu.history': { en: 'What we said', fr: 'Notre conversation', es: 'Nuestra conversación', de: 'Unser Gespräch' },
  'menu.fresh': { en: 'Start fresh', fr: 'Recommencer', es: 'Empezar de nuevo', de: 'Neu anfangen' },
  'menu.teachers': { en: 'Teachers', fr: 'Enseignants', es: 'Profesores', de: 'Lehrer' },
  'menu.howList': {
    en: [
      'Tap Talk with me and speak. I listen and answer out loud.',
      'Or type a question and press Send.',
      'Tap my face and I giggle.',
      'Say “quiz me” to play a quiz.',
      'If I get something wrong, tap That’s wrong and teach me.',
    ],
    fr: [
      'Touche « Parle avec moi » et parle. J’écoute et je réponds à voix haute.',
      'Ou écris une question et touche Envoyer.',
      'Touche mon visage et je rigole.',
      'Dis « fais-moi un quiz » pour jouer.',
      'Si je me trompe, touche C’est faux et apprends-moi la réponse.',
    ],
    es: [
      'Toca «Habla conmigo» y habla. Te escucho y respondo en voz alta.',
      'O escribe una pregunta y toca Enviar.',
      'Toca mi cara y me da la risa.',
      'Di «hazme un quiz» para jugar.',
      'Si me equivoco, toca Está mal y enséñame la respuesta.',
    ],
    de: [
      'Tippe auf „Sprich mit mir“ und sprich. Ich höre zu und antworte laut.',
      'Oder schreib eine Frage und tippe auf Senden.',
      'Tippe auf mein Gesicht, dann kichere ich.',
      'Sag „Quiz mit mir“, um ein Quiz zu spielen.',
      'Wenn ich mich irre, tippe auf Das ist falsch und bring mir die Antwort bei.',
    ],
  },

  // ---- the seven topics
  'topic.school': { en: 'Our School', fr: 'Notre école', es: 'Nuestra escuela', de: 'Unsere Schule' },
  'topic.maths': { en: 'Maths', fr: 'Maths', es: 'Matemáticas', de: 'Mathe' },
  'topic.english': { en: 'English', fr: 'Langue', es: 'Lengua', de: 'Sprache' },
  'topic.science': { en: 'Science', fr: 'Sciences', es: 'Ciencias', de: 'Wissen' },
  'topic.ghana': { en: 'Ghana', fr: 'Ghana', es: 'Ghana', de: 'Ghana' },
  'topic.arts': { en: 'Arts', fr: 'Arts', es: 'Artes', de: 'Kunst' },
  'topic.tech': { en: 'Tech', fr: 'Technologie', es: 'Tecnología', de: 'Technik' },
  'topic.fun': { en: 'Fun', fr: 'Jeux', es: 'Juegos', de: 'Spaß' },

  // ---- the bottom bar
  'talk.start': { en: 'Talk with me', fr: 'Parle avec moi', es: 'Habla conmigo', de: 'Sprich mit mir' },
  'talk.stop': { en: 'Stop talking', fr: 'Arrêter', es: 'Parar', de: 'Beenden' },
  'talk.hintOff': {
    en: 'Press the button and we can chat out loud. No tapping needed.',
    fr: 'Appuie sur le bouton et on discute à voix haute, sans rien toucher.',
    es: 'Pulsa el botón y charlamos en voz alta, sin tocar nada.',
    de: 'Drück den Knopf, dann plaudern wir laut, ganz ohne Tippen.',
  },
  'talk.hintListening': { en: 'I’m listening. Just talk to me.', fr: 'Je t’écoute. Parle-moi.', es: 'Te escucho. Solo háblame.', de: 'Ich höre zu. Sprich einfach.' },
  'talk.hintThinking': { en: 'Thinking…', fr: 'Je réfléchis…', es: 'Pensando…', de: 'Ich überlege …' },
  'talk.hintSpeaking': {
    en: 'Tap {name} to stop her and speak.', fr: 'Touche {name} pour l’arrêter et parler.',
    es: 'Toca a {name} para pararla y hablar.', de: 'Tippe auf {name}, damit sie aufhört und du sprechen kannst.',
  },
  'talk.hintSpeaking.m': {
    en: 'Tap {name} to stop him and speak.', fr: 'Touche {name} pour l’arrêter et parler.',
    es: 'Toca a {name} para pararlo y hablar.', de: 'Tippe auf {name}, damit er aufhört und du sprechen kannst.',
  },
  'talk.hintWait': { en: 'One moment…', fr: 'Un instant…', es: 'Un momento…', de: 'Einen Moment …' },
  'dock.placeholder': { en: 'Type your question', fr: 'Écris ta question', es: 'Escribe tu pregunta', de: 'Schreib deine Frage' },
  'dock.placeholderQuiz': { en: 'Type your answer', fr: 'Écris ta réponse', es: 'Escribe tu respuesta', de: 'Schreib deine Antwort' },
  'dock.question': { en: 'Your question', fr: 'Ta question', es: 'Tu pregunta', de: 'Deine Frage' },
  'dock.answer': { en: 'Your answer', fr: 'Ta réponse', es: 'Tu respuesta', de: 'Deine Antwort' },
  'dock.send': { en: 'Send', fr: 'Envoyer', es: 'Enviar', de: 'Senden' },
  'mic.ask': {
    en: 'Tap and ask {name} a question', fr: 'Touche et pose une question à {name}',
    es: 'Toca y hazle una pregunta a {name}', de: 'Tippe und stell {name} eine Frage',
  },
  'mic.stop': { en: 'Stop listening', fr: 'Arrêter l’écoute', es: 'Dejar de escuchar', de: 'Zuhören beenden' },
  'mic.stopShort': { en: 'Stop', fr: 'Stop', es: 'Parar', de: 'Stopp' },
  'mic.cantListen': {
    en: 'This browser can’t listen yet, so please type your question.',
    fr: 'Ce navigateur ne peut pas encore écouter, alors écris ta question.',
    es: 'Este navegador todavía no puede escuchar, así que escribe tu pregunta.',
    de: 'Dieser Browser kann noch nicht zuhören, bitte schreib deine Frage.',
  },
  'mic.cantListenLang': {
    en: 'I can’t listen to this language here yet. Please type your question.',
    fr: 'Je ne peux pas encore écouter le français ici. Écris ta question.',
    es: 'Todavía no puedo escuchar español aquí. Escribe tu pregunta.',
    de: 'Deutsch kann ich hier noch nicht hören. Bitte schreib deine Frage.',
  },
  'mic.needSecure': {
    en: 'The microphone needs the address http://localhost:8000 (or HTTPS). You can type for now.',
    fr: 'Le micro demande l’adresse http://localhost:8000 (ou HTTPS). Tu peux écrire en attendant.',
    es: 'El micrófono necesita la dirección http://localhost:8000 (o HTTPS). Mientras tanto puedes escribir.',
    de: 'Das Mikrofon braucht die Adresse http://localhost:8000 (oder HTTPS). Du kannst solange tippen.',
  },
  'mic.listeningHint': {
    en: 'I’m listening. Say your question, then wait a moment.', fr: 'Je t’écoute. Dis ta question, puis attends un instant.',
    es: 'Te escucho. Di tu pregunta y espera un momento.', de: 'Ich höre zu. Sag deine Frage und warte kurz.',
  },
  'quiz.bar': {
    en: 'Quiz time. You have {score} right out of {total}.', fr: 'C’est l’heure du quiz. Score : {score} sur {total}.',
    es: 'Hora del quiz. Aciertos: {score} de {total}.', de: 'Quizzeit! Richtig: {score} von {total}.',
  },
  'quiz.barShort': { en: 'Quiz: {score} / {total}', fr: 'Quiz : {score} / {total}', es: 'Quiz: {score} / {total}', de: 'Quiz: {score} / {total}' },
  'quiz.stop': { en: 'Stop quiz', fr: 'Arrêter le quiz', es: 'Terminar el quiz', de: 'Quiz beenden' },

  // ---- what she says in a quiz
  'quiz.lets': { en: 'Let’s play! {q}', fr: 'On joue ! {q}', es: '¡A jugar! {q}', de: 'Los geht’s! {q}' },
  'quiz.yes': {
    en: ['Yes! That’s right!', 'Brilliant! You got it!', 'Hooray, correct!'],
    fr: ['Oui ! C’est juste !', 'Génial ! Tu as trouvé !', 'Hourra, c’est correct !'],
    es: ['¡Sí! ¡Correcto!', '¡Genial! ¡Lo lograste!', '¡Hurra, es correcto!'],
    de: ['Ja! Das stimmt!', 'Super! Du hast es geschafft!', 'Hurra, richtig!'],
  },
  'quiz.notQuite': { en: 'Not quite.', fr: 'Pas tout à fait.', es: 'No exactamente.', de: 'Nicht ganz.' },
  'quiz.answerIs': { en: 'The answer is: {a}', fr: 'La réponse est : {a}', es: 'La respuesta es: {a}', de: 'Die Antwort ist: {a}' },
  'quiz.end': {
    en: 'Quiz finished! You got {score} out of {total}.', fr: 'Quiz terminé ! Tu as eu {score} sur {total}.',
    es: '¡Quiz terminado! Acertaste {score} de {total}.', de: 'Quiz beendet! Du hast {score} von {total} richtig.',
  },
  'quiz.well': { en: 'Well done!', fr: 'Bravo !', es: '¡Bien hecho!', de: 'Gut gemacht!' },
  'quiz.tryAgain': {
    en: 'Good try! Let’s practise again soon.', fr: 'Bien essayé ! On s’entraîne encore bientôt.',
    es: '¡Buen intento! Practiquemos otra vez pronto.', de: 'Guter Versuch! Wir üben bald wieder.',
  },
  'quiz.later': {
    en: 'Okay, we can play another time!', fr: 'D’accord, on jouera une autre fois !',
    es: '¡Vale, jugamos otro día!', de: 'Okay, wir spielen ein andermal!',
  },

  // ---- talking back and forth
  'convo.stopLong': {
    en: 'Okay, I’ll stop listening. Tap Talk with me whenever you want to chat again.',
    fr: 'D’accord, j’arrête d’écouter. Touche « Parle avec moi » quand tu veux rediscuter.',
    es: 'Vale, dejo de escuchar. Toca «Habla conmigo» cuando quieras charlar otra vez.',
    de: 'Okay, ich höre nicht mehr zu. Tippe auf „Sprich mit mir“, wenn du wieder plaudern möchtest.',
  },
  'convo.stopShort': { en: 'Okay, I’ll stop listening.', fr: 'D’accord, j’arrête d’écouter.', es: 'Vale, dejo de escuchar.', de: 'Okay, ich höre nicht mehr zu.' },
  'convo.bye': {
    en: 'Goodbye! It was lovely talking with you. Come and chat again soon.',
    fr: 'Au revoir ! C’était un plaisir de discuter avec toi. Reviens bientôt !',
    es: '¡Adiós! Fue un placer hablar contigo. ¡Vuelve pronto!',
    de: 'Tschüss! Es war schön, mit dir zu plaudern. Komm bald wieder!',
  },
  'convo.rest': {
    en: 'I’ll take a little rest now. Tap Talk with me when you want to chat again.',
    fr: 'Je me repose un peu. Touche « Parle avec moi » pour rediscuter.',
    es: 'Voy a descansar un poquito. Toca «Habla conmigo» para charlar otra vez.',
    de: 'Ich ruhe mich jetzt kurz aus. Tippe auf „Sprich mit mir“, wenn du wieder plaudern möchtest.',
  },
  'convo.stillThere': {
    en: 'Are you still there? Just talk to me, or tap Stop.', fr: 'Tu es toujours là ? Parle-moi, ou touche Arrêter.',
    es: '¿Sigues ahí? Háblame o toca Parar.', de: 'Bist du noch da? Sprich mit mir oder tippe auf Beenden.',
  },
  'listen.nothing': {
    en: 'I didn’t hear anything. Tap the microphone and try again.', fr: 'Je n’ai rien entendu. Touche le micro et réessaie.',
    es: 'No he oído nada. Toca el micrófono e inténtalo otra vez.', de: 'Ich habe nichts gehört. Tippe auf das Mikrofon und versuch es nochmal.',
  },
  'listen.nothingSpoken': {
    en: 'I didn’t hear anything. Tap the microphone and try again, or type your question.',
    fr: 'Je n’ai rien entendu. Touche le micro et réessaie, ou écris ta question.',
    es: 'No he oído nada. Toca el micrófono e inténtalo otra vez, o escribe tu pregunta.',
    de: 'Ich habe nichts gehört. Tippe auf das Mikrofon und versuch es nochmal, oder schreib deine Frage.',
  },

  // ---- under an answer
  'msg.right': { en: 'That’s right', fr: 'C’est juste', es: 'Está bien', de: 'Das stimmt' },
  'msg.wrong': { en: 'That’s wrong', fr: 'C’est faux', es: 'Está mal', de: 'Das ist falsch' },
  'msg.thanks': { en: 'Thank you for telling me!', fr: 'Merci de me l’avoir dit !', es: '¡Gracias por decírmelo!', de: 'Danke, dass du es mir sagst!' },
  'msg.teach': {
    en: 'Teach {name} the answer', fr: 'Apprends la réponse à {name}',
    es: 'Enséñale la respuesta a {name}', de: 'Bring {name} die Antwort bei',
  },
  'msg.didYouMean': { en: 'Did you mean “{q}”?', fr: 'Voulais-tu dire « {q} » ?', es: '¿Querías decir «{q}»?', de: 'Meintest du „{q}“?' },
  'msg.picture': { en: 'Open the picture: {title}', fr: 'Ouvrir l’image : {title}', es: 'Abrir la imagen: {title}', de: 'Bild öffnen: {title}' },
  'msg.you': { en: 'You', fr: 'Toi', es: 'Tú', de: 'Du' },
  'msg.thinkingAria': { en: '{name} is thinking', fr: '{name} réfléchit', es: '{name} está pensando', de: '{name} überlegt' },
  'msg.chatAria': { en: 'Chat with {name}', fr: 'Conversation avec {name}', es: 'Conversación con {name}', de: 'Gespräch mit {name}' },
  'history.empty': { en: 'Nothing yet. Say hello!', fr: 'Rien pour l’instant. Dis bonjour !', es: 'Todavía nada. ¡Saluda!', de: 'Noch nichts. Sag Hallo!' },

  // ---- the "teach me" form
  'teach.title': { en: 'Teach {name}', fr: 'Apprendre à {name}', es: 'Enseñar a {name}', de: '{name} etwas beibringen' },
  'teach.lead': {
    en: 'I want to learn! Tell me the right answer and I will remember it.', fr: 'Je veux apprendre ! Donne-moi la bonne réponse et je m’en souviendrai.',
    es: '¡Quiero aprender! Dime la respuesta correcta y la recordaré.', de: 'Ich will lernen! Sag mir die richtige Antwort und ich merke sie mir.',
  },
  'teach.q': { en: 'The question', fr: 'La question', es: 'La pregunta', de: 'Die Frage' },
  'teach.a': { en: 'The right answer', fr: 'La bonne réponse', es: 'La respuesta correcta', de: 'Die richtige Antwort' },
  'teach.aPlaceholder': {
    en: 'Write a short, true answer', fr: 'Écris une réponse courte et vraie',
    es: 'Escribe una respuesta corta y verdadera', de: 'Schreib eine kurze, wahre Antwort',
  },
  'teach.name': { en: 'Your first name (optional)', fr: 'Ton prénom (facultatif)', es: 'Tu nombre (opcional)', de: 'Dein Vorname (freiwillig)' },
  'teach.sayIt': { en: 'Say it', fr: 'Dis-le', es: 'Dilo', de: 'Sag es' },
  'teach.needQ': { en: 'Please write the question first.', fr: 'Écris d’abord la question.', es: 'Escribe primero la pregunta.', de: 'Bitte schreib zuerst die Frage.' },
  'teach.needA': {
    en: 'Please write the answer so I can learn it.', fr: 'Écris la réponse pour que je l’apprenne.',
    es: 'Escribe la respuesta para que pueda aprenderla.', de: 'Bitte schreib die Antwort, damit ich sie lernen kann.',
  },
  'teach.noHear': {
    en: 'I didn’t hear anything. Tap “Say it” and try again.', fr: 'Je n’ai rien entendu. Touche « Dis-le » et réessaie.',
    es: 'No he oído nada. Toca «Dilo» e inténtalo otra vez.', de: 'Ich habe nichts gehört. Tippe auf „Sag es“ und versuch es nochmal.',
  },
  'teach.notNow': { en: 'Not now', fr: 'Pas maintenant', es: 'Ahora no', de: 'Jetzt nicht' },
  'teach.save': { en: 'Teach {name}', fr: 'Apprendre à {name}', es: 'Enseñar a {name}', de: '{name} beibringen' },
  'teach.saving': { en: 'Learning…', fr: 'J’apprends…', es: 'Aprendiendo…', de: 'Ich lerne …' },

  // ---- when something goes wrong
  'err.offline': {
    en: 'I can’t reach my brain right now. Is the server running?', fr: 'Je n’arrive pas à joindre mon cerveau. Le serveur est-il lancé ?',
    es: 'No puedo conectar con mi cerebro ahora mismo. ¿Está funcionando el servidor?', de: 'Ich erreiche mein Gehirn gerade nicht. Läuft der Server?',
  },
  'err.generic': { en: 'Something went wrong ({status}).', fr: 'Quelque chose s’est mal passé ({status}).', es: 'Algo salió mal ({status}).', de: 'Etwas ist schiefgelaufen ({status}).' },
  'err.micServer': {
    en: 'I need to use the microphone. Please allow it, then tap the microphone again.',
    fr: 'J’ai besoin du micro. Autorise-le, puis touche à nouveau le micro.',
    es: 'Necesito usar el micrófono. Permítelo y toca otra vez el micrófono.',
    de: 'Ich brauche das Mikrofon. Erlaube es bitte und tippe dann nochmal auf das Mikrofon.',
  },
  'err.micBrowser': {
    en: 'I need to use the microphone. Please allow it in the browser, then try again. (Teachers: Teachers, Voice and screen, Listening has help.)',
    fr: 'J’ai besoin du micro. Autorise-le dans le navigateur, puis réessaie. (Teachers: Teachers, Voice and screen, Listening has help.)',
    es: 'Necesito usar el micrófono. Permítelo en el navegador y vuelve a intentarlo. (Teachers: Teachers, Voice and screen, Listening has help.)',
    de: 'Ich brauche das Mikrofon. Erlaube es bitte im Browser und versuch es nochmal. (Teachers: Teachers, Voice and screen, Listening has help.)',
  },
  'err.listenBroken': {
    en: 'Listening is not working in this browser, but it is not your internet. Please type your question. (Teachers: open Teachers, Voice and screen, Listening to fix it.)',
    fr: 'L’écoute ne marche pas dans ce navigateur, mais ce n’est pas ton internet. Écris ta question. (Teachers: open Teachers, Voice and screen, Listening to fix it.)',
    es: 'La escucha no funciona en este navegador, pero no es tu internet. Escribe tu pregunta. (Teachers: open Teachers, Voice and screen, Listening to fix it.)',
    de: 'Das Zuhören funktioniert in diesem Browser nicht, aber es liegt nicht am Internet. Bitte schreib deine Frage. (Teachers: open Teachers, Voice and screen, Listening to fix it.)',
  },
  'err.couldntHear': {
    en: 'I couldn’t hear that. Please try again or type your question.', fr: 'Je n’ai pas bien entendu. Réessaie ou écris ta question.',
    es: 'No lo he oído bien. Inténtalo otra vez o escribe tu pregunta.', de: 'Das habe ich nicht verstanden. Versuch es nochmal oder schreib deine Frage.',
  },
  'err.couldntStart': {
    en: 'I couldn’t start listening. Please try again.', fr: 'Je n’ai pas pu commencer à écouter. Réessaie.',
    es: 'No pude empezar a escuchar. Inténtalo otra vez.', de: 'Ich konnte nicht anfangen zuzuhören. Versuch es nochmal.',
  },
  'err.noMic': {
    en: 'This browser can’t use a microphone. Please type your question.', fr: 'Ce navigateur ne peut pas utiliser de micro. Écris ta question.',
    es: 'Este navegador no puede usar un micrófono. Escribe tu pregunta.', de: 'Dieser Browser kann kein Mikrofon benutzen. Bitte schreib deine Frage.',
  },
  'err.insecure': {
    en: 'The microphone only works on a secure address. Open Marshie at http://localhost:8000 on this computer, or ask your teacher to enable HTTPS.',
    fr: 'Le micro ne marche que sur une adresse sécurisée. Ouvre Marshie sur http://localhost:8000 sur cet ordinateur, ou demande à ton enseignant d’activer HTTPS.',
    es: 'El micrófono solo funciona en una dirección segura. Abre Marshie en http://localhost:8000 en este ordenador, o pide a tu profesor que active HTTPS.',
    de: 'Das Mikrofon funktioniert nur auf einer sicheren Adresse. Öffne Marshie auf diesem Computer unter http://localhost:8000 oder bitte deine Lehrkraft, HTTPS einzuschalten.',
  },
}

const fill = (s, vars) => s.replace(/\{(\w+)\}/g, (m, k) => (vars && vars[k] !== undefined ? vars[k] : m))

/** The text for `key` in the language the child picked. Lists (instructions, cheers) come back as lists. */
export function t(key, vars) {
  const row = (settings.voiceGender === 'male' && S[`${key}.m`]) || S[key]
  if (!row) return key
  const v = row[lang()] ?? row.en
  return Array.isArray(v) ? v : fill(v, vars)
}
/** The same, in a language of your choice (used when the language is not the current one). */
export const tIn = (code, key, vars) => {
  const row = (settings.voiceGender === 'male' && S[`${key}.m`]) || S[key]
  if (!row) return key
  const v = row[code] ?? row.en
  return Array.isArray(v) ? v : fill(v, vars)
}

/** Every key, so a test can check each one is written in all four languages. */
export const ALL_KEYS = Object.keys(S)
export const TABLE = S

// ---- the words that end a hands-free chat, per language (after plain(): lower case, no accents, no apostrophes)
export const STOP_WORDS = {
  en: /^(stop|stop listening|stop talking|be quiet|quiet|enough|cancel|pause|end|quit|exit)$/,
  fr: /^(stop|stoppe|arrete|arrete toi|arrete decouter|arrete de parler|tais toi|silence|ca suffit|assez|annule|pause|fin|quitter|termine)$/,
  es: /^(stop|para|parar|basta|silencio|callate|cancelar|cancela|pausa|fin|salir|termina|deja de escuchar|deja de hablar)$/,
  de: /^(stopp|stop|halt|hor auf|aufhoren|ruhe|sei still|genug|abbrechen|pause|ende|beenden|schluss)$/,
}
export const BYE_WORDS = {
  en: /^(bye|bye bye|goodbye|good bye|see you|see you later|see you soon|that is all|that is it|i am done|we are done|good night|thats all|i have to go)$/,
  fr: /^(au revoir|aurevoir|bye|bye bye|ciao|a bientot|a plus tard|a plus|a demain|bonne nuit|bonne journee|cest tout|jai fini|on a fini|je dois partir|je dois y aller)$/,
  es: /^(adios|hasta luego|hasta pronto|hasta manana|chao|chau|bye|nos vemos|buenas noches|eso es todo|ya termine|he terminado|tengo que irme)$/,
  de: /^(tschuss|tschus|bye|ciao|auf wiedersehen|wiedersehen|bis spater|bis bald|bis morgen|gute nacht|das wars|das ist alles|ich bin fertig|ich muss gehen)$/,
}

/** Lower case, no accents, no apostrophes, only a-z and spaces: how spoken commands are compared. */
export function plain(text) {
  return String(text || '')
    .toLowerCase().replace(/ß/g, 'ss').normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/['’`]/g, '').replace(/[^a-z ]+/g, ' ').replace(/\s+/g, ' ').trim()
}
