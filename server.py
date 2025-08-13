from flask import Flask, request, render_template, redirect, url_for, jsonify, session
from flask_cors import CORS
import psycopg2
import os

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")  # Pour sessions

# -------------------- IDENTIFIANTS --------------------
USERS = {
    "renseignement": {"username": "EAP-TAV", "password": "EAP-TAV95"},
    "consultage": {"username": "BFOR-TAV", "password": "BFOR-TAV95"},
    "gssi": {"username": "SOG-TAV", "password": "SOG-TAV95"}
}

DATABASE_URL = os.environ.get("DATABASE_URL")  # Exemple : postgres://user:pass@host/db

# -------------------- BDD --------------------
def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS icp (
            id SERIAL PRIMARY KEY,
            date DATE,
            eap TEXT,
            nom TEXT,
            pompes INTEGER,
            tractions INTEGER,
            killy INTEGER,
            gainage INTEGER,
            luc_leger INTEGER,
            souplesse INTEGER,
            grh BOOLEAN DEFAULT FALSE
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS gssi (
            id SERIAL PRIMARY KEY,
            date DATE,
            eap TEXT,
            nom TEXT,
            psc BOOLEAN,
            crochet BOOLEAN,
            excavation BOOLEAN,
            grh BOOLEAN DEFAULT FALSE
        )
    """)
    conn.commit()
    c.close()
    conn.close()

# -------------------- LOGIN --------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        for role, creds in USERS.items():
            if username == creds["username"] and password == creds["password"]:
                session["logged_in"] = True
                session["role"] = role
                session["username"] = username
                return redirect(url_for(f"{role}_page"))
        error = "Identifiants incorrects"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# -------------------- PROTECTION --------------------
def require_auth(role):
    if not session.get("logged_in") or session.get("role") != role:
        return redirect(url_for("login"))
    return True

# -------------------- ROUTES --------------------
@app.route("/renseignement")
def renseignement_page():
    auth = require_auth("renseignement")
    if auth is True:
        return render_template("Renseignement ICP.html")
    return auth

@app.route("/consultage")
def consultage_page():
    auth = require_auth("consultage")
    if auth is True:
        return render_template("Consultage.html")
    return auth

@app.route("/gssi")
def gssi_page():
    auth = require_auth("gssi")
    if auth is True:
        return render_template("Renseignement GSSI.html")
    return auth

# -------------------- ICP --------------------
@app.route("/save-icp", methods=["POST"])
def save_icp():
    try:
        data = request.get_json()
        if not data or "agents" not in data:
            return jsonify({"status": "error", "message": "Pas de données reçues"}), 400
        conn = get_db_connection()
        c = conn.cursor()
        for agent in data["agents"]:
            nom = agent.get("nom")
            c.execute("SELECT id FROM icp WHERE nom = %s", (nom,))
            result = c.fetchone()
            if result:
                c.execute("""
                    UPDATE icp SET
                        date=%s, eap=%s, pompes=%s, tractions=%s, killy=%s,
                        gainage=%s, luc_leger=%s, souplesse=%s, grh=FALSE
                    WHERE nom=%s
                """, (
                    data.get("date"), data.get("eap"), agent.get("pompes"),
                    agent.get("tractions"), agent.get("killy"), agent.get("gainage"),
                    agent.get("luc_leger"), agent.get("souplesse"), nom
                ))
            else:
                c.execute("""
                    INSERT INTO icp (date, eap, nom, pompes, tractions, killy, gainage, luc_leger, souplesse, grh)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,FALSE)
                """, (
                    data.get("date"), data.get("eap"), nom, agent.get("pompes"),
                    agent.get("tractions"), agent.get("killy"), agent.get("gainage"),
                    agent.get("luc_leger"), agent.get("souplesse")
                ))
        conn.commit()
        c.close()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/get-icp")
def get_icp():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM icp")
        rows = c.fetchall()
        c.close()
        conn.close()
        results = []
        for r in rows:
            results.append({
                "id": r[0], "date": r[1], "eap": r[2], "nom": r[3],
                "pompes": r[4], "tractions": r[5], "killy": r[6],
                "gainage": r[7], "luc_leger": r[8], "souplesse": r[9],
                "grh": r[10]
            })
        return jsonify(results)
    except Exception as e:
        print(e)
        return jsonify([])

# -------------------- GSSI --------------------
@app.route("/save-gssi", methods=["POST"])
def save_gssi():
    try:
        data = request.get_json()
        if not data or "agents" not in data:
            return jsonify({"status": "error", "message": "Pas de données reçues"}), 400
        conn = get_db_connection()
        c = conn.cursor()
        for agent in data["agents"]:
            nom = agent.get("nom")
            psc = bool(agent.get("psc"))
            crochet = bool(agent.get("crochet"))
            excavation = bool(agent.get("excavation"))
            c.execute("SELECT id FROM gssi WHERE nom = %s", (nom,))
            result = c.fetchone()
            if result:
                c.execute("""
                    UPDATE gssi SET date=%s, eap=%s, psc=%s, crochet=%s, excavation=%s, grh=FALSE
                    WHERE nom=%s
                """, (data.get("date"), data.get("eap"), psc, crochet, excavation, nom))
            else:
                c.execute("""
                    INSERT INTO gssi (date,eap,nom,psc,crochet,excavation,grh)
                    VALUES (%s,%s,%s,%s,%s,%s,FALSE)
                """, (data.get("date"), data.get("eap"), nom, psc, crochet, excavation))
        conn.commit()
        c.close()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/get-gssi")
def get_gssi():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM gssi")
        rows = c.fetchall()
        c.close()
        conn.close()
        results = []
        for r in rows:
            results.append({
                "id": r[0], "date": r[1], "eap": r[2], "nom": r[3],
                "psc": r[4], "crochet": r[5], "excavation": r[6], "grh": r[7]
            })
        return jsonify(results)
    except Exception as e:
        print(e)
        return jsonify([])

# -------------------- LANCEMENT --------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
