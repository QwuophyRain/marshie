// Tap-to-ask ideas, so a child who doesn't know what to ask can still start straight away.
// Only questions Marshie's built-in knowledge can answer. Teachers can add more in the Teacher panel.
export const TOPICS = [
  { id: 'school', label: 'Our School', color: 'var(--brand)', fg: '#ffffff',
    questions: ['What does STEAM stand for?', 'Where is our school?', 'Who is the principal?', 'What clubs does the school have?', 'What sports do we play at school?'] },
  { id: 'maths', label: 'Maths', color: 'var(--gold)',
    questions: ['What is 12 times 7?', 'What is a prime number?', 'How many degrees are in a triangle?', 'What is a fraction?', 'Quiz me'] },
  { id: 'english', label: 'English', color: 'var(--pink)',
    questions: ['What is a noun?', 'What is a simile?', 'How do I say good morning in Twi?', 'What is a synonym?'] },
  { id: 'science', label: 'Science', color: 'var(--green)',
    questions: ['What is photosynthesis?', 'Why is the sky blue?', 'How many planets are there?', 'What is gravity?'] },
  { id: 'ghana', label: 'Ghana', color: '#e5484d',
    questions: ['When did Ghana get independence?', 'Who was Yaa Asantewaa?', 'What is kente?', 'What is the Akosombo Dam?'] },
  { id: 'arts', label: 'Arts', color: '#b18cff',
    questions: ['What are the primary colours?', 'What is a talking drum?', 'Who painted the Mona Lisa?', 'What is highlife music?'] },
  { id: 'tech', label: 'Tech', color: '#5fb8e8',
    questions: ['What is a Raspberry Pi?', 'What is artificial intelligence?', 'How do I make a strong password?', 'What is coding?'] },
]

export const STARTERS = ['Tell me a joke', 'Quiz me', 'What does STEAM stand for?', 'Tell me about our school']
