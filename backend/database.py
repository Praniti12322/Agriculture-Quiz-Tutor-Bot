import sqlite3
from passlib.context import CryptContext

DB_FILE = "users.db"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_correct BOOLEAN NOT NULL,
            question_type TEXT DEFAULT 'text'
        )
    ''')
    # Migration: add question_type column if it doesn't exist (for existing DBs)
    try:
        cursor.execute("ALTER TABLE quiz_attempts ADD COLUMN question_type TEXT DEFAULT 'text'")
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_user(username: str, email: str, password: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                       (username, email, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user(username: str):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return dict(user) if user else None

def log_attempt(username: str, is_correct: bool, question_type: str = "text"):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO quiz_attempts (username, is_correct, question_type) VALUES (?, ?, ?)",
        (username, is_correct, question_type)
    )
    conn.commit()
    conn.close()

def get_user_progress(username: str):
    conn = get_db_connection()
    # Get total overview
    overview = conn.execute('''
        SELECT COUNT(*) as total_questions, 
               SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as total_correct 
        FROM quiz_attempts 
        WHERE username = ?
    ''', (username,)).fetchone()
    
    # Get daily chart data
    daily = conn.execute('''
        SELECT DATE(timestamp) as date,
               COUNT(*) as total_questions,
               SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as total_correct
        FROM quiz_attempts
        WHERE username = ?
        GROUP BY DATE(timestamp)
        ORDER BY date ASC
    ''', (username,)).fetchall()
    
    conn.close()
    
    return {
        "overview": dict(overview),
        "daily": [dict(d) for d in daily]
    }
