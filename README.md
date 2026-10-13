# Marshie

Marshie is a marshmallow who talks and listens in **English, French, Spanish and German**, with a girl's or a boy's voice (her choice of bow on the head or bow tie on the neck goes with it). She was made for the **Ecole Ronsard STEAM Program 2026** (Science, Technology, English, Agriculture & Arts, and Mathematics). Children talk or type to her. She fills the screen, and a small **Menu** box holds everything else. She answers from what she knows (maths, English, literature, science, technology, Ghana and world history, geography, arts, STEAM, and facts about Ecole Ronsard itself), shows how she feels with her face, and learns whatever the students and teachers teach her: Excel sheets, pictures, recordings, videos, PDF and Word files.

She wakes up with this greeting, written on the screen and spoken aloud:

> Hello! My name is Marshie, your friendly educative chatbot for the Ecole Ronsard STEAM (Science, Technology, English, Agriculture & Arts, and Mathematics) Program 2026. How may I be of assistance?

(You can change the words in the Teacher panel, **Look and words**.)

She runs on **Raspberry Pi 5, Windows, macOS (Apple silicon and Intel) and Linux** with the same files, and the same code also deploys to **Vercel**. She works with no AI key and no internet once installed. A paid AI can be added later from the Teacher panel.

Her colours come from the school logo (teal, yellow, pink and green) and can be changed, or picked from any other logo, in the Teacher panel.

| She is... | when... |
|---|---|
| bouncing, waving and winking | she is idle: now and then she hops, waves, winks, looks around, wiggles or twirls. Tap her and she giggles, waves, gasps or blushes |
| waving hello | she wakes up, or a child says hello or goodbye |
| listening | the microphone is on (she shows the sound waves, and the words appear as the child speaks) |
| thinking | she is searching her knowledge |
| talking | she is answering |
| giggling | she tells a joke or sings |
| amazed | she shares a fun fact |
| blushing with hearts | a child says thank you or is kind to her |
| celebrating | a child taps **That's right** |
| sad and sorry | a child taps **That's wrong**, then she asks to be taught the right answer |
| puzzled | she does not know yet (the question goes on the teacher's "to learn" list) |
| sleepy | nobody has touched the screen for a while |

## Start her

You need Python 3.10 or newer and an internet connection for the first start only.

**Windows.** Install Python from python.org (tick *Add python.exe to PATH*). Double-click **`start.bat`**.

**macOS.** Install Python from python.org. Double-click **`Start Marshie.command`** (the first time: right-click, Open, Open).

**Raspberry Pi 5 / Linux.**
```bash
sudo apt install python3 python3-venv python3-pip
./start.sh
```

Every system also works with the same command: `python marshie.py` (or `python3 marshie.py`).

The first start makes a private Python space (`.venv`), installs the packages, creates a `.env` settings file with a fresh secret key, and opens Marshie in the browser at http://localhost:8000. Run `python marshie.py setup` instead if you want to choose the teacher PIN and school name when asked.

The screen is already built in the zip. If you got the project from Git it is not, so install Node.js 18 or newer (`sudo apt install nodejs npm` on the Pi) and the launcher builds it for you. You can also build it on any computer and copy `frontend/dist` across.

### Commands

```
python marshie.py start        start her and open the browser
python marshie.py kiosk        start her and open her full screen (Chrome, Edge or Chromium)
python marshie.py key          save your paid AI key in the private .env file (asks while you paste; --status, --remove)
python marshie.py voice        install the offline voice and listening (--piper-voice en_US-lessac-medium for a more lifelike one)
python marshie.py autostart    start her by herself when the computer turns on (add --remove to undo)
python marshie.py doctor       check what works and what is missing
python marshie.py build        rebuild the screen after editing frontend/src
python marshie.py test         run the self-tests
```

Add `--share` to `start` or `kiosk` so phones and tablets on the school network can open her at the address she prints. The microphone only works on `localhost` or HTTPS, so on those devices children can type.

### The school screen

1. Plug a screen, speakers and a USB microphone into the Pi (or use a laptop).
2. `python marshie.py kiosk` opens her full screen. Press Alt+F4 to leave (Cmd+Q on a Mac).
3. `python marshie.py autostart` makes this happen every time the computer starts. On the Pi also turn on automatic sign-in: `sudo raspi-config`, System Options, Boot / Auto Login.

## Talking with her

**The screen.** Marshie fills the whole screen. What she says appears under her in large writing like subtitles, with the question above it. The bar at the bottom has **Talk with me**, a box to type in, and **Send**. The small **Menu** button (top right) opens a little box with: the language, girl or boy, the topics to tap and ask about, **How to use me**, **Full screen**, **What we said** (the whole conversation) and **Start fresh**. Teachers open the Teacher panel from the same box (**Teachers**).

**Four languages.** In the Menu box, pick **English, Français, Español or Deutsch**. Everything changes at once: the words on the screen, the tap-to-ask questions, what she hears and what she says. She keeps her own knowledge for each language, so a French question is answered from French facts. About 77 facts and answers are built in for each of French, Spanish and German (the school, maths, science, Ghana, arts, technology and fun), sums work in each language ("Combien font 12 fois 7 ?"), the quiz asks in that language and unkind words are caught in all four. Good to know:

- If she knows an answer only in English, she says so kindly, gives it in English and, when the paid AI is on, translates it. Translations count against the AI's daily limit.
- Teach her in a language by choosing it first (children) or by picking **Language** in the Teacher panel, **Teach by typing**. Excel sheets have a **Language** column (English, French, Spanish, German; empty means English).
- Her offline voice and ears (`python marshie.py voice`: Piper and Vosk) are English only. In French, Spanish and German she uses the voices that come with the browser and computer, and listening needs Chrome or Edge with the internet. If a computer has no French, Spanish or German voice, she still writes the answer on the screen; install one in the computer's voice settings.
- The greeting you write in the Teacher panel is the English one. The other three languages have a built-in greeting.

**Girl or boy.** In the Menu box (or Teacher panel, **Voice and screen**) choose **Girl** or **Boy**. A girl Marshie wears a **bow on her head** and speaks with a girl's voice. A boy Marshie wears a **bow tie on his neck**, speaks with a lower voice and the screen's wording changes where it matters (for example "désolé" instead of "désolée" in French). The choice is remembered on that computer.

**Conversation mode.** Press **Talk with me** under the chat and just talk. She listens, answers out loud, then listens again, like a conversation with a phone assistant. The words she hears appear on the screen while the child is still speaking, and a soft sound tells them when it is their turn.

- To end it: say "stop" or "goodbye", press **Stop talking**, or stay quiet. After a few quiet turns she says she will rest.
- Tap Marshie while she is talking to stop her and speak.
- She only listens when she is not talking, so she never hears herself.
- In a quiz, children say their answers. Saying "stop" ends the quiz first, and a second "stop" ends the conversation.
- On a school screen, tick **Start chatting by herself when she wakes up** (Teacher panel, Voice and screen) so children do not even need to press the button.

**Her voice, like Siri.** (For a boy Marshie the voice is lower and the **Young girl** style is not used.) She starts in the **Natural** style: a normal pitch and pace, using the most lifelike voice she can find on the computer (Apple's Siri, Premium and Enhanced voices, then Microsoft's Natural voices, then the plain built-in ones). The **Young girl** style, higher and slower, is one click away in the Teacher panel, **Voice and screen**, which also shows which voice she is using and lists the voices best first.

To get a more lifelike voice:

- **Mac:** System Settings, Accessibility, Spoken Content, System Voice, Manage Voices. Download a voice marked *Premium* or *Enhanced* (for example Ava or Samantha), and any Siri voices you see. Quit the browser fully and open it again. Whether the browser lists Apple's own Siri voices depends on your macOS and browser; if it does, she picks them. If not, Ava (Premium) is the nearest.
- **Windows:** use Microsoft Edge. Its voices ending in "Natural" (Aria, Jenny) are the best.
- **Any computer, no internet:** run `python marshie.py voice --piper-voice en_US-lessac-medium` once. It installs Piper (talking) and Vosk (listening) and downloads the voice files (about 140 MB). Other good ones are `en_US-amy-medium` and `en_GB-jenny_dioco-medium`. Chromium on a Raspberry Pi often has no speech recognition of its own, so this is also how to get listening working there.

Good to know:

- Listening in Chrome or Edge uses the browser's online speech recognition, so it needs the internet. Firefox has none, Brave switches it off, and Safari's is unreliable (see "Listening says it needs the internet" below). The offline listener (Vosk) works without the internet but shows the words only after the child has finished speaking.
- She does not wake up to "Hey Marshie". Browsers cannot safely listen all the time, so children press **Talk with me**, or use the auto-start setting above.
- She answers each question on its own. A follow-up like "and what about Kenya?" only works when the paid AI is on, because the AI is given the recent conversation. Her own knowledge needs a full question.
- In a noisy hall the microphone will pick up other people. For a busy fair, use a headset microphone or let children press the button for each question.

## The Teacher panel

Click **Teachers** at the top right and type the PIN (`ADMIN_PIN` in `.env`, starts as 2468, please change it).

- **Today** shows what she knows, anything waiting for your approval, and *Questions Marshie could not answer*, each with a **Teach the answer** button. A switch makes children's teaching wait for your OK first.
  Under **Recent uploads** each Excel sheet, picture, recording or document has an **Undo** button (it asks twice). It takes back everything that one upload added: the facts, the data tables, the file itself. Facts she already knew before are kept, and Undo cannot bring back something the upload *replaced* (a table or document with the same name). Uploads made before this feature existed have no Undo; delete their items in **What Marshie knows** instead.
- **Add data** is the place for everything else. Choose files, or drop them on the box, as many as you like at once. She shows you each one before it is added:
  - **Excel sheets** (made in the next tab, filled in by students). She shows what she found, which rows need fixing and a few things she would learn.
  - **Pictures** (png, jpg, webp, gif). Children ask "show me the school gate" and the picture appears in the chat. Big photos are shrunk for you.
  - **Recordings** (mp3, wav, m4a, ogg, webm) and **videos** (mp4, webm). Children ask "play the school bell" and a player appears. You can also record your own voice right there. Type or paste what the recording says, or press **Write it out for me** (needs `python marshie.py voice`), and children can then ask about the words inside it.
  - **Documents** (PDF, Word, PowerPoint, plain text, web pages). She cuts them into short passages and reads the right passage when someone asks. Adding the same file again replaces the earlier copy.
  - **Pasted text**, for a page of a textbook or school notes.
  - **A backup** made by this panel (.json or .zip). Adding it adds what is inside to what she already knows. It does not remove anything, so to go back to an earlier state use **Undo** on the upload, or stop Marshie and delete the `data` folder to start from nothing.
- **Excel sheets** makes the template for students (pick the sheet type, class, subject and columns). It has instructions, an example row and subject drop-downs.
  - *Questions and answers* and *Facts* sheets become things she can answer.
  - *Data* sheets become tables. Children can ask "What is the average Week 2 height in the plant data?" or "Who has the highest Week 1?".
- **Teach by typing** adds one question and answer, in the language you pick. Add a short answer to make it usable in quiz mode.
- **What Marshie knows** lets you search, delete things that were taught, delete pictures, recordings, documents and data tables, and keep a copy safe: a **.zip with the pictures and sound** (best), the words only (.json), or an Excel file.
- **Look and words** changes the (English) greeting, the four school colours (with a live preview), the logo, and has a **Pick the colours from this logo** button. It also shows all of Marshie's faces.
- **Paid AI** adds an AI service (see below).
- **Voice and screen** has girl or boy (bow or bow tie), the voice and pitch controls, bigger writing, sleep and fresh-chat timers.

### How she learns

A child asks, she answers, and the child taps **That's right** or **That's wrong**. Right makes her celebrate and trust that answer more. Wrong makes her sad, and she opens a box where the child types or says the right answer. A corrected answer beats the old one the next time. Unkind words and phone numbers or emails are refused. Typing `quiz me` starts a quiz (arithmetic that gets harder as the child gets it right, plus questions from everything she knows).

### Knowledge files

Her built-in knowledge is in `backend/app/data/*.json`. To add your own, copy a backup file (**What Marshie knows**, Download backup) into `backend/app/data/custom/`. The questions in it then ship with every deployment. Data tables are not part of that folder; restore them from the same backup in the panel.

## The paid AI (optional)

Open the Teacher panel, **Paid AI**.

1. Choose the service: Claude (Anthropic), OpenAI, OpenRouter, Groq, Google Gemini, Ollama on this computer (free, no key), or any other OpenAI-style service.
2. Make a key on that service's website, paste it in, and press **Test it**. You will see the AI's reply, or a plain explanation of what is wrong.
3. Set **Most AI answers each day** (the default is 300) and press **Save**.

She still answers from her own knowledge first. Only when she is not sure does she ask the AI, giving it her best facts, and the AI's answer is checked for unkind words before a child sees it. If the AI is slow, offline or over its daily limit, she falls back to what she has learned. Uncheck **Use the AI** to pause it without losing the key, or **Remove the key** to take it out.

Good to know:

- **You pay the service**, a very small amount for each answer. The daily limit protects you from a surprise bill. On Vercel each running copy counts by itself, so the limit is approximate there.
- **The key is private.** It is stored on the computer that runs Marshie (`data/state.json`; on Vercel, in your Upstash store). It is never sent back to any screen, never shown again (only its last four letters), and never put in a backup. Anyone who copies the `data` folder copies the key, so keep that folder private. On Vercel you can set `LLM_PROVIDER` and `LLM_API_KEY` as environment variables instead.
- **Privacy.** When she asks the AI, the child's question and a few lines of the school's facts go to that service. Ask children not to type their full names, addresses or phone numbers, and tell parents.
- **Putting your key on this computer.** Run `python marshie.py key`, paste the key when asked (nothing is shown while you paste) and press Enter. It is saved in the private `.env` file, which is never committed to Git, and only its last four letters are ever printed. It picks the service for you: keys starting `sk-ant` are Claude, other `sk-` keys are OpenAI. `python marshie.py key --status` says whether one is saved and `--remove` takes it out. **Never write a key into any other file** (README, code, a message you commit): a key that reaches GitHub can be found and used by strangers within minutes. If a key was ever pasted somewhere public or in a chat, make a new one on the service's website and delete the old one.
- Computers that are set up by hand can still use `.env`: `LLM_PROVIDER` (`anthropic` or `openai`), `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`. What is saved in the Teacher panel wins over `.env`.
- For an offline AI on a Pi-sized machine, choose **Ollama** (it runs on the same computer, so no key is needed).

## Put it on Git and Vercel

```bash
git init && git add . && git commit -m "Marshie"
git remote add origin <your repository url> && git push -u origin main
```

`.env`, `data/`, `voices/`, `.venv` and `node_modules` are in `.gitignore`, so your PIN and secret key stay private.

On Vercel: **Add New, Project**, import the repository, leave the framework as *Other* (`vercel.json` has the build command), and add these environment variables before deploying:

| Name | Value |
|---|---|
| `ADMIN_PIN` | your teacher PIN (**required**: not 2468) |
| `SECRET_KEY` | **required**: a long random string: `python3 -c "import secrets;print(secrets.token_hex(24))"` |
| `SCHOOL_NAME`, `BOT_NAME`, `EVENT_NAME`, `GREETING` | optional (the school's name and greeting are already set to Ecole Ronsard) |
| `LLM_PROVIDER`, `LLM_API_KEY` | optional (or add the key later in the Teacher panel) |

To take back a bad update later: in Vercel, open the project's page, click **Instant Rollback** on the Production tile and pick the earlier deployment (or run `vercel rollback`; the free plan can only go back one step). After a rollback, new pushes do not go live until you click **Undo Rollback** (or run `vercel promote <deployment-url>`). Rolling back changes her code only, not what she has learned; use **Undo** on an upload for that. On GitHub, `git revert HEAD` then `git push` undoes your last push without erasing history.

If `vercel --prod` says *Failed to connect <your repository> to project*, the deployment still worked. Vercel just cannot see your GitHub repository yet: in Vercel, open your account's **Settings, Authentication** (or the project's **Settings, Git**), connect GitHub, and allow it to read the `marshie` repository.

Online, anyone can reach the site, so the Teacher panel **stays locked** (it says so when you try to log in) until both `ADMIN_PIN` and `SECRET_KEY` are set in the Vercel project's **Settings, Environment Variables**, or with `vercel env add ADMIN_PIN production` and `vercel env add SECRET_KEY production`. Deploy again after adding them.

Things that are different online:

- **Memory.** Vercel's disk is temporary. Without a store she forgets what she was taught when the function restarts. Add an **Upstash Redis** (or Vercel KV) store from the Vercel Marketplace; it sets `KV_REST_API_URL` and `KV_REST_API_TOKEN` and she then remembers everything. The Teacher panel warns you while this is missing.
- **Voice.** The offline voice needs a computer, so online she uses the browser's voice and listening. HTTPS is automatic, so the microphone works on phones and laptops.
- **Uploads are limited.** Vercel accepts about 4.5 MB per request, so Excel sheets and documents must be smaller than that (the Pi accepts 8 MB). Pictures, recordings and videos are kept in the Upstash store, so each must be under about 600 KB (big photos are shrunk for you; use short recordings, and keep videos for the Pi or a laptop). A free Upstash store also holds only about 1 MB of knowledge in all, and the Teacher panel's **Today** tab shows how full it is. Without a store, uploaded files are lost when the function restarts. For a real event with lots of pictures and sound, run Marshie on the Pi or a laptop and use Vercel only as a lighter demo.

## Folder map

```
marshie.py            launcher for every system
start.sh, start.bat, Start Marshie.command    double-click or one-line starters
.env.example          copy of the settings (the launcher makes .env for you)
backend/app/          the brain: FastAPI, search, maths, Excel, documents, media, AI, voice, store
backend/app/data/     built-in knowledge (JSON), custom/ for your own
backend/tests/        self-tests (python marshie.py test)
frontend/src/         the face and screens (Vue 3 + Vite)
api/index.py          Vercel entry point
vercel.json           Vercel settings
data/state.json       what she has learned on this computer (private, not in Git)
data/media/           the pictures, recordings and videos you added (private, not in Git)
voices/               offline voice files, if installed
```

## If something is not working

Run `python marshie.py doctor` first. It lists what is missing.

- **She does not speak.** Tap the page once (browsers need that), check the speaker and the *Sound on* button. Try the Teacher panel, Voice and screen, **Hear Marshie talk**. On a Pi with no sound from Chromium, run `python marshie.py voice`.
- **"Listening is not working in this browser, but it is not your internet."** The word *network* in this error comes from the browser's own speech service, not from your Wi-Fi. That service is missing or blocked in Brave, Arc, Chromium, Opera, Vivaldi and Firefox, it can be blocked by a VPN, a firewall, a school network or a privacy or ad blocker, and Safari only has it when Dictation is on. Two fixes, in this order:
  1. Open `http://localhost:8000` in **Google Chrome** (or Microsoft Edge), with any VPN off, and allow the microphone. Then open **Teachers, Voice and screen, Listening, Test the microphone**. It tells you which browser it found and what to change.
  2. For listening that never depends on the browser or the internet, stop Marshie with Ctrl+C, then run `python3 marshie.py voice --only listen` (about 40 MB, once) and `python3 marshie.py start`. The Listening box then says she is using the offline listener.
- **"Method Not Allowed" when logging in online (Vercel).** The online copy was handed the wrong web address for the request. Use the latest files (`vercel.json` and `backend/app/vercel_path.py` carry the fix), run `vercel --prod` again, then check `https://YOUR-ADDRESS/api/health`. It should show Marshie's name. A wrong PIN should then say "That PIN is not right."
- **The microphone does nothing.** It needs `http://localhost:8000` or HTTPS, not a plain network address. Allow the microphone when the browser asks. Firefox has no speech recognition and Safari's is unreliable, so use Chrome or Edge, or install the offline listening.
- **"Port 8000 is busy".** She picks the next free port by herself. You can also use `--port 9000`.
- **Packages will not install.** The first start needs the internet. A school network that blocks PyPI can use a phone hotspot for that one step.
- **A picture or recording will not add.** She tells you why: too big (the limit is shown on the Add data tab), or the file is not what its name says. PDF files need one extra package that `python marshie.py setup` installs (`pypdf`). A PDF that is a photo of paper has no text to read, so type or paste the words instead.
- **"Pick the colours from this logo" gives odd colours.** Logos with many shades confuse it. Pick the four colours by hand, or press **Use the Ecole Ronsard colours**.
- **The AI test says the key was not accepted.** Check that you copied the whole key with no spaces, that it belongs to the service you chose, and that the account has credit.
- **macOS says the file is from an unidentified developer.** Right-click the file, Open, Open.

## What has and has not been tested

Run in a headless Chromium and a test server, and passing: the built-in and school knowledge, search, the learning loop, Excel templates and upload, data-table questions, adding pictures, a recording, a Word document and an Excel sheet from the Teacher panel and then asking for them in the chat (including the audio player and byte-range playback that Safari needs), the zip backup and restore, deleting files, the greeting and colour editor, the Paid AI tab (against a stand-in service, and a real service that correctly refused a made-up key), the quiz, the launcher's setup, start, doctor, autostart and test commands, and the screens at phone, tablet, laptop and Pi-screen sizes with no sideways scrolling, and the hands-free conversation (with a simulated microphone and simulated voices: it listens, answers aloud, never listens while she talks, ends on "goodbye" or "stop", on the Stop button or after silence, can be interrupted by a tap, handles a spoken quiz, and can start by itself). The words on the screen were checked to exist in all four languages with the same blanks to fill in, every tap-to-ask question was asked in each language and got a real answer, and the whole screen was run in French, Spanish and German (phone, tablet, laptop and desktop, girl and boy) with no errors. There are 42 automatic backend tests (`python marshie.py test`), including one that checks no AI key is written anywhere in the project. **Not yet tried:** how French, Spanish and German sound with real Apple or Microsoft voices, and real listening in those languages (the tests used stand-ins), so please try each language with a microphone on the Mac before the event. Vercel's runtime was simulated locally.

**Not yet tried on real hardware or services:** real speech recognition and real Apple or Microsoft voices (the tests used stand-ins, so please try a conversation on your Mac before the event), the offline voice downloads and speaking/listening (Piper and Vosk), uploading a recording and having Vosk write it out, the Raspberry Pi 5 itself, Windows and macOS, an actual Vercel deployment, and a paid AI key from Claude or OpenAI (the request format is written to their documentation, and the Test button will tell you at once if something is off). The code is written to be portable, and `python marshie.py doctor` and the voice self-test are there to show quickly if something on your machine differs. Please try the voice, the microphone and the AI test the day before the event.

**About the school's information.** Her facts about Ecole Ronsard come from the school's website. Pages that were empty or missing there (for example field trips and the blog) were left out rather than guessed, so please teach her anything else children will ask about the school in **Add data**.
