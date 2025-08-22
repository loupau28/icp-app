from flask import Flask, request, render_template, redirect, url_for, jsonify
from flask_cors import CORS
from functools import wraps
import psycopg2
import os
import traceback

app = Flask(__name__)
app.secret_key = "un_secret_solide"
CORS(app)

# -------------------- UTILISATEURS --------------------
USERS = {
    "BFOR-TAV": "BFOR-TAV95",   # Consultation
    "SOG-TAV": "SOG-TAV95",     # GSSI
    "EAP-TAV": "EAP-TAV95"      # ICP
}

DATABASE_URL = os.environ.get("DATABASE_URL")

# -------------------- BDD --------------------
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS icp (
            id SERIAL PRIMARY KEY,
            date DATE,
            eap TEXT,
            nom TEXT UNIQUE,
            pompes INTEGER DEFAULT 0,
            tractions INTEGER DEFAULT 0,
            killy INTEGER DEFAULT 0,
            gainage INTEGER DEFAULT 0,
            luc_leger INTEGER DEFAULT 0,
            souplesse INTEGER DEFAULT 0,
            grh BOOLEAN DEFAULT FALSE
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS gssi (
            id SERIAL PRIMARY KEY,
            date DATE,
            eap TEXT,
            nom TEXT UNIQUE,
            psc BOOLEAN DEFAULT FALSE,
            crochet BOOLEAN DEFAULT FALSE,
            excavation BOOLEAN DEFAULT FALSE,
            grh BOOLEAN DEFAULT FALSE
        )
    """)
    conn.commit()
    c.close()
    conn.close()

# -------------------- DECORATEURS --------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Toujours forcer le passage par la page de login
        return redirect(url_for("login", next=request.url))
    return decorated_function

def role_required(allowed_users):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            username = request.args.get("user")
            if not username or username not in allowed_users:
                return "Accès interdit", 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# -------------------- LOGIN --------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username not in USERS:
            error = "Identifiant invalide"
        elif USERS[username] != password:
            error = "Mot de passe incorrect"
        else:
            next_page = request.args.get("next") or url_for("index")
            sep = "&" if "?" in next_page else "?"
            return redirect(f"{next_page}{sep}user={username}")

    return render_template("login.html", error=error)

# -------------------- ROUTES PUBLIQUES --------------------
@app.route("/")
def index():
    return render_template("index.html")

# -------------------- ROUTES PROTÉGÉES --------------------
@app.route("/consultation")
@login_required
@role_required(["BFOR-TAV"])
def consultation_page():
    role = request.args.get("role")
    if role == "gssi":
        return render_template("consultageGSSI.html")
    else:
        return render_template("consultage.html")

@app.route("/renseignement")
@login_required
@role_required(["EAP-TAV"])
def consultation_icp():
    return render_template("Renseignement ICP.html")

@app.route("/gssi")
@login_required
@role_required(["SOG-TAV"])
def consultation_gssi():
    return render_template("Renseignement GSSI.html")

# -------------------- ICP --------------------
@app.route("/save-icp", methods=["POST"])
@login_required
@role_required(["EAP-TAV"])
def save_icp():
    try:
        data = request.get_json()
        if not data or "agents" not in data:
            return jsonify({"status": "error", "message": "Pas de données reçues"}), 400

        conn = get_db_connection()
        c = conn.cursor()

        for agent in data["agents"]:
            nom = (agent.get("nom") or "").strip().upper()
            c.execute("SELECT id FROM icp WHERE nom = %s", (nom,))
            result = c.fetchone()

            values = (
                data.get("date"),
                data.get("eap"),
                agent.get("pompes", 0),
                agent.get("tractions", 0),
                agent.get("killy", 0),
                agent.get("gainage", 0),
                agent.get("luc_leger", 0),
                agent.get("souplesse", 0),
                nom
            )

            if result:
                c.execute("""
                    UPDATE icp
                    SET date=%s, eap=%s, pompes=%s, tractions=%s, killy=%s, gainage=%s, luc_leger=%s, souplesse=%s
                    WHERE nom=%s
                """, values)
            else:
                c.execute("""
                    INSERT INTO icp (date, eap, nom, pompes, tractions, killy, gainage, luc_leger, souplesse)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, values[:-1] + (nom,))

        conn.commit()
        c.close()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/get-icp")
@login_required
@role_required(["EAP-TAV"])
def get_icp():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM icp")
        rows = c.fetchall()
        c.close()
        conn.close()
        results = [
            {
                "id": r[0], "date": r[1], "eap": r[2], "nom": r[3],
                "pompes": r[4], "tractions": r[5], "killy": r[6],
                "gainage": r[7], "luc_leger": r[8], "souplesse": r[9],
                "grh": r[10]
            }
            for r in rows
        ]
        return jsonify(results)
    except Exception as e:
        traceback.print_exc()
        return jsonify([])

# -------------------- GSSI --------------------
@app.route("/save-gssi", methods=["POST"])
@login_required
@role_required(["SOG-TAV"])
def save_gssi():
    try:
        data = request.get_json()
        if not data or "agents" not in data:
            return jsonify({"status": "error", "message": "Pas de données reçues"}), 400

        conn = get_db_connection()
        c = conn.cursor()

        for agent in data["agents"]:
            nom = (agent.get("nom") or "").strip().upper()
            c.execute("SELECT id FROM gssi WHERE nom = %s", (nom,))
            result = c.fetchone()

            values = (
                data.get("date"),
                data.get("eap"),
                bool(agent.get("psc")),
                bool(agent.get("crochet")),
                bool(agent.get("excavation")),
                nom
            )

            if result:
                c.execute("""
                    UPDATE gssi
                    SET date=%s, eap=%s, psc=%s, crochet=%s, excavation=%s, grh=FALSE
                    WHERE nom=%s
                """, values)
            else:
                c.execute("""
                    INSERT INTO gssi (date, eap, nom, psc, crochet, excavation, grh)
                    VALUES (%s, %s, %s, %s, %s, %s, FALSE)
                """, values[:-1] + (nom,))

        conn.commit()
        c.close()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/get-gssi")
@login_required
@role_required(["SOG-TAV"])
def get_gssi():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM gssi")
        rows = c.fetchall()
        c.close()
        conn.close()
        results = [
            {
                "id": r[0], "date": r[1], "eap": r[2], "nom": r[3],
                "psc": r[4], "crochet": r[5], "excavation": r[6], "grh": r[7]
            }
            for r in rows
        ]
        return jsonify(results)
    except Exception as e:
        traceback.print_exc()
        return jsonify([])

# -------------------- UPDATE GRH --------------------
@app.route("/update-grh/<table>", methods=["POST"])
@login_required
@role_required(["BFOR-TAV"])
def update_grh(table):
    if table not in ["icp", "gssi"]:
        return jsonify({"error": "Table invalide"}), 400
    try:
        data = request.get_json()
        ids = data.get("ids", [])
        if not ids:
            return jsonify({"error": "Aucun ID fourni"}), 400

        conn = get_db_connection()
        c = conn.cursor()
        for id_val in ids:
            c.execute(f"UPDATE {table} SET grh = TRUE WHERE id = %s", (id_val,))
        conn.commit()
        c.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# -------------------- LANCEMENT --------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
