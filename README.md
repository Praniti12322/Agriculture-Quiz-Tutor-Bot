# Agriculture Quiz / Tutor Bot 🤖🌾

A premium full-stack AI learning platform for agriculture, powered by **FAISS** (Local Knowledge Base) and **Groq LLaMA 3.1** (AI Generation & Reasoning).

## ✨ Key Features

- **🎯 Integrated Quiz Layout**: Questions are rendered intuitively with the **Scenario/Text first**, followed by **Integrated Media** (Image/Audio), and then the **Multiple Choice Options**, all within a single chat bubble.
- **🔊 Hear AI Scenarios (TTS)**: For audio-based quizzes, the bot uses the browser's built-in Text-to-Speech engine to read out AI-generated scenarios, complete with a natural pulsing neon "Hear AI Scenario" button.
- **🖼️ Multimodal Support**:
  - **Dynamic Images**: Generated based on question context using LoremFlickr.
  - **Real Audio**: Full support for standard playback controls for uploaded or static media.
- **📤 Custom Learning Path**: Users can upload their own farming media (Images or Audio) to generate specific questions from their personal content.
- **📈 Progress Dashboard**: Track your agricultural knowledge growth with real-time performance visualizations (Chart.js).
- **🔒 Secure Authentication & Dashboard**: Built-in user authentication (SQLite/JWT) with a personalized learning dashboard.

## 🛠️ Prerequisites

- Python 3.10+
- A Groq API Key (Sign up at [console.groq.com](https://console.groq.com/))

## ⚙️ Setup Instructions

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Configuration**
   - Create a `.env` file in the root directory (or use `.env.example` as a template).
   - Add your Groq API key:
   ```env
   # .env content
   GROQ_API_KEY=gsk_your_actual_key_here
   ```

3. **Run the Server**
   ```bash
   uvicorn backend.app:app --reload --host 0.0.0.0
   ```

4. **Access the Application**
   Navigate to: [http://localhost:8000](http://localhost:8000)

## 📁 Project Structure

- `backend/`: FastAPI application, vector database logic (FAISS), and user auth (SQLite).
- `frontend/`: Modern HTML/vanilla CSS/JS interface designed for visual excellence.
- `data/`: Knowledge base source (`agriculture_tips.txt`) and image repository.
- `uploads/`: Dedicated directory for user-uploaded media content.

## ⚠️ Troubleshooting

### "Failed to generate question"
- Ensure your `GROQ_API_KEY` in the `.env` file is valid and hasn't hit rate limits.
- Check the backend console for `Warning: GROQ_API_KEY not found in environment`.

### Port 8000 already in use
- **Windows Fix**:
  ```powershell
  $pid = (Get-NetTCPConnection -LocalPort 8000).OwningProcess
  Stop-Process -Id $pid -Force
  ```
