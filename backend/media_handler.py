"""
media_handler.py – Handles image, audio, and video processing for multimodal quiz generation.
- Images: Sent to Groq vision model for description
- Audio:  Sent to Groq Whisper API for transcription
- Video:  Audio extracted via ffmpeg, then transcribed with Whisper
"""

import os
import io
import base64
import subprocess
import tempfile
from groq import Groq

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
WHISPER_MODEL = "whisper-large-v3-turbo"
TEXT_MODEL = "llama-3.1-8b-instant"


def describe_image(image_bytes: bytes, filename: str) -> str:
    """Send image to Groq vision model, get a description of its agricultural content."""
    ext = filename.rsplit(".", 1)[-1].lower()
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp", "gif": "image/gif"}
    mime = mime_map.get(ext, "image/jpeg")
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{mime};base64,{b64}"

    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": data_url}
                },
                {
                    "type": "text",
                    "text": (
                        "You are an agriculture expert. Describe what you see in this image "
                        "in terms of agricultural relevance (crop types, farming techniques, soil, "
                        "pests, irrigation, etc.). Be concise and factual (2-4 sentences)."
                    )
                }
            ]
        }],
        max_tokens=400,
    )
    return response.choices[0].message.content.strip()


def transcribe_audio(audio_bytes: bytes, filename: str) -> str:
    """Transcribe audio file using Groq Whisper API."""
    ext = filename.rsplit(".", 1)[-1].lower()
    # Groq Whisper accepts: flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, webm
    supported = {"flac", "mp3", "mp4", "mpeg", "mpga", "m4a", "ogg", "wav", "webm"}
    if ext not in supported:
        ext = "wav"

    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = f"audio.{ext}"

    transcription = client.audio.transcriptions.create(
        file=(audio_file.name, audio_bytes),
        model=WHISPER_MODEL,
        response_format="text"
    )
    return str(transcription).strip()


def extract_audio_from_video(video_bytes: bytes, input_ext: str) -> bytes:
    """Extract audio (WAV) from video bytes using ffmpeg subprocess."""
    with tempfile.NamedTemporaryFile(suffix=f".{input_ext}", delete=False) as vf:
        vf.write(video_bytes)
        video_path = vf.name

    audio_path = video_path.replace(f".{input_ext}", "_audio.wav")

    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
             "-ar", "16000", "-ac", "1", audio_path],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr}")

        with open(audio_path, "rb") as af:
            return af.read()
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(audio_path):
            os.remove(audio_path)


def generate_question_from_context(context: str, media_type: str, force_mcq: bool = True) -> dict:
    """
    Given a text context (from image description or audio transcript),
    generate a quiz question using the LLM.
    Returns dict: { question_text, options (list[str] or []), correct_hint }
    """
    mcq_instruction = (
        "Generate a single multiple-choice question with exactly 4 options labeled A, B, C, D. "
        "Do NOT reveal the correct answer — only provide the question and options."
    ) if force_mcq else (
        "Generate a single open-ended descriptive question. No options needed."
    )

    media_label = {
        "image": "the image described above",
        "audio": "the audio transcript above",
        "video": "the video transcript above",
        "text": "the agricultural facts above"
    }.get(media_type, "the content above")

    prompt = f"""You are an agriculture education expert.

Based on the following content about agriculture:
---
{context}
---

{mcq_instruction}
The question should test understanding of {media_label}.
Output ONLY the question text and options (if MCQ). No extra text, no answers, no explanations.
"""

    response = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=300,
    )
    raw = response.choices[0].message.content.strip()

    # Parse options from response
    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    options = []
    question_lines = []
    for line in lines:
        if line[:2] in ("A.", "B.", "C.", "D.", "A)", "B)", "C)", "D)") or \
           (len(line) > 2 and line[0] in "ABCD" and line[1] in ".):"):
            options.append(line)
        else:
            question_lines.append(line)

    question_text = " ".join(question_lines).strip()
    return {
        "question_text": question_text,
        "options": options,
        "raw": raw,
        "context": context  # store for evaluation
    }


def handle_image(image_bytes: bytes, filename: str) -> dict:
    """Full pipeline: image bytes → description → question."""
    description = describe_image(image_bytes, filename)
    result = generate_question_from_context(description, "image", force_mcq=True)
    result["media_description"] = description
    result["media_type"] = "image"
    return result


def handle_audio(audio_bytes: bytes, filename: str) -> dict:
    """Full pipeline: audio bytes → transcript → question."""
    transcript = transcribe_audio(audio_bytes, filename)
    if not transcript:
        transcript = "No clear speech detected in audio."
    result = generate_question_from_context(transcript, "audio", force_mcq=False)
    result["media_description"] = transcript
    result["media_type"] = "audio"
    return result


def handle_video(video_bytes: bytes, filename: str) -> dict:
    """Full pipeline: video bytes → audio extraction → transcript → question."""
    ext = filename.rsplit(".", 1)[-1].lower()
    try:
        audio_bytes = extract_audio_from_video(video_bytes, ext)
        transcript = transcribe_audio(audio_bytes, "extracted.wav")
    except Exception as e:
        transcript = f"Could not extract audio: {str(e)}"

    if not transcript or transcript.startswith("Could not"):
        # Fallback: describe it as unknown video
        transcript = "Video content related to agriculture practices."

    result = generate_question_from_context(transcript, "video", force_mcq=False)
    result["media_description"] = transcript
    result["media_type"] = "video"
    return result
