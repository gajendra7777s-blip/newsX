"""
NewsX - AI-Summarized Reels-Style News App
--------------------------------------------
Final year project. Run with:  python app.py
Then open http://localhost:5000 in your browser (laptop or phone on same WiFi).
"""

import os
import hashlib
import secrets
import requests
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

import database as db

load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
NEWS_URL = "https://newsapi.org/v2/top-headlines"

CATEGORIES = ["general", "technology", "business", "sports", "entertainment", "health", "science"]

app = Flask(__name__, static_folder="static", static_url_path="")
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)
db.init_db()

AVATARS = ["🙂", "😎", "🦊", "🐱", "🐼", "🦁", "🐨", "🐸", "🤖", "🌟"]


# ---------------- FALLBACK DATA (so the demo never shows a blank screen) ----------------
FALLBACK_ARTICLES = [
    {
        "title": "Sample Headline: Add your NEWS_API_KEY to see live news",
        "description": "This is placeholder content. Once you add a free NewsAPI key to your .env file, real daily headlines will appear here automatically, summarized by AI.",
        "urlToImage": "https://images.unsplash.com/photo-1495020689067-958852a7765e?w=800",
        "source": {"name": "NewsX"},
        "url": "https://newsapi.org/register",
        "publishedAt": datetime.now().isoformat(),
    }
]


def make_id(url):
    return hashlib.md5(url.encode()).hexdigest()[:16]


def summarize_with_groq(title, description):
    """Turn an article into a short, punchy 'reel' style 3-4 line caption."""
    if not GROQ_API_KEY:
        return description or title

    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": (
                        "You rewrite news articles into short, punchy, easy-to-read 'reel' style captions "
                        "for a mobile news app. 3-4 short sentences max. No hashtags, no emojis, factual and clear."
                    )},
                    {"role": "user", "content": f"Title: {title}\nDetails: {description or 'N/A'}"},
                ],
                "temperature": 0.5,
                "max_tokens": 150,
            },
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return description or title


def fetch_and_cache(category):
    """Fetch fresh articles from NewsAPI + summarize with AI, cache in DB. Falls back gracefully."""
    if not NEWS_API_KEY:
        db.save_articles(category, [{
            "id": make_id(a["url"]), "title": a["title"],
            "summary": a["description"], "image_url": a["urlToImage"],
            "source": a["source"]["name"], "url": a["url"], "published_at": a["publishedAt"],
        } for a in FALLBACK_ARTICLES])
        return

    try:
        resp = requests.get(NEWS_URL, params={
            "category": category, "language": "en", "pageSize": 15, "apiKey": NEWS_API_KEY,
        }, timeout=15)
        resp.raise_for_status()
        raw_articles = resp.json().get("articles", [])
    except Exception:
        raw_articles = FALLBACK_ARTICLES

    cleaned = []
    for a in raw_articles:
        if not a.get("title") or a.get("title") == "[Removed]":
            continue
        summary = summarize_with_groq(a["title"], a.get("description", ""))
        cleaned.append({
            "id": make_id(a["url"]),
            "title": a["title"],
            "summary": summary,
            "image_url": a.get("urlToImage") or "",
            "source": (a.get("source") or {}).get("name", "Unknown"),
            "url": a["url"],
            "published_at": a.get("publishedAt", ""),
        })

    if cleaned:
        db.save_articles(category, cleaned)


# ---------------- AUTH HELPERS ----------------

def current_user_id():
    return session.get("user_id")


def login_required(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user_id():
            return jsonify({"error": "not_logged_in"}), 401
        return fn(*args, **kwargs)
    return wrapper


# ---------------- ROUTES ----------------

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.json or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters"}), 400
    if len(password) < 4:
        return jsonify({"error": "Password must be at least 4 characters"}), 400
    if db.get_user_by_username(username):
        return jsonify({"error": "That username is already taken"}), 400

    avatar = AVATARS[len(username) % len(AVATARS)]
    user_id = db.create_user(username, generate_password_hash(password), avatar)
    session["user_id"] = user_id
    return jsonify({"id": user_id, "username": username, "avatar_emoji": avatar})


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = db.get_user_by_username(username)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Incorrect username or password"}), 401

    session["user_id"] = user["id"]
    return jsonify({"id": user["id"], "username": user["username"], "avatar_emoji": user["avatar_emoji"]})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"status": "ok"})


@app.route("/api/me")
def api_me():
    uid = current_user_id()
    if not uid:
        return jsonify({"error": "not_logged_in"}), 401
    user = db.get_user_by_id(uid)
    if not user:
        session.clear()
        return jsonify({"error": "not_logged_in"}), 401
    return jsonify({"id": user["id"], "username": user["username"], "avatar_emoji": user["avatar_emoji"]})


@app.route("/api/categories")
def api_categories():
    return jsonify(CATEGORIES)


@app.route("/api/feed")
@login_required
def api_feed():
    category = request.args.get("category", "general")
    if category not in CATEGORIES:
        category = "general"

    rows = db.get_cached_articles(category)
    if not rows:
        fetch_and_cache(category)
        rows = db.get_cached_articles(category)

    uid = current_user_id()
    articles = [dict(r) for r in rows]
    ids = [a["id"] for a in articles]
    liked_set = db.get_liked_set(uid, ids)
    like_counts = db.get_like_counts(ids)
    for a in articles:
        a["bookmarked"] = db.is_bookmarked(uid, a["id"])
        a["liked"] = a["id"] in liked_set
        a["like_count"] = like_counts.get(a["id"], 0)
    return jsonify(articles)


@app.route("/api/bookmark", methods=["POST"])
@login_required
def api_bookmark():
    article_id = request.json.get("article_id")
    uid = current_user_id()
    db.add_bookmark(uid, article_id)
    db.log_action(uid, article_id, "bookmark")
    return jsonify({"status": "ok"})


@app.route("/api/bookmark", methods=["DELETE"])
@login_required
def api_unbookmark():
    article_id = request.json.get("article_id")
    db.remove_bookmark(current_user_id(), article_id)
    return jsonify({"status": "ok"})


@app.route("/api/like", methods=["POST"])
@login_required
def api_like():
    article_id = request.json.get("article_id")
    uid = current_user_id()
    db.add_like(uid, article_id)
    db.log_action(uid, article_id, "like")
    return jsonify({"status": "ok"})


@app.route("/api/like", methods=["DELETE"])
@login_required
def api_unlike():
    article_id = request.json.get("article_id")
    db.remove_like(current_user_id(), article_id)
    return jsonify({"status": "ok"})


@app.route("/api/skip", methods=["POST"])
@login_required
def api_skip():
    article_id = request.json.get("article_id")
    db.log_action(current_user_id(), article_id, "skip")
    return jsonify({"status": "ok"})


@app.route("/api/bookmarks")
@login_required
def api_bookmarks():
    rows = db.get_bookmarks(current_user_id())
    return jsonify([dict(r) for r in rows])


@app.route("/api/stats")
@login_required
def api_stats():
    return jsonify(db.get_stats(current_user_id()))


@app.route("/api/community-stats")
@login_required
def api_community_stats():
    """How many people are using the app in total - for your own curiosity/demo."""
    return jsonify(db.get_community_stats())


def get_lan_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


if __name__ == "__main__":
    lan_ip = get_lan_ip()
    print("\n  NewsX is running:")
    print(f"  \u279c Local (this laptop):  http://127.0.0.1:5000")
    print(f"  \u279c Network (your phone): http://{lan_ip}:5000")
    print("  (phone must be on the SAME WiFi network as this laptop)\n")
    app.run(debug=True, host="0.0.0.0", port=5000)