import sqlite3

conn = sqlite3.connect("exam.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT,
    image_id TEXT,
    correct_answer TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS choices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER,
    choice TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS results (
    user_id INTEGER,
    score INTEGER,
    total INTEGER
)
""")

conn.commit()


def add_question(q_type, image_id, correct_answer, choices=None):
    cursor.execute(
        "INSERT INTO questions (type, image_id, correct_answer) VALUES (?, ?, ?)",
        (q_type, image_id, correct_answer)
    )
    q_id = cursor.lastrowid

    if choices:
        for c in choices:
            cursor.execute(
                "INSERT INTO choices (question_id, choice) VALUES (?, ?)",
                (q_id, c)
            )
    conn.commit()


def get_questions():
    cursor.execute("SELECT * FROM questions")
    return cursor.fetchall()


def get_choices(q_id):
    cursor.execute("SELECT choice FROM choices WHERE question_id=?", (q_id,))
    return [c[0] for c in cursor.fetchall()]
