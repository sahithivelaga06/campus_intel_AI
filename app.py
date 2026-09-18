import os
import re
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

import streamlit as st
from dotenv import load_dotenv
from pypdf import PdfReader
from groq import Groq

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "college_helpdesk.db"
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
]

POPULAR_COLLEGES = [
    "-- Select College --",
    "Aditya Degree College, Kakinada",
    "Aditya Degree College, Rajahmundry",
    "Aditya Degree College, Visakhapatnam",
    "Aditya Engineering College, Surampalem",
    "Pithapur Rajah's Government College (PRGC), Kakinada",
    "Ideal College of Arts and Sciences, Kakinada",
    "MSN Degree College, Kakinada",
    "Andhra University (AU), Visakhapatnam",
    "JNTU Kakinada (JNTUK)",
    "Sri Venkateswara University (SVU), Tirupati",
    "Acharya Nagarjuna University (ANU), Guntur",
    "Christ University, Bengaluru",
    "Madras Christian College (MCC), Chennai",
    "Delhi University (DU), New Delhi",
    "IIT Madras",
    "IIT Bombay",
    "NIT Warangal",
    "Other / Custom College",
]

COLLEGE_CATEGORIES = [
    "Unknown / Not verified",
    "Government Autonomous College",
    "Government Non-Autonomous College",
    "Private Autonomous College",
    "Private Non-Autonomous College",
    "Aided Autonomous College",
    "Aided Non-Autonomous College",
    "Government University",
    "Private University",
    "Deemed University",
    "Government Engineering College",
    "Private Engineering College",
]

STUDENT_CATEGORIES = ["General", "OBC", "SC", "ST", "EWS", "Minority", "Other"]

COMMON_QUESTIONS = [
    "-- Select Common Question --",
    "What courses are offered?",
    "What subjects are taught each semester?",
    "What is the fee structure?",
    "What are the eligibility requirements?",
    "What scholarships may be available?",
    "What laboratory facilities are available?",
    "What placements and internships are reported?",
    "What are the library and college timings?",
    "What hostel and transport facilities are available?",
    "What is the official admission process?",
]

# ============================================================
# PAGE AND SIMPLE, READABLE UI
# ============================================================

st.set_page_config(
    page_title="Campus Intel AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
      --ink:#17345f; --muted:#7183a4; --line:#e2e9f7; --primary:#6657ed;
      --primary2:#8b7cff; --surface:rgba(255,255,255,.92);
    }
    .stApp {
      background: linear-gradient(135deg,#f8faff 0%,#edf5ff 52%,#fbf7ff 100%);
      color:var(--ink); overflow-x:hidden;
    }
    .stApp:before,.stApp:after {content:"";position:fixed;z-index:-1;border-radius:50%;pointer-events:none;}
    .stApp:before {width:420px;height:420px;right:-180px;top:-140px;background:radial-gradient(circle at 30% 35%,#d8eaff 0 22%,#e7ddff 55%,transparent 70%);opacity:.9;}
    .stApp:after {width:380px;height:380px;left:-190px;bottom:-80px;background:radial-gradient(circle at 55% 35%,#d5f4f0 0 25%,#dce4ff 52%,transparent 72%);opacity:.8;}
    .block-container {max-width:1080px!important;width:100%!important;margin:0 auto!important;padding:1.2rem 1.5rem 3rem;}
    h1,h2,h3,h4,h5,p,label,li {color:var(--ink)!important;}
    .top-brand {display:flex;align-items:center;gap:12px;margin:0 auto 18px;max-width:1080px;width:100%;flex-wrap:wrap;overflow:visible;}
    .brand-mark {width:48px;height:48px;border-radius:16px;background:linear-gradient(145deg,#dff0ff,#b9c9ff);display:flex;align-items:center;justify-content:center;font-size:25px;box-shadow:0 8px 22px #8099d522;}
    .brand-name {white-space:normal;overflow:visible;word-break:normal;font-size:1.25rem;font-weight:850;letter-spacing:-.03em;line-height:1.05;}
    .brand-sub {font-size:.72rem;color:#7183a4!important;margin-top:3px;}
    .hero {position:relative;overflow:hidden;border:1px solid #dce7fa;border-radius:28px;padding:2rem 2.4rem;margin:.8rem 0 1.2rem;background:linear-gradient(110deg,rgba(255,255,255,.98),rgba(239,246,255,.92));box-shadow:0 18px 55px #6279a514;min-height:190px;}
    .hero:before {content:"";position:absolute;width:300px;height:300px;right:-75px;top:-120px;border-radius:50%;background:linear-gradient(140deg,#d9f2ff,#e4d9ff);opacity:.8;}
    .hero:after {content:"✦  ˚  ✧";position:absolute;right:18%;top:23%;font-size:2.2rem;color:#7d8cff;letter-spacing:20px;transform:rotate(-12deg);}
    .hero-kicker {font-size:.72rem;font-weight:850;letter-spacing:.15em;text-transform:uppercase;color:#7568ed!important;position:relative;z-index:1;}
    .hero-title {font-size:2.55rem;font-weight:900;letter-spacing:-.055em;line-height:1.08;margin:.35rem 0 .6rem;position:relative;z-index:1;}
    .hero-copy {max-width:650px;font-size:1rem;color:var(--muted)!important;position:relative;z-index:1;}
    .script-note {font-family:cursive;font-style:italic;color:#7d8cff!important;font-size:1.45rem;line-height:1.1;transform:rotate(-7deg);position:absolute;right:26%;top:42px;z-index:2;}
    .illus-books {position:absolute;right:35px;bottom:12px;font-size:4.4rem;filter:drop-shadow(0 10px 10px #8aa3d522);opacity:.78;}
    .section-title {font-size:1.2rem;font-weight:850;margin:.3rem 0 .15rem;}
    .section-sub {font-size:.86rem;color:var(--muted)!important;margin-bottom:.9rem;}
    .feature-card {background:rgba(255,255,255,.88);border:1px solid #dfe7f6;border-radius:20px;padding:1.15rem;min-height:126px;box-shadow:0 8px 25px #647da612;transition:transform .2s ease;}
    .feature-card:hover {transform:translateY(-3px);}
    .feature-icon {width:44px;height:44px;border-radius:15px;display:flex;align-items:center;justify-content:center;font-size:1.55rem;background:linear-gradient(145deg,#e8edff,#d5f0ff);margin-bottom:.65rem;}
    .feature-title {font-weight:850;font-size:.96rem;}
    .small-note {font-size:.78rem;color:var(--muted)!important;line-height:1.45;}
    .panel {max-width:980px;margin-left:auto;margin-right:auto;background:var(--surface);border:1px solid var(--line);border-radius:22px;padding:1.25rem 1.4rem;box-shadow:0 10px 32px #647da60d;margin-bottom:1rem;}
    .step-strip {display:flex;gap:7px;flex-wrap:wrap;margin:.8rem 0 1rem;}
    .step-chip {padding:7px 12px;border:1px solid #dce5f7;border-radius:999px;background:#f8faff;font-size:.74rem;color:#7183a4;}
    .step-chip.active {background:#eceaff;color:#5c50d8;border-color:#d5d0ff;font-weight:800;}
    .chat-panel {background:rgba(255,255,255,.9);border:1px solid #dfe7f6;border-radius:22px;padding:1.1rem;box-shadow:0 10px 30px #647da610;}
    .chat-head {display:flex;align-items:center;gap:10px;border-bottom:1px solid #edf0f8;padding-bottom:.8rem;margin-bottom:.9rem;}
    .bot-avatar {width:42px;height:42px;border-radius:50%;background:linear-gradient(145deg,#d8f0ff,#c8c1ff);display:flex;align-items:center;justify-content:center;font-size:1.45rem;}
    .online {font-size:.7rem;color:#29a879!important;}
    .bubble {background:#f0f3ff;border-radius:16px 16px 16px 4px;padding:.85rem;font-size:.84rem;color:#3b5279!important;margin-bottom:.6rem;}
    .quick-question {border:1px solid #dce5f7;border-radius:999px;padding:.55rem .8rem;background:#fff;font-size:.75rem;color:#40577e!important;margin:.35rem 0;}
    input,textarea {background:#fff!important;color:#172b4d!important;border-radius:12px!important;border:1px solid #d4dff1!important;}
    input::placeholder,textarea::placeholder {color:#91a0b8!important;opacity:1!important;}
    div[data-baseweb="select"]>div {background:#fff!important;border:1px solid #d4dff1!important;border-radius:12px!important;}
    div[data-baseweb="select"] span,div[data-baseweb="select"] input,div[data-baseweb="select"] svg {color:#172b4d!important;fill:#172b4d!important;}
    div[data-baseweb="popover"],div[data-baseweb="menu"],ul[data-baseweb="menu"],li[role="option"],div[role="option"] {background:#fff!important;color:#172b4d!important;}
    li[role="option"]:hover,div[role="option"]:hover {background:#eef2ff!important;}
    .stButton>button {border:0!important;border-radius:12px!important;background:linear-gradient(100deg,#6657ed,#8173ff)!important;color:#fff!important;font-weight:800!important;min-height:2.65rem;box-shadow:0 8px 18px #6657ed2b;}
    .stButton>button:hover {background:linear-gradient(100deg,#5143d1,#6b5cf0)!important;transform:translateY(-1px);}
    .secondary-button .stButton>button {background:#eef0ff!important;color:#5b50d7!important;box-shadow:none!important;}
    [data-testid="stSidebar"] {background:linear-gradient(180deg,#fff,#f3f5ff)!important;border-right:1px solid #e0e7f6;}
    [data-testid="stSidebar"] * {color:var(--ink)!important;}
    [data-testid="stSidebar"] .stButton>button {background:#eceaff!important;color:#5549d0!important;box-shadow:none!important;}
    div[data-testid="stForm"] {max-width:980px;margin:0 auto 1rem!important;background:rgba(255,255,255,.95);border:1px solid #dfe7f6;border-radius:22px;padding:1.35rem;box-shadow:0 15px 38px #647da612;}
    .auth-shell {border:1px solid #dfe7f6;border-radius:28px;background:rgba(255,255,255,.72);padding:1.4rem;box-shadow:0 18px 55px #647da614;}
    .footer-note {font-size:.75rem;color:#8a9ab5!important;text-align:center;margin-top:1.5rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# DATABASE
# ============================================================

def get_connection():
    connection = sqlite3.connect(str(DB_FILE))
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL DEFAULT 'Student',
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                college_name TEXT NOT NULL,
                department TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                college_name TEXT NOT NULL,
                filename TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS college_information (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                college_name TEXT NOT NULL,
                college_type TEXT NOT NULL,
                location TEXT,
                official_url TEXT,
                courses TEXT,
                fee_information TEXT,
                verified_date TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scholarships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scholarship_name TEXT NOT NULL,
                provider TEXT,
                student_category TEXT NOT NULL,
                eligibility TEXT,
                amount_information TEXT,
                official_url TEXT,
                verified_date TEXT
            )
        """)
        # Safe migration for databases created by an older version.
        cur.execute("PRAGMA table_info(users)")
        columns = {row[1] for row in cur.fetchall()}
        if "name" not in columns:
            cur.execute("ALTER TABLE users ADD COLUMN name TEXT DEFAULT 'Student'")
        conn.commit()


init_db()

# ============================================================
# AUTHENTICATION
# ============================================================

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def register_user(name, email, password):
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name.strip(), email.strip().lower(), hash_password(password)),
            )
        return True, "Account created. You can now sign in."
    except sqlite3.IntegrityError:
        return False, "This email address is already registered."
    except Exception as error:
        return False, f"Registration error: {error}"


def authenticate_user(email, password):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE LOWER(email)=LOWER(?)",
            (email.strip(),),
        ).fetchone()
    if row and row[1] == hash_password(password):
        return row[0]
    return None


def get_user_name(user_id):
    with get_connection() as conn:
        row = conn.execute("SELECT name FROM users WHERE id=?", (user_id,)).fetchone()
    return row[0] if row and row[0] else "Student"

# ============================================================
# DATABASE OPERATIONS
# ============================================================

def save_chat(user_id, college, department, question, answer):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO chat_history
            (user_id, college_name, department, question, answer)
            VALUES (?, ?, ?, ?, ?)""",
            (user_id, college, department, question, answer),
        )


def get_user_chats(user_id):
    with get_connection() as conn:
        return conn.execute(
            """SELECT college_name, department, question, answer, created_at
            FROM chat_history WHERE user_id=? ORDER BY id DESC""",
            (user_id,),
        ).fetchall()


def save_document(college_name, filename, content):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO documents (college_name, filename, content) VALUES (?, ?, ?)",
            (college_name, filename, content),
        )


def get_college_docs(college_name):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT content FROM documents WHERE LOWER(college_name)=LOWER(?)",
            (college_name,),
        ).fetchall()
    return "\n\n".join(row[0] for row in rows)


def get_college_information(college_name):
    with get_connection() as conn:
        return conn.execute(
            """SELECT college_name, college_type, location, official_url,
            courses, fee_information, verified_date
            FROM college_information WHERE LOWER(college_name) LIKE LOWER(?)""",
            (f"%{college_name}%",),
        ).fetchall()


def get_scholarship_information(student_category):
    with get_connection() as conn:
        return conn.execute(
            """SELECT scholarship_name, provider, student_category,
            eligibility, amount_information, official_url, verified_date
            FROM scholarships
            WHERE student_category=? OR student_category='All'""",
            (student_category,),
        ).fetchall()

# ============================================================
# SEARCH AND AI
# ============================================================

def get_groq_client():
    key = os.getenv("GROQ_API_KEY", "").strip()
    return Groq(api_key=key) if key else None


def perform_web_search(query, max_results=8):
    """Return search snippets as context. Snippets are not treated as proof."""
    try:
        results = list(DDGS().text(query, max_results=max_results))
        if not results:
            return "No search results returned."
        output = []
        for item in results:
            url = item.get("href", "") or item.get("url", "")
            domain = urlparse(url).netloc.lower().removeprefix("www.")
            output.append(
                f"Title: {item.get('title', '')}\n"
                f"Snippet: {item.get('body', '')}\n"
                f"URL: {url}\n"
                f"Domain: {domain}\n"
            )
        return "\n".join(output)
    except Exception as error:
        return f"Search unavailable: {error}"


def extract_json_array(text):
    cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    match = re.search(r"\[[\s\S]*\]", cleaned)
    if not match:
        return []
    try:
        value = json.loads(match.group(0))
        return [str(x) for x in value if str(x).strip()]
    except json.JSONDecodeError:
        return []


def fetch_college_departments(college_name):
    """Fetch a hierarchical academic structure: department -> programme -> specialization."""
    search_queries = [
        f'"{college_name}" official departments programmes courses branches specializations',
        f'"{college_name}" prospectus syllabus departments PDF',
        f'"{college_name}" academic programmes BCA BCom BSc BBA BTech'
    ]
    context_parts = [perform_web_search(q, max_results=6) for q in search_queries]
    context = "\n\n--- NEXT SEARCH ---\n\n".join(context_parts)
    client = get_groq_client()

    if client:
        prompt = f"""
You are an academic information extraction engine.
Institution: {college_name}

Search context:
{context[:50000]}

Task:
Extract every department, degree/programme, branch and specialization that is actually supported by the context.
Represent each item as one readable string using this format:
Department: <department> | Programme: <degree/programme> | Specialization/Branch: <specialization or None>

Rules:
- Include separate entries for separate programmes and branches.
- Include sub-departments, specializations, streams and branches when the source mentions them.
- Do not add common departments just because they exist in other colleges.
- Do not confuse a university's departments with an affiliated college's departments.
- If the evidence is incomplete, include only supported entries and append '| Evidence: confirm from official source'.
- Return only a JSON array of strings.
"""
        for model in GROQ_MODELS:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                )
                values = extract_json_array(response.choices[0].message.content)
                cleaned = []
                for value in values:
                    value = re.sub(r"^[-•*]\s*", "", value).strip()
                    if value and value not in cleaned:
                        cleaned.append(value)
                if cleaned:
                    return cleaned[:60]
            except Exception:
                continue

    return [
        "Department/programme structure could not be extracted - verify using the official prospectus"
    ]

def answer_college_query(college_name, department, question, college_type, student_category, doc_text=""):
    client = get_groq_client()
    if not client:
        return "**Configuration needed:** Add `GROQ_API_KEY=your_key_here` to `.env` and restart Streamlit."

    # Use several targeted searches instead of one narrow search. This gives the model
    # more opportunities to find syllabus, fees, branches and official notices.
    search_queries = [
        f'"{college_name}" "{department}" "{question}" official',
        f'"{college_name}" "{department}" syllabus subjects semester',
        f'"{college_name}" "{department}" fee structure admission eligibility',
        f'"{college_name}" "{department}" specialization branch curriculum prospectus'
    ]
    web_context = "\n\n--- SEARCH ---\n\n".join(
        perform_web_search(query, max_results=6) for query in search_queries
    )
    college_records = get_college_information(college_name)
    scholarship_records = get_scholarship_information(student_category)

    system_prompt = f"""
You are Campus Intel AI, a practical academic helpdesk assistant.
Institution: {college_name}
Selected college type: {college_type}
Selected academic path: {department}
Student category: {student_category}

Your goal is to give a useful answer, not merely say 'not available'.

Strict rules:
1. Keep the answer limited to the selected academic path. Never mix another degree,
   department, branch or specialization into its fees, subjects or syllabus.
2. First use information from uploaded documents, local database records and official
   college/university/government sources.
3. Give the most useful supported details available: department, programme, branches,
   specializations, semester subjects, admission route, eligibility, fee components,
   scholarships and next verification steps, depending on the question.
4. Separate the answer into these labels when appropriate:
   - Confirmed from supplied/official information
   - Reported online; verify before relying on it
   - General guidance (not college-specific)
   - Missing or conflicting information
5. Search snippets alone are not proof. Do not call snippets verified.
6. If an exact fee, subject or deadline is unavailable, do not stop at one sentence.
   Explain what is known, provide a clearly labelled general explanation only when useful,
   and tell the user exactly which official document/page should be checked.
7. Never invent exact numbers, subjects, deadlines, rankings, placement statistics or
   scholarship amounts. Estimates are allowed only when the user asks for an estimate;
   label the estimate and explain that it is not an official figure.
8. For a department with sub-branches or specializations, explain their differences and
   keep each detail attached to the correct branch.
9. Include source URLs from the search context when available.
10. Use plain readable headings, tables where helpful, and short bullet points.
"""

    user_prompt = f"""
Question: {question}
Selected academic path (strict filter): {department}

Uploaded college documents:
{doc_text[:35000]}

Local college database records:
{college_records}

Local scholarship records for {student_category}:
{scholarship_records}

Live search context:
{web_context[:45000]}

Answer the question directly. If exact college-specific evidence is missing, still provide
useful general guidance separately and explain how the student can verify the exact detail.
"""

    last_error = "Unknown error"
    for model in GROQ_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
            return response.choices[0].message.content
        except Exception as error:
            last_error = str(error)
    return f"The AI request failed: {last_error}"


# ============================================================
# GENERAL CHATBOT
# ============================================================
def answer_general_chat(question, active_field=""):
    client = get_groq_client()
    if not client:
        return "**Configuration needed:** Add `GROQ_API_KEY=your_key_here` to `.env` and restart Streamlit."

    taxonomy_context = json.dumps(ACADEMIC_TAXONOMY, ensure_ascii=False, default=list)[:30000]
    prompt = f"""
You are Campus Intel AI, a friendly college and career guidance chatbot.
The user may ask about academic fields, streams, departments, courses, eligibility,
subjects, careers, admissions or general college guidance.
Current selected field, if any: {active_field or 'None'}
Academic taxonomy for context:
{taxonomy_context}

Rules:
- Answer the user's question directly in simple language.
- If the question is college-specific but no college is selected, explain that the user
  should select a college for exact official details, while still giving clearly labelled
  general guidance when useful.
- Do not invent college-specific fees, deadlines, subjects, rankings or admission rules.
- Distinguish general guidance from information that must be verified officially.
- Use headings and short bullets. Never answer only 'not available' when useful guidance is possible.

User question: {question}
"""
    last_error = "Unknown error"
    for model in GROQ_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.25,
            )
            return response.choices[0].message.content
        except Exception as error:
            last_error = str(error)
    return f"The chatbot request failed: {last_error}"

# ============================================================
# SESSION STATE
# ============================================================

DEFAULTS = {
    "user_id": None,
    "user_email": None,
    "user_name": "Student",
    "auth_mode": "signin",
    "loaded_college": "",
    "departments": [],
    "last_answer": "",
    "active_field": "",
    "chat_messages": [],
    "chatbot_question": "",
    "sidebar_question": "",
    "page": "dashboard",
}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ============================================================
# AUTH PAGE
# ============================================================

def render_auth_page():
    st.markdown(
        """
        <div class="top-brand"><div class="brand-mark">🎓</div><div><div class="brand-name">Campus Intel AI</div><div class="brand-sub">Your College & Career Guide</div></div></div>
        <div class="hero">
          <div class="hero-kicker">Your academic companion</div>
          <div class="hero-title">Dream. Explore. Achieve. ✨</div>
          <div class="hero-copy">Explore colleges, discover courses, understand eligibility and ask an AI guide for clear academic direction — all in one friendly workspace.</div>
          <div class="script-note">Your future<br/>starts here ♡</div><div class="illus-books">📚</div>
        </div>
        """, unsafe_allow_html=True)
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        st.markdown("<div class='section-title'>Everything you need to plan your next step</div><div class='section-sub'>Explore academic fields, compare college information and keep your guidance in one place.</div>", unsafe_allow_html=True)
        cards=[("🔎","Explore colleges","Find college and course information in one place."),("🧭","Choose your academic path","Move from field to stream, department, course and specialization."),("🤖","Ask the AI guide","Get structured answers with verification reminders."),("📚","Save your conversations","Keep your questions and answers inside your account.")]
        cols=st.columns(2)
        for i,(ico,title,desc) in enumerate(cards):
            with cols[i%2]:
                st.markdown(f"<div class='feature-card'><div class='feature-icon'>{ico}</div><div class='feature-title'>{title}</div><div class='small-note'>{desc}</div></div>",unsafe_allow_html=True)
        st.markdown("<div class='panel'><b>💡 Helpful reminder</b><div class='small-note'>Confirm fees, deadlines, eligibility and course availability using the official college or government source.</div></div>",unsafe_allow_html=True)
    with right:
        st.markdown("<div class='auth-shell'>",unsafe_allow_html=True)
        st.markdown("### Welcome to your workspace")
        st.caption("Sign in to continue or create a new account. Both screens use the same Campus Intel AI theme.")
        a,b=st.columns(2)
        with a:
            if st.button("Sign In",use_container_width=True): st.session_state.auth_mode="signin"; st.rerun()
        with b:
            if st.button("Sign Up",use_container_width=True): st.session_state.auth_mode="signup"; st.rerun()
        if st.session_state.auth_mode=="signup":
            st.markdown("#### Create your account")
            with st.form("signup_form"):
                name=st.text_input("Full name"); email=st.text_input("Email address"); password=st.text_input("Password",type="password"); confirm=st.text_input("Confirm password",type="password"); submit=st.form_submit_button("Create Account",use_container_width=True)
            if submit:
                if not name.strip() or not email.strip() or not password: st.warning("Complete all fields.")
                elif len(password)<6: st.warning("Password must contain at least 6 characters.")
                elif password!=confirm: st.error("Passwords do not match.")
                else:
                    success,message=register_user(name,email,password)
                    if success: st.success(message); st.session_state.auth_mode="signin"
                    else: st.error(message)
        else:
            st.markdown("#### Sign in to your workspace")
            with st.form("signin_form"):
                email=st.text_input("Email address"); password=st.text_input("Password",type="password"); submit=st.form_submit_button("Sign In",use_container_width=True)
            if submit:
                if not email.strip() or not password: st.warning("Enter both email and password.")
                else:
                    user_id=authenticate_user(email,password)
                    if user_id:
                        st.session_state.user_id=user_id; st.session_state.user_email=email.strip().lower(); st.session_state.user_name=get_user_name(user_id); st.rerun()
                    else: st.error("Invalid email or password.")
        st.markdown("</div>",unsafe_allow_html=True)
    st.markdown("<div class='footer-note'>Campus Intel AI · Explore wisely and verify important information from official sources.</div>",unsafe_allow_html=True)


def parse_academic_records(items):
    """Parse AI records into structured rows for genuinely cascading dropdowns."""
    records = []
    for item in items or []:
        values = {}
        for part in str(item).split("|"):
            if ":" in part:
                key, value = part.split(":", 1)
                values[key.strip().lower()] = value.strip()
        department = values.get("department") or "General / Not available"
        programme = values.get("programme") or values.get("degree") or "All programmes"
        specialization = (
            values.get("specialization/branch")
            or values.get("specialization")
            or values.get("branch")
            or "No specific branch"
        )
        if department.lower() in {"none", "unknown"}:
            department = "General / Not available"
        if programme.lower() in {"none", "unknown"}:
            programme = "All programmes"
        if specialization.lower() in {"none", "unknown"}:
            specialization = "No specific branch"
        row = {"department": department, "programme": programme, "specialization": specialization}
        if row not in records:
            records.append(row)
    if not records:
        records = [{"department": "General / Not available", "programme": "All programmes", "specialization": "No specific branch"}]
    return records


def related_field_options(department, programme):
    """Provide useful related academic fields when a college source does not list branches."""
    text = f"{department} {programme}".lower()
    groups = {
        "computer": ["Computer Applications", "Computer Science", "Information Technology", "Data Science", "Artificial Intelligence", "Cyber Security", "Cloud Computing", "Software Development", "Web Development", "Networking"],
        "bca": ["Computer Applications", "Data Analytics", "Artificial Intelligence", "Cyber Security", "Cloud Computing", "Web Development", "Software Development"],
        "science": ["Mathematics", "Statistics", "Physics", "Chemistry", "Botany", "Zoology", "Computer Science", "Data Science", "Biotechnology"],
        "commerce": ["Accounting", "Finance", "Banking and Insurance", "Taxation", "Business Analytics", "E-Commerce", "Corporate Accounting"],
        "management": ["Finance", "Marketing", "Human Resources", "Business Analytics", "Operations", "International Business", "Entrepreneurship"],
        "engineering": ["Computer Science and Engineering", "Information Technology", "Artificial Intelligence and Machine Learning", "Data Science", "Cyber Security", "Electronics and Communication", "Electrical and Electronics", "Mechanical", "Civil"],
        "arts": ["English", "Economics", "History", "Political Science", "Psychology", "Sociology", "Journalism and Mass Communication"],
    }
    chosen=[]
    for key, values in groups.items():
        if key in text:
            chosen.extend(values)
    if not chosen:
        chosen = ["General / No branch specified", "Core subjects", "Applied / Practical subjects", "Skill-based electives", "Project / Internship area", "Career-oriented specialization"]
    return list(dict.fromkeys(chosen))


# ============================================================
# BROAD ACADEMIC TAXONOMY
# ============================================================
ACADEMIC_TAXONOMY = {
    "Arts & Humanities": {
        "Languages & Literature": {"English", "Telugu", "Hindi", "Foreign Languages", "Comparative Literature"},
        "Social Sciences": {"Economics", "History", "Political Science", "Psychology", "Sociology", "Public Administration"},
        "Media & Communication": {"Journalism", "Mass Communication", "Advertising", "Film & Television"},
        "Fine Arts": {"Visual Arts", "Painting", "Applied Arts", "Music", "Dance", "Theatre"},
    },
    "Commerce & Business": {
        "Commerce": {"B.Com General", "Accounting", "Corporate Accounting", "Computer Applications", "Taxation", "Banking & Insurance"},
        "Business & Management": {"BBA", "Marketing", "Finance", "Human Resources", "Business Analytics", "International Business", "Entrepreneurship", "Operations"},
        "Economics": {"BA Economics", "Applied Economics", "Financial Economics", "Econometrics"},
    },
    "Fashion, Design & Creative": {
        "Fashion": {"Fashion Design", "Fashion Technology", "Textile Design", "Fashion Merchandising", "Apparel Production"},
        "Design": {"Graphic Design", "UI/UX Design", "Interior Design", "Product Design", "Industrial Design", "Animation", "Game Design"},
        "Architecture & Planning": {"Architecture", "Interior Architecture", "Urban Planning", "Landscape Design"},
    },
    "Engineering & Technology": {
        "Software / Computing": {"CSE", "CSE (AI & ML)", "CSE (Data Science)", "Artificial Intelligence", "Machine Learning", "Data Science", "Information Technology", "Software Engineering", "Cyber Security", "Cloud Computing", "Computer Applications", "Internet of Things", "Blockchain", "Computer Networks"},
        "Hardware / Electronics": {"Electronics & Communication Engineering", "Electrical & Electronics Engineering", "Electrical Engineering", "VLSI Design", "Embedded Systems", "Instrumentation & Control", "Telecommunication"},
        "Core Engineering": {"Mechanical Engineering", "Civil Engineering", "Chemical Engineering", "Automobile Engineering", "Aerospace Engineering", "Biotechnology Engineering", "Industrial Engineering", "Mining Engineering", "Agricultural Engineering"},
        "Emerging Technology": {"Robotics", "Mechatronics", "Renewable Energy", "Artificial Intelligence & Robotics", "Computer Engineering"},
    },
    "Medical & Health Sciences": {
        "Medicine": {"MBBS", "MD", "MS", "Medical Laboratory Technology"},
        "Dental": {"BDS", "MDS"},
        "Nursing": {"B.Sc Nursing", "GNM", "ANM"},
        "Pharmacy": {"B.Pharm", "M.Pharm", "Pharm.D"},
        "Allied Health": {"Physiotherapy", "Radiology", "Medical Imaging", "Optometry", "Operation Theatre Technology", "Cardiac Care", "Nutrition & Dietetics"},
    },
    "Science": {
        "Physical Sciences": {"Physics", "Chemistry", "Mathematics", "Statistics"},
        "Life Sciences": {"Botany", "Zoology", "Biotechnology", "Microbiology", "Biochemistry", "Genetics"},
        "Computer & Data Sciences": {"Computer Science", "Data Science", "Artificial Intelligence", "Information Science"},
        "Environmental Sciences": {"Environmental Science", "Geology", "Geography", "Climate Science"},
    },
    "Law & Legal Studies": {
        "Law": {"LLB", "BA LLB", "BBA LLB", "LLM", "Corporate Law", "Criminal Law", "Constitutional Law"},
    },
    "Education": {
        "Teacher Education": {"B.Ed", "D.El.Ed", "M.Ed", "Special Education", "Physical Education"},
    },
    "Agriculture & Veterinary": {
        "Agriculture": {"B.Sc Agriculture", "Horticulture", "Agricultural Engineering", "Agribusiness", "Food Technology"},
        "Veterinary": {"BVSc & AH", "Animal Husbandry", "Dairy Technology", "Fisheries Science"},
    },
    "Hospitality, Travel & Tourism": {
        "Hospitality": {"Hotel Management", "Culinary Arts", "Food Production", "Hospitality Administration"},
        "Travel & Tourism": {"Tourism Management", "Travel Management", "Aviation & Airport Management"},
    },
    "Interdisciplinary & Vocational": {
        "Skill-Based Programmes": {"Animation", "Multimedia", "Digital Marketing", "Logistics", "Retail Management", "Event Management", "Library Science", "Social Work"},
    },
}

def taxonomy_options():
    fields = list(ACADEMIC_TAXONOMY.keys())
    return fields

def taxonomy_streams(field):
    return list(ACADEMIC_TAXONOMY.get(field, {}).keys())

def taxonomy_courses(field, stream):
    return sorted(ACADEMIC_TAXONOMY.get(field, {}).get(stream, set()))

# ============================================================
# DASHBOARD
# ============================================================

def render_dashboard():
    """Render a clear two-level experience: dashboard -> field page, with chatbot isolated in sidebar."""
    if "page" not in st.session_state:
        st.session_state.page = "dashboard"
    if "chat_open" not in st.session_state:
        st.session_state.chat_open = False

    # -------------------- Header --------------------
    st.markdown(
        f"""
        <div class='top-brand'>
          <div class='brand-mark'>🎓</div>
          <div><div class='brand-name'>Campus Intel AI</div>
          <div class='brand-sub'>Your College & Career Guide</div></div>
          <div style='margin-left:auto;text-align:right;'>
            <div style='font-size:.78rem;color:#7183a4;'>Signed in as</div>
            <div style='font-weight:800;color:#17345f;white-space:normal;overflow:visible;'>{st.session_state.user_name or 'Student'}</div>
          </div>
        </div>
        """, unsafe_allow_html=True
    )
    head_left, head_right = st.columns([5, 1])
    with head_right:
        if st.button("Sign out", use_container_width=True):
            for key, value in DEFAULTS.items():
                st.session_state[key] = value
            st.session_state.page = "dashboard"
            st.rerun()

    # -------------------- Gemini-style assistant drawer --------------------
    with st.sidebar:
        st.markdown("## 🤖 Campus Intel AI")
        st.caption("Your separate AI assistant")
        st.info("Ask general questions here. College selection and the main college question form stay on the dashboard.")
        quick_questions = [
            "Explain CSE, AI & ML and Data Science",
            "What can I study after 12th Commerce?",
            "What is the difference between MBBS and B.Sc Nursing?",
        ]
        for idx, quick in enumerate(quick_questions):
            if st.button(quick, key=f"sidebar_quick_{idx}", use_container_width=True):
                st.session_state.sidebar_question = quick
                st.rerun()
        sidebar_question = st.text_area(
            "Ask Gemini-style AI",
            value=st.session_state.get("sidebar_question", ""),
            placeholder="Ask a general academic or career question...",
            height=130,
            key="sidebar_chat_input",
        )
        if st.button("Send question", type="primary", use_container_width=True):
            if not sidebar_question.strip():
                st.warning("Type a question first.")
            else:
                with st.spinner("Preparing answer..."):
                    reply = answer_general_chat(sidebar_question.strip(), st.session_state.get("active_field", ""))
                st.session_state.chat_messages.append((sidebar_question.strip(), reply))
                st.session_state.sidebar_question = ""
                st.rerun()
        if st.session_state.chat_messages:
            st.markdown("### Conversation")
            for user_message, bot_reply in st.session_state.chat_messages[-8:]:
                st.markdown(f"**You**  \n{user_message}")
                st.markdown(f"**Campus Intel AI**  \n{bot_reply}")
                st.divider()
        st.caption("The assistant is separate from the college information form.")

    st.markdown(
        """
        <div class='hero'>
          <div class='hero-kicker'>College discovery · Course guidance · AI helpdesk</div>
          <div class='hero-title'>Welcome to Campus Intel AI ✨</div>
          <div class='hero-copy'>Choose an academic field first. Then explore its page, select a college and ask a focused question below.</div>
          <div class='script-note'>Dream<br/>Explore<br/>Achieve ♡</div><div class='illus-books'>🎓📚</div>
        </div>
        """, unsafe_allow_html=True
    )

    # -------------------- Field page --------------------
    cards = [
        ("🎨", "Arts & Humanities", "Languages, history, psychology, media and fine arts."),
        ("💼", "Commerce & Business", "Accounting, finance, management and economics."),
        ("👗", "Fashion, Design & Creative", "Fashion, textile, interior, graphic and product design."),
        ("⚙️", "Engineering & Technology", "Software, hardware, core and emerging technologies."),
        ("🩺", "Medical & Health Sciences", "Medicine, nursing, pharmacy, dental and allied health."),
        ("🧪", "Science", "Physics, chemistry, mathematics, biology and data sciences."),
        ("⚖️", "Law & Legal Studies", "Law degrees, legal practice and specializations."),
        ("🌾", "Agriculture & Veterinary", "Agriculture, veterinary science, food and rural studies."),
        ("🏨", "Hospitality & Tourism", "Hotel management, culinary arts, travel and tourism."),
    ]

    if st.session_state.page == "field":
        field = st.session_state.get("active_field", "")
        back_col, title_col = st.columns([1, 5])
        with back_col:
            if st.button("← Dashboard", use_container_width=True):
                st.session_state.page = "dashboard"
                st.rerun()
        with title_col:
            st.markdown(f"## {field}")
            st.caption("This is a separate field page. Select a stream to see example courses and related study paths.")
        streams = ACADEMIC_TAXONOMY.get(field, {})
        if not streams:
            st.warning("This field is not yet included in the academic catalogue.")
        else:
            for stream, courses in streams.items():
                with st.expander(stream, expanded=True):
                    course_cols = st.columns(2)
                    for idx, course in enumerate(sorted(courses)):
                        with course_cols[idx % 2]:
                            st.markdown(f"- {course}")
        st.info("These are exploration examples. Confirm exact courses offered by a particular college using its official prospectus.")
        st.markdown("### Continue with college-specific guidance")

    else:
        st.markdown("<div class='section-title'>Explore by Academic Field</div><div class='section-sub'>Click a card to open a dedicated field page. The main college question form is kept separately below the dashboard.</div>", unsafe_allow_html=True)
        cols = st.columns(3)
        for i, (ico, title, desc) in enumerate(cards):
            with cols[i % 3]:
                st.markdown(
                    f"<div class='feature-card'><div class='feature-icon'>{ico}</div><div class='feature-title'>{title}</div><div class='small-note'>{desc}</div></div>",
                    unsafe_allow_html=True,
                )
                if st.button(f"Open {title} →", key=f"open_field_{i}", use_container_width=True):
                    st.session_state.active_field = title
                    st.session_state.selected_field = title
                    st.session_state.page = "field"
                    st.session_state.last_answer = ""
                    st.rerun()
        st.markdown("<div class='panel'><b>How to use this dashboard</b><div class='small-note'>1. Open a field page. 2. Return to the dashboard. 3. Fill in the college and academic path. 4. Read the answer below the form. 5. Use the separate AI assistant from the sidebar for general questions.</div></div>", unsafe_allow_html=True)

    # -------------------- Main college problem form --------------------
    st.markdown("## 🎓 College Information Workspace")
    st.caption("This is the main problem statement area. All college-related inputs are large, clear and kept together below the dashboard.")
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.markdown("### 1. Select college details")
    student_category = st.selectbox("Student category", STUDENT_CATEGORIES, key="student_category_main")
    college_type = st.selectbox("College type", COLLEGE_CATEGORIES, key="college_type_main")
    selected = st.selectbox("College", POPULAR_COLLEGES, key="main_college")
    custom = ""
    if selected == "Other / Custom College":
        custom = st.text_input("Enter college name", key="main_custom")
    final_college = custom.strip() if selected == "Other / Custom College" else (selected if selected != "-- Select College --" else "")
    if st.button("Fetch College Departments", use_container_width=True):
        if not final_college:
            st.warning("Select or enter a college name first.")
        else:
            with st.spinner("Finding possible departments and programmes..."):
                st.session_state.departments = fetch_college_departments(final_college)
                st.session_state.loaded_college = final_college
            st.success("College data loaded. Now choose the academic path.")

    st.markdown("### 2. Choose the academic path")
    st.caption("Select only the field, department and course. Stream and specialization are intentionally removed to keep the form simple.")
    field_options = ["-- Select Broad Field --"] + taxonomy_options()
    current_field = st.session_state.get("active_field", "")
    default_field_index = field_options.index(current_field) if current_field in field_options else 0
    selected_field = st.selectbox("Broad field", field_options, index=default_field_index, key="selected_field_main")

    academic_records = parse_academic_records(st.session_state.departments) if st.session_state.loaded_college else []
    fetched_departments = sorted({r["department"] for r in academic_records if r["department"] not in {"General / Not available"}})
    department_options = ["-- Select Department --"]
    if selected_field != "-- Select Broad Field --":
        department_options += taxonomy_streams(selected_field)
    department_options += [d for d in fetched_departments if d not in department_options]
    selected_department = st.selectbox("Department", list(dict.fromkeys(department_options)), key="selected_department_main")

    course_options = ["-- Select Course / Branch --"]
    if selected_field != "-- Select Broad Field --" and selected_department != "-- Select Department --":
        course_options += taxonomy_courses(selected_field, selected_department)
    matching_courses = sorted({r["programme"] for r in academic_records if r["department"] == selected_department and r["programme"].strip().lower() not in {"none", "unknown"}})
    course_options += [c for c in matching_courses if c not in course_options]
    selected_course = st.selectbox("Course / Branch", list(dict.fromkeys(course_options)), key="selected_course_main")
    department = f"Broad Field: {selected_field} | Department: {selected_department} | Course/Branch: {selected_course}"

    st.markdown("### 3. Ask one focused college question")
    common = st.selectbox("Choose a common question", COMMON_QUESTIONS, key="common_question_main")
    custom_question = st.text_area("Your college question", placeholder="Example: What are the eligibility rules and semester subjects for this selected course?", height=130, key="college_question_main")
    question = custom_question.strip() or (common if common != "-- Select Common Question --" else "")
    if st.button("Get College Information", type="primary", use_container_width=True):
        if not final_college:
            st.warning("Select a college first.")
        elif not question:
            st.warning("Choose a common question or write your own question.")
        else:
            with st.spinner("Searching and preparing a structured answer..."):
                docs = get_college_docs(st.session_state.loaded_college)
                answer = answer_college_query(st.session_state.loaded_college, department, question, college_type, student_category, docs)
                st.session_state.last_answer = answer
                save_chat(st.session_state.user_id, st.session_state.loaded_college, department, question, answer)
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # -------------------- Answer area below all fields --------------------
    st.markdown("## 📌 College Information Result")
    if st.session_state.last_answer:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown(st.session_state.last_answer)
        st.caption("Confirm important details such as fees, deadlines, eligibility and course availability using the official college source.")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Your college-specific answer will appear here after you submit the form above.")

    if st.session_state.loaded_college:
        st.markdown("### Follow-up about the selected college")
        follow_up = st.text_area("Follow-up question", key="follow_up_main", height=100, placeholder="Ask one additional question about the selected college...")
        if st.button("Ask College Follow-up", use_container_width=True):
            if not follow_up.strip():
                st.warning("Write a follow-up question first.")
            else:
                with st.spinner("Preparing follow-up answer..."):
                    docs = get_college_docs(st.session_state.loaded_college)
                    answer = answer_college_query(st.session_state.loaded_college, department, follow_up.strip(), college_type, student_category, docs)
                    st.session_state.last_answer = answer
                    save_chat(st.session_state.user_id, st.session_state.loaded_college, department, follow_up.strip(), answer)
                st.rerun()

    with st.expander("🕘 Search History"):
        rows = get_user_chats(st.session_state.user_id)
        if not rows:
            st.info("No saved questions yet.")
        else:
            for college, department_text, question_text, answer_text, created_at in rows:
                with st.expander(f"{college} | {question_text}"):
                    st.caption(f"Academic path: {department_text} | {created_at}")
                    st.markdown(answer_text)

# ============================================================
# ROUTER
# ============================================================

if st.session_state.user_id is None:
    render_auth_page()
else:
    render_dashboard()
