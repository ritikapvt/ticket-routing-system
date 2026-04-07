from flask import Flask, request, jsonify
from flask import send_from_directory
import os
from datetime import datetime
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
def get_db():
    return sqlite3.connect("database.db")


tickets = []

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            subject TEXT,
            description TEXT,
            category TEXT,
            priority TEXT,
            status TEXT,
            timestamp TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

billing_keywords = [
    "payment","pay","paid","unpaid","transaction","charge","charged",
    "refund","refunded","invoice","billing","bill","subscription","plan",
    "price","cost","fee","credit card","debit card","bank","paypal"
]

technical_keywords = [
    "error","bug","crash","login","password","slow","lag","not working",
    "broken","api","server","database","2FA","app","browser","timeout"
]

general_keywords = [
    "account","profile","how to","guide","setup","help","question",
    "feedback","request","status","update"
]

def classify_ticket(text):
    text = text.lower()
    scores = {"Billing": 0, "Technical": 0, "General": 0}
    matched_words = {"Billing": [], "Technical": [], "General": []}

    for word in billing_keywords:
        if word in text:
            scores["Billing"] += 1
            matched_words["Billing"].append(word)

    for word in technical_keywords:
        if word in text:
            scores["Technical"] += 1
            matched_words["Technical"].append(word)

    for word in general_keywords:
        if word in text:
            scores["General"] += 1
            matched_words["General"].append(word)

    if all(score == 0 for score in scores.values()):
        return "General", []

    category = max(scores, key=scores.get)

    return category, matched_words[category]

    
high_priority_keywords = [
    "urgent", "asap", "immediately", "right now", "critical",
    "not working", "system down", "server down", "crash",
    "blocked", "can't access", "unable to login", "payment failed"
]

medium_priority_keywords = [
    "issue", "problem", "error", "slow", "delay",
    "not responding", "bug", "glitch", "failed"
]

low_priority_keywords = [
    "question", "inquiry", "how to", "clarification",
    "suggestion", "feedback", "request"
]

def get_priority(text):
    text = text.lower()
    scores = {"High": 0, "Medium": 0, "Low": 0}
    reasons = []

    for word in high_priority_keywords:
        if word in text:
            scores["High"] += 2
            reasons.append(word)

    for word in medium_priority_keywords:
        if word in text:
            scores["Medium"] += 1
            reasons.append(word)

    for word in low_priority_keywords:
        if word in text:
            scores["Low"] += 1

    priority = max(scores, key=scores.get)

    return priority, reasons

@app.route('/submit_ticket', methods=['POST'])
def submit_ticket():
    try:
        data = request.get_json(force=True)
        print("Incoming data:", data)

        if not data:
            return jsonify({"error": "No data received"}), 400

        name = data.get("name", "")
        email = data.get("email", "")
        subject = data.get("subject", "")
        description = data.get("description", "")

        full_text = subject + " " + description
        category, cat_reason = classify_ticket(full_text)
        priority, pr_reason = get_priority(full_text)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO tickets (name, email, subject, description, category, priority, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, email, subject, description, category, priority, "Open", timestamp))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "category": category,
            "priority": priority,
            "category_reason": cat_reason,
            "priority_reason": pr_reason,
            "timestamp": timestamp
        })

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/tickets', methods=['GET'])
def get_tickets():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, name, email, subject, description, category, priority, status, timestamp
    FROM tickets
    """)
    rows = cursor.fetchall()

    conn.close()

    tickets = []
    for row in rows:
        tickets.append({
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "subject": row[3],
            "description": row[4],
            "category": row[5],
            "priority": row[6],
            "status": row[7],
            "timestamp": row[8]
        })

    return jsonify(tickets)

@app.route('/close_ticket', methods=['POST'])
def close_ticket():
    data = request.get_json()

    ticket_id = data.get("id")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tickets
        SET status = 'Closed'
        WHERE id = ?
    """, (ticket_id,))

    conn.commit()
    conn.close()

    return jsonify({"success": True})
    
@app.route('/')
def serve_submit():
    return send_from_directory('frontend', 'submit.html')

@app.route('/dashboard')
def serve_dashboard():
    return send_from_directory('frontend', 'dashboard.html')

if __name__ == '__main__':
    app.run()