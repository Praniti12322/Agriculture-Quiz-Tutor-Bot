from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os, random
from . import database, auth, quiz_logic

app = FastAPI(title="Agriculture AI Quiz Bot")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Ensure upload & image dirs exist
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
IMAGES_DIR = os.path.join(BASE_DIR, "data", "images")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(FRONTEND_DIR, exist_ok=True)

# ── Pydantic Models ────────────────────────────────────────────────
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class AnswerSubmission(BaseModel):
    question: str
    user_answer: str

class MultimodalAnswerSubmission(BaseModel):
    question: str
    user_answer: str
    media_context: Optional[str] = ""

class AttemptSubmission(BaseModel):
    is_correct: bool
    question_type: Optional[str] = "text"

class TutorChatRequest(BaseModel):
    message: str
    history: list = []

# ── Startup ────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    print("Initializing Database...")
    database.init_db()
    print("Initializing Vector Database...")
    quiz_logic.init_index()

# ── Auth ───────────────────────────────────────────────────────────
@app.post("/signup")
def signup(user: UserCreate):
    success = database.create_user(user.username, user.email, user.password)
    if not success:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    return {"message": "User created successfully"}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = database.get_user(form_data.username)
    if not user or not database.verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = auth.verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return username

# ── Quiz – Text (legacy) ───────────────────────────────────────────
@app.get("/generate-question")
def generate_question(current_user: str = Depends(get_current_user)):
    question = quiz_logic.generate_quiz_question()
    return {"question": question}

@app.post("/evaluate-answer")
def evaluate_answer(submission: AnswerSubmission, current_user: str = Depends(get_current_user)):
    evaluation = quiz_logic.evaluate_answer(submission.question, submission.user_answer)
    return {"evaluation": evaluation}

# ── Quiz – Multimodal ──────────────────────────────────────────────
SUPPORTED_TYPES = ["text", "image", "audio"]

@app.get("/generate-question-multimodal")
def generate_question_multimodal(
    type: str = Query(default="random", description="text | image | audio | random"),
    current_user: str = Depends(get_current_user)
):
    q_type = type if type in SUPPORTED_TYPES else random.choice(["text", "image", "audio"])
    result = quiz_logic.generate_question_multimodal(q_type)
    return result

@app.post("/upload-media")
async def upload_media(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user)
):
    from . import media_handler

    filename = file.filename or "upload"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    content_bytes = await file.read()

    IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "gif"}
    AUDIO_EXTS = {"mp3", "wav", "m4a", "ogg", "flac", "webm", "mpga"}
    VIDEO_EXTS = {"mp4", "mov", "avi", "mkv", "webm"}

    if ext in IMAGE_EXTS:
        q_type = "image"
        result = media_handler.handle_image(content_bytes, filename)
    elif ext in AUDIO_EXTS:
        q_type = "audio"
        result = media_handler.handle_audio(content_bytes, filename)
    elif ext in VIDEO_EXTS:
        q_type = "video"
        result = media_handler.handle_video(content_bytes, filename)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: .{ext}")

    # Save file for frontend display
    save_path = os.path.join(UPLOAD_DIR, filename)
    with open(save_path, "wb") as f:
        f.write(content_bytes)

    media_url = f"/uploads/{filename}" if q_type in ("image", "audio", "video") else None

    return {
        "question": result["raw"],
        "options": result["options"],
        "q_type": q_type,
        "media_url": media_url,
        "media_context": result["media_description"],
        "raw_question": result["question_text"],
    }

@app.post("/evaluate-multimodal")
def evaluate_multimodal(
    submission: MultimodalAnswerSubmission,
    current_user: str = Depends(get_current_user)
):
    evaluation = quiz_logic.evaluate_answer_multimodal(
        submission.question,
        submission.user_answer,
        submission.media_context or ""
    )
    return {"evaluation": evaluation}

# ── Tutor Chat ─────────────────────────────────────────────────────
@app.post("/tutor-chat")
def tutor_chat_endpoint(request: TutorChatRequest, current_user: str = Depends(get_current_user)):
    response = quiz_logic.tutor_chat(request.message, request.history)
    return {"response": response}

# ── Progress ───────────────────────────────────────────────────────
@app.post("/save-attempt")
def save_attempt(submission: AttemptSubmission, current_user: str = Depends(get_current_user)):
    database.log_attempt(current_user, submission.is_correct, submission.question_type)
    return {"status": "success"}

@app.get("/progress-data")
def progress_data(current_user: str = Depends(get_current_user)):
    data = database.get_user_progress(current_user)
    return data

# ── Static Files ───────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/media", StaticFiles(directory=IMAGES_DIR), name="media")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))

@app.get("/{page}")
def get_page(page: str):
    file_path = os.path.join(FRONTEND_DIR, page)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Page not found")
