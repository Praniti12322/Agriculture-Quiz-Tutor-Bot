# 🌾 Agriculture Quiz & Tutor Bot

A premium full-stack AI learning platform for agriculture, powered by **FAISS** (local semantic knowledge base), **Groq LLaMA 3.1** (AI generation & reasoning), and **Sentence Transformers** (semantic embeddings).

---

## ✨ Features

### 🎯 Multimodal Quiz Engine
- **Text Questions**: AI-generated MCQs drawn from a curated agriculture knowledge base.
- **Image Questions**: Dynamic, context-relevant farming images sourced via LoremFlickr, paired with AI-crafted scenario questions.
- **Audio Questions**: Text-to-Speech (TTS) AI scenario narration using the browser's built-in speech engine, with a pulsing "Hear AI Scenario" button.
- **Random Mode**: Randomly selects question type for a varied learning experience.

### 📤 Custom Media Upload
- Users can upload their own **farming images** or **audio files** to generate personalized quiz questions from their own content.
- Supported formats: `jpg`, `jpeg`, `png`, `webp`, `gif` (images) | `mp3`, `wav`, `m4a`, `ogg`, `flac`, `webm`, `mpga` (audio).

### 🤖 AI Tutor Chat
- A dedicated **Tutor page** (`tutor.html`) with a conversational AI interface.
- Powered by Groq LLaMA 3.1 and grounded in the FAISS knowledge base for factual, agriculture-specific answers.
- Supports multi-turn conversation history for context-aware responses.

### 📈 Progress Dashboard
- Tracks every quiz attempt per user with timestamps and question type.
- Displays **daily performance charts** (Chart.js) showing total questions vs. correct answers.
- Overview stats: total questions attempted, total correct, and accuracy percentage.

### 🔒 Secure Authentication
- User registration and login using **JWT tokens** (via `python-jose`).
- Passwords securely hashed with **bcrypt** (`passlib`).
- All quiz, tutor, and progress endpoints are protected and require authentication.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI, Uvicorn |
| **AI / LLM** | Groq API (LLaMA 3.1 8B Instant) |
| **Embeddings** | Sentence Transformers (`all-MiniLM-L6-v2`) |
| **Vector Search** | FAISS (CPU) |
| **Database** | SQLite (users & quiz attempts) |
| **Auth** | JWT (`python-jose`) + bcrypt (`passlib`) |
| **Frontend** | Vanilla HTML / CSS / JavaScript |
| **Media** | LoremFlickr (dynamic images), Web Speech API (TTS) |

---

## 📁 Project Structure

```
agriculture_bot/
├── backend/
│   ├── app.py              # FastAPI routes (auth, quiz, tutor, progress, static serving)
│   ├── quiz_logic.py       # FAISS index, question generation, multimodal prompts, tutor chat
│   ├── database.py         # SQLite schema, user management, progress tracking
│   ├── auth.py             # JWT token creation & verification
│   ├── media_handler.py    # Image & audio upload processing
│   └── __init__.py
├── frontend/
│   ├── login.html          # Login page (served at /)
│   ├── signup.html         # New user registration
│   ├── bot.html            # Multimodal quiz interface
│   ├── tutor.html          # Conversational AI tutor chat page
│   ├── dashboard.html      # User progress dashboard
│   ├── progress.html       # Progress charts (Chart.js)
│   ├── script.js           # Frontend quiz & chat logic
│   └── index.css           # Global styles
├── data/
│   ├── agriculture_tips.txt  # Knowledge base (FAISS source documents)
│   └── images/               # Static agriculture images
├── uploads/                  # User-uploaded media files
├── users.db                  # SQLite database
├── requirements.txt
├── .env                      # API keys (not committed)
├── .env.example              # Template for environment setup
└── .gitignore
```

---

## ⚙️ Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Create a `.env` file in the root directory (use `.env.example` as a template):
```env
GROQ_API_KEY=gsk_your_actual_key_here
```
Get your free API key at [console.groq.com](https://console.groq.com/).

### 3. Run the Server
```bash
python -m uvicorn backend.app:app --reload --port 8000
```

### 4. Access the App
Open your browser and navigate to: [http://localhost:8000](http://localhost:8000)

You'll be directed to the **Login page**. Sign up for a new account to get started.

---

## 🔗 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/signup` | Register a new user |
| `POST` | `/login` | Login and receive a JWT token |
| `GET` | `/generate-question` | Generate a text-only MCQ |
| `GET` | `/generate-question-multimodal?type=` | Generate text/image/audio/random MCQ |
| `POST` | `/upload-media` | Upload image or audio to generate a question |
| `POST` | `/evaluate-answer` | Evaluate a text quiz answer |
| `POST` | `/evaluate-multimodal` | Evaluate a multimodal quiz answer |
| `POST` | `/tutor-chat` | Conversational AI tutor message |
| `POST` | `/save-attempt` | Log a quiz attempt to the database |
| `GET` | `/progress-data` | Retrieve user's progress statistics |

---

## ⚠️ Troubleshooting

### "Failed to generate question"
- Ensure your `GROQ_API_KEY` in `.env` is valid and hasn't exceeded rate limits.
- Check the backend terminal for: `Warning: GROQ_API_KEY not found in environment`.

### Sentence Transformer warning on startup
The warning `embeddings.position_ids | UNEXPECTED` from `BertModel` is **benign** and can be safely ignored. It's a known quirk of loading `all-MiniLM-L6-v2` for a different task architecture.

### Port 8000 already in use
**Windows fix:**
```powershell
$pid = (Get-NetTCPConnection -LocalPort 8000).OwningProcess
Stop-Process -Id $pid -Force
```

---

## 📌 Recent Changes

- ✅ **Added `tutor.html`** — Dedicated AI tutor chat page with multi-turn conversation history.
- ✅ **Removed video support** — Backend and frontend fully cleaned of all video-related logic; only text, image, and audio are supported.
- ✅ **Improved `quiz_logic.py`** — Added `AGRI_IMAGE_KEYWORDS` mapping, `extract_image_keyword()`, `build_image_url()` for smarter, context-relevant LoremFlickr images.
- ✅ **Updated `bot.html`** — Improved integrated quiz layout with scenario text, embedded media, and MCQ options in a single chat bubble.
- ✅ **Updated `dashboard.html`** — Cleaner progress overview with daily chart data.
- ✅ **Database migration** — Auto-adds `question_type` column to legacy `quiz_attempts` tables on startup.

---

## 📋 License

This project is for educational purposes. Feel free to contribute or adapt it for your own agricultural projects!
