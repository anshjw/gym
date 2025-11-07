import os
import sqlite3
from datetime import datetime, date, timedelta
from flask import Flask, request, jsonify, render_template

BASE_DIR = os.path.dirname(__file__)
# Use your existing DB if you set GYM_DB_PATH, else gym.db in this folder
DB_PATH = os.environ.get("GYM_DB_PATH") or os.path.join(BASE_DIR, "gym.db")
print(">> Using database at:", DB_PATH)

app = Flask(__name__, template_folder="templates", static_folder="static")

# --------- DB helpers ---------
def connect_db():
    # short-lived connection per operation (simple + safe)
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn

def init_db():
    conn = connect_db()
    cur = conn.cursor()

    # tables
    cur.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            code TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            duration_months INTEGER NOT NULL,
            price INTEGER NOT NULL
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            join_date DATE NOT NULL,
            plan_code TEXT NOT NULL,
            end_date DATE NOT NULL,
            FOREIGN KEY(plan_code) REFERENCES plans(code)
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trainers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialization TEXT,
            salary INTEGER NOT NULL DEFAULT 0
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS billing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            date_paid DATE NOT NULL,
            FOREIGN KEY(member_id) REFERENCES members(id)
        );
    """)

    # seed plans (no effect if already there)
    seed_plans = [
        ("1M", "1 Month", 1, 1000),
        ("3M", "3 Months", 3, 2500),
        ("6M", "6 Months", 6, 4500),
        ("12M", "12 Months", 12, 8000),
        ("3M_WT_CF_CARDIO", "Weight Training + CrossFit + Cardio (3M)", 3, 4000),
        ("1M_WT", "Weight Training (1M)", 1, 1000),
        ("12M_WT", "Weight Training (12M)", 12, 8000),
    ]
    cur.executemany("""
        INSERT OR IGNORE INTO plans (code, label, duration_months, price)
        VALUES (?, ?, ?, ?);
    """, seed_plans)

    conn.commit()
    conn.close()

def add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    if m == 12:
        next_month = date(y + 1, 1, 1)
    else:
        next_month = date(y, m + 1, 1)
    last_day = (next_month - timedelta(days=1)).day
    day = min(d.day, last_day)
    return date(y, m, day)

def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()

def row_to_dict(row):
    return {k: row[k] for k in row.keys()}

# --------- Pages ---------
@app.route("/")
def home():
    return render_template("index.html")

# --------- Plans ---------
@app.route("/api/plans", methods=["GET"])
def list_plans():
    with connect_db() as conn:
        rows = conn.execute("SELECT * FROM plans ORDER BY duration_months, label;").fetchall()
    return jsonify([row_to_dict(r) for r in rows])

@app.route("/api/plans", methods=["POST"])
def add_plan():
    data = request.get_json(force=True)
    code = data.get("code")
    label = data.get("label")
    duration_months = int(data.get("duration_months"))
    price = int(data.get("price"))
    try:
        with connect_db() as conn:
            conn.execute(
                "INSERT INTO plans (code, label, duration_months, price) VALUES (?, ?, ?, ?);",
                (code, label, duration_months, price),
            )
            conn.commit()
        return jsonify({"ok": True}), 201
    except sqlite3.IntegrityError as e:
        return jsonify({"ok": False, "error": str(e)}), 400

# --------- Members ---------
@app.route("/api/members", methods=["GET"])
def list_members():
    with connect_db() as conn:
        rows = conn.execute("""
            SELECT m.id, m.name, m.join_date, m.end_date,
                   p.code AS plan_code, p.label AS plan_label, p.price, p.duration_months
            FROM members m
            JOIN plans p ON p.code = m.plan_code
            ORDER BY m.id DESC;
        """).fetchall()
    return jsonify([row_to_dict(r) for r in rows])

@app.route("/api/members", methods=["POST"])
def add_member():
    data = request.get_json(force=True)
    name = data.get("name")
    join_date_str = data.get("join_date")
    plan_code = data.get("plan_code")
    if not all([name, join_date_str, plan_code]):
        return jsonify({"ok": False, "error": "name, join_date, plan_code are required"}), 400

    jd = parse_date(join_date_str)
    with connect_db() as conn:
        cur = conn.cursor()
        plan = cur.execute("SELECT duration_months FROM plans WHERE code = ?;", (plan_code,)).fetchone()
        if not plan:
            return jsonify({"ok": False, "error": "Invalid plan_code"}), 400
        end_dt = add_months(jd, int(plan["duration_months"]))
        cur.execute("""
            INSERT INTO members (name, join_date, plan_code, end_date)
            VALUES (?, ?, ?, ?);
        """, (name, jd.isoformat(), plan_code, end_dt.isoformat()))
        conn.commit()
        new_id = cur.lastrowid
    return jsonify({"ok": True, "member_id": new_id, "end_date": end_dt.isoformat()}), 201

@app.route("/api/members/<int:member_id>", methods=["DELETE"])
def remove_member(member_id):
    with connect_db() as conn:
        conn.execute("DELETE FROM members WHERE id = ?;", (member_id,))
        conn.commit()
    return jsonify({"ok": True})

@app.route("/api/members/<int:member_id>", methods=["PATCH"])
def update_member(member_id):
    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name")
    join_date_str = data.get("join_date")
    plan_code = data.get("plan_code")

    with connect_db() as conn:
        cur = conn.cursor()
        row = cur.execute("""
            SELECT m.id, m.name, m.join_date, m.plan_code, m.end_date, p.duration_months
            FROM members m
            JOIN plans p ON p.code = m.plan_code
            WHERE m.id = ?;
        """, (member_id,)).fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Invalid member_id"}), 404

        current_join = parse_date(row["join_date"])
        current_plan = row["plan_code"]
        current_duration = int(row["duration_months"])

        new_plan_code = plan_code if plan_code else current_plan
        if plan_code:
            plan_row = cur.execute("SELECT duration_months FROM plans WHERE code = ?;", (plan_code,)).fetchone()
            if not plan_row:
                return jsonify({"ok": False, "error": "Invalid plan_code"}), 400
            new_duration = int(plan_row["duration_months"])
        else:
            new_duration = current_duration

        new_join = parse_date(join_date_str) if join_date_str else current_join
        recalc = (join_date_str is not None) or (plan_code is not None)
        if recalc:
            new_end = add_months(new_join, new_duration)
        else:
            new_end = parse_date(row["end_date"])

        fields, params = [], []
        if name is not None:
            fields.append("name = ?"); params.append(name)
        if join_date_str is not None:
            fields.append("join_date = ?"); params.append(new_join.isoformat())
        if plan_code is not None:
            fields.append("plan_code = ?"); params.append(new_plan_code)
        if recalc:
            fields.append("end_date = ?"); params.append(new_end.isoformat())

        if fields:
            params.append(member_id)
            cur.execute(f"UPDATE members SET {', '.join(fields)} WHERE id = ?;", params)
            conn.commit()

    return jsonify({
        "ok": True,
        "member_id": member_id,
        "updated": {
            "name": name if name is not None else row["name"],
            "join_date": new_join.isoformat() if join_date_str is not None else row["join_date"],
            "plan_code": new_plan_code,
            "end_date": new_end.isoformat() if recalc else row["end_date"]
        }
    })

@app.route("/api/members/<int:member_id>/renew", methods=["POST"])
def renew_member(member_id):
    data = request.get_json(force=True, silent=True) or {}
    create_bill = bool(data.get("create_bill", True))
    amount = data.get("amount")
    date_paid = data.get("date_paid") or date.today().isoformat()

    with connect_db() as conn:
        cur = conn.cursor()
        row = cur.execute("""
            SELECT m.id, m.end_date, p.duration_months, p.price
            FROM members m
            JOIN plans p ON p.code = m.plan_code
            WHERE m.id = ?;
        """, (member_id,)).fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Invalid member_id"}), 404

        current_end = parse_date(row["end_date"])
        new_end = add_months(current_end, int(row["duration_months"]))
        cur.execute("UPDATE members SET end_date = ? WHERE id = ?;", (new_end.isoformat(), member_id))

        if create_bill:
            amt = int(amount) if amount is not None else int(row["price"])
            cur.execute("""
                INSERT INTO billing (member_id, amount, date_paid)
                VALUES (?, ?, ?);
            """, (member_id, amt, date_paid))

        conn.commit()

    return jsonify({"ok": True, "new_end_date": new_end.isoformat()})

# --------- Trainers ---------
@app.route("/api/trainers", methods=["GET"])
def list_trainers():
    with connect_db() as conn:
        rows = conn.execute("SELECT * FROM trainers ORDER BY id DESC;").fetchall()
    return jsonify([row_to_dict(r) for r in rows])

@app.route("/api/trainers", methods=["POST"])
def add_trainer():
    data = request.get_json(force=True)
    name = data.get("name")
    specialization = data.get("specialization", "")
    salary = int(data.get("salary", 0))
    if not name:
        return jsonify({"ok": False, "error": "name is required"}), 400

    with connect_db() as conn:
        conn.execute("""
            INSERT INTO trainers (name, specialization, salary)
            VALUES (?, ?, ?);
        """, (name, specialization, salary))
        conn.commit()
    return jsonify({"ok": True}), 201

@app.route("/api/trainers/<int:trainer_id>", methods=["DELETE"])
def remove_trainer(trainer_id):
    with connect_db() as conn:
        conn.execute("DELETE FROM trainers WHERE id = ?;", (trainer_id,))
        conn.commit()
    return jsonify({"ok": True})

# --------- Billing ---------
@app.route("/api/billing", methods=["GET"])
def list_billing():
    with connect_db() as conn:
        rows = conn.execute("""
            SELECT b.id, b.member_id, m.name AS member_name, b.amount, b.date_paid
            FROM billing b
            JOIN members m ON m.id = b.member_id
            ORDER BY b.id DESC;
        """).fetchall()
    return jsonify([row_to_dict(r) for r in rows])

@app.route("/api/billing", methods=["POST"])
def add_bill():
    data = request.get_json(force=True)
    member_id = data.get("member_id")
    amount = data.get("amount")
    date_paid = data.get("date_paid")
    if not all([member_id, amount, date_paid]):
        return jsonify({"ok": False, "error": "member_id, amount, date_paid are required"}), 400

    with connect_db() as conn:
        m = conn.execute("SELECT id FROM members WHERE id = ?;", (member_id,)).fetchone()
        if not m:
            return jsonify({"ok": False, "error": "Invalid member_id"}), 400
        conn.execute("""
            INSERT INTO billing (member_id, amount, date_paid)
            VALUES (?, ?, ?);
        """, (int(member_id), int(amount), date_paid))
        conn.commit()
    return jsonify({"ok": True}), 201

# --------- Smart Plan Over ---------
@app.route("/api/smart-expiring", methods=["GET"])
def smart_expiring():
    days = int(request.args.get("days", 5))
    today = date.today()
    cutoff = today + timedelta(days=days)
    with connect_db() as conn:
        rows = conn.execute("""
            SELECT m.id, m.name, m.join_date, m.end_date, p.label AS plan_label, p.price
            FROM members m
            JOIN plans p ON p.code = m.plan_code
            WHERE date(m.end_date) BETWEEN date(?) AND date(?)
            ORDER BY date(m.end_date);
        """, (today.isoformat(), cutoff.isoformat())).fetchall()
    return jsonify([row_to_dict(r) for r in rows])

# ---- init (Flask 3.x safe) ----
with app.app_context():
    init_db()

if __name__ == "__main__":
    # Turn off reloader to avoid duplicate inits/locks
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
