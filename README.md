# NewsX — AI-Summarized, Reels-Style Daily News

Scroll through the day's news the way you scroll Instagram Reels — one
AI-condensed story per screen, vertical scroll or swipe to move to the next
one. Tap ♥ to like, 🔖 to save, tap your avatar for your profile dashboard.
Works in the browser on your laptop AND on your phone, with a real login
system and a real database behind it.

**Tech stack:** Python + Flask (backend/API), SQLite (database), vanilla
HTML/CSS/JS (frontend — real vertical scroll-snap reels, 3D-styled buttons),
NewsAPI (live headlines), Groq (free LLM that rewrites each article into a
short punchy summary).

---

## STEP 1 — Install Python (skip if already installed)

1. Go to https://www.python.org/downloads/ and download Python 3.11+.
2. Run the installer. **Tick "Add Python to PATH"** before clicking Install.
3. Check it worked — open a terminal (Windows: search "cmd") and run:
   ```
   python --version
   ```

## STEP 2 — Get the project folder onto your laptop

Copy the whole `NewsX` folder (with the `static` subfolder inside it, containing
`index.html`) to your Desktop. Keep the folder structure exactly as given —
`app.py` and `database.py` sit directly inside `NewsX/`, and `index.html` sits
inside `NewsX/static/`.

## STEP 3 — Open in VS Code

Open VS Code → File → Open Folder → select `NewsX`. Then Terminal → New
Terminal (or Ctrl + `) — this opens a terminal already inside the right folder.

## STEP 4 — Create a virtual environment and install dependencies

```
python -m venv .venv
```
Activate it:
- Windows: `.venv\Scripts\activate`
- Mac/Linux: `source .venv/bin/activate`

Then:
```
pip install -r requirements.txt
```

## STEP 5 — Get your two free API keys

**NewsAPI (real daily headlines):**
1. Go to https://newsapi.org/register — sign up free.
2. Copy your API key from the dashboard.

**Groq (AI that writes the short summaries):**
1. Go to https://console.groq.com/keys
2. Sign up free, click "Create API Key", copy it.

Now in the NewsX folder, rename `.env.example` to `.env`, open it, and paste
both keys so it looks like:
```
NEWS_API_KEY=paste_your_newsapi_key_here
GROQ_API_KEY=paste_your_groq_key_here
```
Save the file.

*(If you skip this step, the app still runs and still looks fully working —
it just shows a placeholder story instead of live news. Good for testing the
UI, but get real keys before your demo.)*

## STEP 6 — Run it

```
python app.py
```

The terminal will print two links, like:
```
NewsX is running:
➜ Local (this laptop):  http://127.0.0.1:5000
➜ Network (your phone): http://192.168.1.5:5000
```
Open the **Local** link on your laptop's browser.

### Getting it to open on your phone

Use the **Network** link the terminal printed, on your phone's browser. If it
still won't open, check these in order — this is almost always one of them:

1. **Same WiFi.** Your phone must be on the exact same WiFi network as your
   laptop — not mobile data, and not a "guest" WiFi network that isolates
   devices from each other (some college/office WiFi does this; a home WiFi
   or a phone hotspot with the laptop connected to it will work).
2. **Windows Firewall.** The first time you run `python app.py`, Windows may
   pop up "Windows Defender Firewall has blocked some features of this app" —
   click **Allow access** (both Private and Public networks). If you missed
   that popup, go to Windows Security → Firewall & network protection →
   Allow an app through firewall → find Python → tick both boxes.
3. **Typed the address correctly** — it must be `http://`, not `https://`,
   and the exact IP the terminal printed (it can change if you reconnect to
   WiFi, so re-check it each session).

You'll land on a **sign-up / login screen** first — create any username and
password (your own local account, stored in your own database).

**How to demo it:** sign up live in front of your teacher, scroll down through
a category (mouse wheel on laptop, swipe on phone), like ♥ and save 🔖 a
couple of stories, then tap your avatar to show the profile dashboard — your
personal stats, the saved-story grid, and a live "community" card showing how
many total people have signed up and used the app, all pulled from the real
database. That signup→scroll→react→dashboard loop is the strongest thing to
show.

---

## STEP 7 — Upload to GitHub

1. Create a free account at https://github.com if needed.
2. Click **+** (top right) → **New repository**. Name it `NewsX`. Public,
   no README (you already have one). **Create repository**.
3. Install Git if needed: https://git-scm.com/downloads
4. In your VS Code terminal, inside the NewsX folder:
   ```
   git init
   git add .
   git commit -m "NewsX - final year project"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/NewsX.git
   git push -u origin main
   ```
   (Replace `YOUR-USERNAME` — copy the exact URL GitHub shows after you
   create the repo.)
5. Refresh your GitHub page — your files should be there. Your `.env` (with
   your secret keys) is deliberately excluded by `.gitignore` — that's correct.

---

## Project structure

```
NewsX/
├── app.py              # Flask backend - auth, fetches news, calls AI, serves API
├── database.py          # SQLite database functions
├── static/
│   └── index.html         # The entire frontend - reels UI, profile, auth
├── requirements.txt       # Python packages needed
├── .env.example            # Template for your API keys
├── .gitignore                # Files Git should ignore
└── README.md                  # This file
```

## How it actually works (for your viva/explanation)

1. **Auth:** passwords are hashed (never stored as plain text) using
   Werkzeug's security functions; a session cookie keeps you logged in.
2. **News caching:** when you open a category, the backend checks the
   database first — if today's news for that category is already cached, it
   serves it instantly. If not, it calls NewsAPI for real headlines, sends
   each one to the Groq AI model to rewrite as a short punchy summary, and
   saves everything into SQLite — so you only burn API calls once a day per
   category.
3. **Reels scroll:** the frontend uses the browser's native CSS scroll-snap
   (`scroll-snap-type`), so it scrolls smoothly with a mouse wheel, trackpad,
   or a touch swipe — no custom drag physics needed, which is also why it
   behaves identically on laptop and phone.
4. **Likes vs. Saves:** likes are global (everyone's likes on a story are
   counted together, shown as a number), saves are personal (only you see
   your own saved list) — both write straight to SQLite.
5. **Community stats:** the profile page queries the database for total
   registered users and how many were active today, so you can see real
   usage of your own app.

## If something goes wrong

- **"flask: command not found" / ModuleNotFoundError** → your virtual
  environment isn't activated. Redo Step 4's activate command.
- **Blank page at localhost:5000** → make sure `index.html` is inside the
  `static` folder, not directly inside `NewsX`.
- **Cards show but say "Add your NEWS_API_KEY"** → check `.env` is named
  exactly `.env` (not `.env.txt`) and sits directly inside `NewsX/`.
- **Won't open on phone** → see the three numbered checks under Step 6 above
  (same WiFi, firewall, correct address).