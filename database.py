"""
database.py
------------
All SQLite database logic for NewsX. SQLite needs no separate server -
it's just a file called newsx.db created automatically on first run.
"""

import sqlite3
from datetime import datetime, date

DB_NAME = "newsx.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            image_url TEXT,
            source TEXT,
            url TEXT,
            published_at TEXT,
            fetch_date TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            article_id TEXT NOT NULL,
            bookmarked_at TEXT NOT NULL,
            UNIQUE(user_id, article_id),
            FOREIGN KEY (article_id) REFERENCES articles(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS seen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            article_id TEXT NOT NULL,
            action TEXT NOT NULL,
            seen_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            avatar_emoji TEXT DEFAULT '🙂',
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            article_id TEXT NOT NULL,
            liked_at TEXT NOT NULL,
            UNIQUE(user_id, article_id)
        )
    """)

    conn.commit()
    conn.close()


# ---------- USERS / AUTH ----------

def create_user(username, password_hash, avatar_emoji="🙂"):
    conn = get_connection()
    conn.execute(
        "INSERT INTO users (username, password_hash, avatar_emoji, created_at) VALUES (?, ?, ?, ?)",
        (username, password_hash, avatar_emoji, datetime.now().strftime("%Y-%m-%d %H:%M")),
    )
    conn.commit()
    user_id = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()[0]
    conn.close()
    return user_id


def get_user_by_username(username):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return row


def get_user_by_id(user_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row


# ---------- ARTICLES / CACHE ----------

def get_cached_articles(category):
    """Return today's cached articles for a category, if any."""
    conn = get_connection()
    today = date.today().isoformat()
    rows = conn.execute(
        "SELECT * FROM articles WHERE category = ? AND fetch_date = ? ORDER BY published_at DESC",
        (category, today),
    ).fetchall()
    conn.close()
    return rows


def save_articles(category, articles):
    """articles: list of dicts with id, title, summary, image_url, source, url, published_at"""
    conn = get_connection()
    today = date.today().isoformat()
    for a in articles:
        conn.execute(
            """INSERT OR IGNORE INTO articles
               (id, category, title, summary, image_url, source, url, published_at, fetch_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (a["id"], category, a["title"], a["summary"], a["image_url"],
             a["source"], a["url"], a["published_at"], today),
        )
    conn.commit()
    conn.close()


def get_article(article_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
    conn.close()
    return row


# ---------- BOOKMARKS (per user) ----------

def add_bookmark(user_id, article_id):
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO bookmarks (user_id, article_id, bookmarked_at) VALUES (?, ?, ?)",
        (user_id, article_id, datetime.now().strftime("%Y-%m-%d %H:%M")),
    )
    conn.commit()
    conn.close()


def remove_bookmark(user_id, article_id):
    conn = get_connection()
    conn.execute("DELETE FROM bookmarks WHERE user_id = ? AND article_id = ?", (user_id, article_id))
    conn.commit()
    conn.close()


def get_bookmarks(user_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT articles.*, bookmarks.bookmarked_at FROM bookmarks
        JOIN articles ON articles.id = bookmarks.article_id
        WHERE bookmarks.user_id = ?
        ORDER BY bookmarks.bookmarked_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return rows


def is_bookmarked(user_id, article_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM bookmarks WHERE user_id = ? AND article_id = ?", (user_id, article_id)
    ).fetchone()
    conn.close()
    return row is not None


# ---------- LIKES (per user, with global counts) ----------

def add_like(user_id, article_id):
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO likes (user_id, article_id, liked_at) VALUES (?, ?, ?)",
        (user_id, article_id, datetime.now().strftime("%Y-%m-%d %H:%M")),
    )
    conn.commit()
    conn.close()


def remove_like(user_id, article_id):
    conn = get_connection()
    conn.execute("DELETE FROM likes WHERE user_id = ? AND article_id = ?", (user_id, article_id))
    conn.commit()
    conn.close()


def get_like_counts(article_ids):
    """Returns {article_id: count} for a list of article ids."""
    if not article_ids:
        return {}
    conn = get_connection()
    placeholders = ",".join("?" * len(article_ids))
    rows = conn.execute(
        f"SELECT article_id, COUNT(*) as cnt FROM likes WHERE article_id IN ({placeholders}) GROUP BY article_id",
        article_ids,
    ).fetchall()
    conn.close()
    return {r["article_id"]: r["cnt"] for r in rows}


def get_liked_set(user_id, article_ids):
    """Returns a set of article_ids the user has liked, from the given list."""
    if not article_ids:
        return set()
    conn = get_connection()
    placeholders = ",".join("?" * len(article_ids))
    rows = conn.execute(
        f"SELECT article_id FROM likes WHERE user_id = ? AND article_id IN ({placeholders})",
        [user_id, *article_ids],
    ).fetchall()
    conn.close()
    return {r["article_id"] for r in rows}


# ---------- SEEN / SWIPE LOG (per user) ----------

def log_action(user_id, article_id, action):
    """action: 'skip' or 'bookmark'"""
    conn = get_connection()
    conn.execute(
        "INSERT INTO seen (user_id, article_id, action, seen_at) VALUES (?, ?, ?, ?)",
        (user_id, article_id, action, datetime.now().strftime("%Y-%m-%d %H:%M")),
    )
    conn.commit()
    conn.close()


def get_stats(user_id):
    conn = get_connection()
    total_seen = conn.execute("SELECT COUNT(*) FROM seen WHERE user_id = ?", (user_id,)).fetchone()[0]
    total_bookmarks = conn.execute("SELECT COUNT(*) FROM bookmarks WHERE user_id = ?", (user_id,)).fetchone()[0]
    total_skipped = conn.execute(
        "SELECT COUNT(*) FROM seen WHERE user_id = ? AND action = 'skip'", (user_id,)
    ).fetchone()[0]
    total_likes = conn.execute("SELECT COUNT(*) FROM likes WHERE user_id = ?", (user_id,)).fetchone()[0]
    conn.close()
    return {
        "total_seen": total_seen, "total_bookmarks": total_bookmarks,
        "total_skipped": total_skipped, "total_likes": total_likes,
    }


def get_community_stats():
    """Site-wide usage numbers, so you can see how many people are using your app."""
    conn = get_connection()
    today = date.today().isoformat()
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    active_today = conn.execute(
        "SELECT COUNT(DISTINCT user_id) FROM seen WHERE seen_at LIKE ?", (f"{today}%",)
    ).fetchone()[0]
    total_saves = conn.execute("SELECT COUNT(*) FROM bookmarks").fetchone()[0]
    total_likes = conn.execute("SELECT COUNT(*) FROM likes").fetchone()[0]
    total_swipes = conn.execute("SELECT COUNT(*) FROM seen").fetchone()[0]
    conn.close()
    return {
        "total_users": total_users, "active_today": active_today,
        "total_saves": total_saves, "total_likes": total_likes, "total_swipes": total_swipes,
    }