import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "payments.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            phone       TEXT    NOT NULL,
            group_name  TEXT    NOT NULL,
            monthly_fee INTEGER NOT NULL CHECK (monthly_fee >= 0),
            created_at  TEXT    NOT NULL DEFAULT (date('now'))
        );

        CREATE TABLE IF NOT EXISTS payments (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            amount     INTEGER NOT NULL CHECK (amount > 0),
            paid_at    TEXT    NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_payments_student_date
            ON payments (student_id, paid_at);
    """)
    conn.commit()
    conn.close()