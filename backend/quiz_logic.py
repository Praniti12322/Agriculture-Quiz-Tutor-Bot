import os
import faiss
from sentence_transformers import SentenceTransformer
from groq import Groq
import numpy as np
import random
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initializing Groq client
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("Warning: GROQ_API_KEY not found in environment. AI features will fail.")
client = Groq(api_key=GROQ_API_KEY)

MODEL_NAME = "llama-3.1-8b-instant"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "agriculture_tips.txt")
IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "images")

embedder = SentenceTransformer(EMBEDDING_MODEL)
index = None
documents = []

def init_index():
    global index, documents
    if not os.path.exists(DATA_PATH):
        print(f"Data file not found at {DATA_PATH}.")
        return
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    raw_docs = [doc.strip() for doc in content.split("\n") if doc.strip()]
    documents = raw_docs

    if not documents:
        return

    embeddings = embedder.encode(documents)
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings, dtype=np.float32))
    print(f"Loaded {len(documents)} documents into FAISS.")

def get_random_context() -> str:
    if not documents:
        return "No agricultural data available."
    facts = random.sample(documents, min(2, len(documents)))
    return "\n".join(facts)

def generate_quiz_question() -> str:
    """Generate a text-only MCQ question from the knowledge base."""
    context = get_random_context()
    prompt = f"""You are an expert agriculture tutor.
Based on the following facts, generate a single multiple-choice question to test the user's knowledge.
Only output the question text and the 4 options (A/B/C/D). Do NOT reveal the answer.

Context:
{context}

Generate Question:"""

    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=MODEL_NAME,
        temperature=0.7,
    )
    return chat_completion.choices[0].message.content.strip()


# Scenario prompts per modality type
MODALITY_PROMPTS = {
    "image": """You are an agriculture education expert creating an image-based quiz.

Pretend the student is looking at a real agricultural photograph. Using the following facts, write:
1. A vivid 2-3 sentence description of what the image shows (crops, soil, pests, irrigation, etc.).
   Start with: "📷 In this image you can see: ..."
2. On a NEW line, write exactly: KEYWORD: <one_agriculture_word>
   (e.g., KEYWORD: tomato, KEYWORD: irrigation, KEYWORD: soil, KEYWORD: compost, KEYWORD: marigold)
3. A multiple-choice question (4 options: A, B, C, D) about what is shown.
   Do NOT reveal the answer. Only output the image description, KEYWORD line, and question+options.

Facts:
{context}
""",
    "audio": """You are an agriculture education expert creating an audio-based quiz.

Pretend the student just listened to a short farming field recording or interview. Using the following facts, write:
1. A short description of what was heard in the "audio clip" (e.g., a farmer explaining a technique, field sounds, an expert discussing a crop condition).
   Start with: "🎵 In this audio clip: ..."
2. A multiple-choice question (4 options: A, B, C, D) based on the audio content.
   Do NOT reveal the answer. Only output the audio description and question+options.

Facts:
{context}
""",
    "text": """You are an expert agriculture tutor.
Based on the following facts, generate a single multiple-choice question to test the user's knowledge.
Only output the question text and the 4 options (A/B/C/D). Do NOT reveal the answer.

Facts:
{context}
"""
}

# Agriculture keyword → LoremFlickr search terms mapping
AGRI_IMAGE_KEYWORDS = {
    "tomato": "tomato,farming",
    "corn": "corn,maize,field",
    "wheat": "wheat,grain,field",
    "rice": "rice,paddy,farm",
    "marigold": "marigold,flower,garden",
    "irrigation": "irrigation,drip,farm",
    "soil": "soil,farmland,earth",
    "compost": "compost,organic,garden",
    "fertilizer": "fertilizer,farming,soil",
    "pest": "pest,insect,crop",
    "ladybug": "ladybug,insect,crop",
    "crop": "crop,harvest,agriculture",
    "mulch": "mulch,garden,soil",
    "cover": "cover,crop,rye",
    "nitrogen": "nitrogen,legume,plant",
    "legume": "legume,bean,field",
    "rotation": "crop,rotation,farm",
    "precision": "precision,agriculture,technology",
    "sensor": "sensor,farm,technology",
    "harvest": "harvest,agriculture,field",
    "greenhouse": "greenhouse,plants,farm",
    "orchard": "orchard,fruit,trees",
    "vineyard": "vineyard,grape,farm",
}


def extract_image_keyword(raw_text: str) -> str:
    """Extract KEYWORD tag from LLM response, fall back to topic detection."""
    import re
    # Try to find explicit KEYWORD: tag
    match = re.search(r'KEYWORD:\s*(\w+)', raw_text, re.IGNORECASE)
    if match:
        kw = match.group(1).lower()
        return AGRI_IMAGE_KEYWORDS.get(kw, f"{kw},agriculture,farm")

    # Fallback: scan text for known agriculture keywords
    text_lower = raw_text.lower()
    for kw in AGRI_IMAGE_KEYWORDS:
        if kw in text_lower:
            return AGRI_IMAGE_KEYWORDS[kw]

    return "agriculture,farm,crop"

def build_image_url(keywords: str, width: int = 800, height: int = 480) -> str:
    """Build a LoremFlickr URL for the given keyword string."""
    import urllib.parse
    encoded = urllib.parse.quote(keywords)
    # Add a random cache-busting seed so we don't always get the same image
    seed = random.randint(1, 9999)
    return f"https://loremflickr.com/{width}/{height}/{encoded}?random={seed}"

def generate_question_multimodal(q_type: str) -> dict:
    """
    Generate a question purely using LLM prompting for all types.
    For image type: also fetches a relevant agriculture photo via LoremFlickr.
    Returns: {question, options, q_type, media_url, media_context, raw_question}
    """
    context = get_random_context()
    effective_type = q_type if q_type in MODALITY_PROMPTS else "text"
    prompt = MODALITY_PROMPTS[effective_type].format(context=context)

    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=MODEL_NAME,
        temperature=0.75,
        max_tokens=500,
    )
    raw = response.choices[0].message.content.strip()

    # For image questions: extract keyword and strip the KEYWORD: line from display
    media_url = None
    display_raw = raw
    if effective_type == "image":
        keywords = extract_image_keyword(raw)
        media_url = build_image_url(keywords)
        # Remove the KEYWORD: line from the displayed question text
        import re
        display_raw = re.sub(r'\n?KEYWORD:\s*\w+\n?', '\n', raw).strip()

    # Parse MCQ options out of the raw response
    lines = [l.strip() for l in display_raw.split("\n") if l.strip()]
    options = []
    q_lines = []
    for line in lines:
        if len(line) > 2 and line[0] in "ABCD" and line[1] in ".):":
            options.append(line)
        else:
            q_lines.append(line)

    question_text = "\n".join(q_lines).strip()

    return {
        "question": display_raw,      # clean text without KEYWORD line
        "options": options,
        "q_type": effective_type,
        "media_url": media_url,       # LoremFlickr URL for image type
        "media_context": context,
        "raw_question": question_text,
    }


def evaluate_answer(question: str, user_answer: str) -> str:
    if not index or not documents:
        return "System error: knowledge base not loaded."

    query = f"Question: {question} \n Answer: {user_answer}"
    query_embedding = embedder.encode([query])
    D, I = index.search(np.array(query_embedding, dtype=np.float32), k=2)

    context = "\n".join([documents[i] for i in I[0] if i < len(documents)])

    prompt = f"""You are an expert agriculture tutor grading a student.

Question: {question}
User's Answer: {user_answer}

Context facts to base evaluation on:
{context}

Evaluate the user's answer.
State clearly if it is "**CORRECT**" or "**INCORRECT**" on the very first line.
Then, provide a detailed, encouraging explanation using the context facts. Keep it beginner-friendly."""

    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=MODEL_NAME,
        temperature=0.3,
    )
    return chat_completion.choices[0].message.content.strip()

def evaluate_answer_multimodal(question: str, user_answer: str, media_context: str = "") -> str:
    """Evaluate answer with extra media context (image description / audio transcript)."""
    if not index or not documents:
        return "System error: knowledge base not loaded."

    query = f"Question: {question} Answer: {user_answer}"
    query_embedding = embedder.encode([query])
    D, I = index.search(np.array(query_embedding, dtype=np.float32), k=2)
    kb_context = "\n".join([documents[i] for i in I[0] if i < len(documents)])

    combined_context = f"{media_context}\n\n{kb_context}".strip() if media_context else kb_context

    prompt = f"""You are an expert agriculture tutor grading a student.

Question: {question}
User's Answer: {user_answer}

Relevant context (from media + knowledge base):
{combined_context}

Evaluate the user's answer.
State clearly "**CORRECT**" or "**INCORRECT**" on the very first line.
Then provide a warm, detailed explanation with key facts. Use bullet points where helpful. Keep it beginner-friendly."""

    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=MODEL_NAME,
        temperature=0.3,
    )
    return chat_completion.choices[0].message.content.strip()
