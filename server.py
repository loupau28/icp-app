from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from functools import wraps
import psycopg2
import os
import traceback

app = Flask(__name__)
app.secret_key = "un_secret_solide"  # ⚠️ à changer par une vraie clé secrète

# -------------------- UTILISATEURS --------------------
USERS = {
    "BFOR-TAV": "BFOR-TAV95",   # Consultation
    "SOG-TAV": "SOG-TAV95",     # GSSI
    "EAP-TAV": "EAP-TAV95"      # ICP
}

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("⚠️ Erreur : la variable d'environnement DATABASE_URL n'est pas définie")
    # Exemple : export DATABASE_URL=postgres://user:password@host:port/dbname

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
            nom TEXT,
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
            nom TEXT,
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
        if "username" not in session:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_users):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get("username") not in allowed_users:
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
            session["username"] = username
            next_page = request.args.get("next") or url_for("index")
            return redirect(next_page)

    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# -------------------- ROUTES --------------------
@app.route("/")
def index():
    session.clear()
    return render_template("index.html")

@app.route("/consultation")
@login_required
@role_required(["BFOR-TAV"])
def consultation_page():
    return render_template("Consultation.html")

@app.route("/consultation/icp")
@login_required
@role_required(["BFOR-TAV"])
def consultation_icp_page():
    return render_template("Consultage.html")

@app.route("/consultation/gssi")
@login_required
@role_required(["BFOR-TAV"])
def consultation_gssi_page():
    return render_template("ConsultageGSSI.html")
    
@app.route("/renseignement")
@login_required
@role_required(["SOG-TAV"])
def consultation_page():
    return render_template("renseignement.html")

@app.route("/renseignementicp")
@login_required
@role_required(["EAP-TAV"])
def consultation_icp():
    return render_template("Renseignement ICP.html")

@app.route("/Renseignement/gssi")
@login_required
@role_required(["SOG-TAV"])
def consultation_gssi():
    return render_template("Renseignement GSSI.html")
    
@app.route("/Renseignement/pepari")
@login_required
@role_required(["SOG-TAV"])
def consultation_gssi():
    return render_template("Renseignement PEPARI.html")

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
                nom,
                agent.get("pompes", 0),
                agent.get("tractions", 0),
                agent.get("killy", 0),
                agent.get("gainage", 0),
                agent.get("luc_leger", 0),
                agent.get("souplesse", 0)
            )

            if result:
                c.execute("""
                    UPDATE icp
                    SET date=%s, eap=%s, nom=%s, pompes=%s, tractions=%s, killy=%s,
                        gainage=%s, luc_leger=%s, souplesse=%s
                    WHERE id=%s
                """, values + (result[0],))
            else:
                c.execute("""
                    INSERT INTO icp (date, eap, nom, pompes, tractions, killy,
                                     gainage, luc_leger, souplesse)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, values)

        conn.commit()
        c.close()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/get-icp")
@login_required
@role_required(["BFOR-TAV"])
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

        date_str = data.get("date")          # ex: "2025-08-27"
        annee = date_str[:4]                 # -> "2025"
        sog = data.get("eap")                # le SOG envoyé depuis le front

        for agent in data["agents"]:
            nom = (agent.get("nom") or "").strip().upper()

            # Vérifier si enregistrement existe pour ce nom + SOG + année
            c.execute("""
                SELECT id, psc, crochet, excavation
                FROM gssi
                WHERE nom=%s AND eap=%s AND date::text LIKE %s
            """, (nom, sog, f"{annee}-%"))
            result = c.fetchone()

            if result:
                old_psc, old_crochet, old_excavation = result[1], result[2], result[3]

                # Fusionner : garder anciens TRUE si front n’envoie rien
                psc = old_psc or bool(agent.get("psc"))
                crochet = old_crochet or bool(agent.get("crochet"))
                excavation = old_excavation or bool(agent.get("excavation"))

                c.execute("""
                    UPDATE gssi
                    SET date=%s, eap=%s, nom=%s, psc=%s, crochet=%s, excavation=%s, grh=FALSE
                    WHERE id=%s
                """, (date_str, sog, nom, psc, crochet, excavation, result[0]))

            else:
                psc = bool(agent.get("psc"))
                crochet = bool(agent.get("crochet"))
                excavation = bool(agent.get("excavation"))

                c.execute("""
                    INSERT INTO gssi (date, eap, nom, psc, crochet, excavation, grh)
                    VALUES (%s, %s, %s, %s, %s, %s, FALSE)
                """, (date_str, sog, nom, psc, crochet, excavation))

        conn.commit()
        c.close()
        conn.close()
        return jsonify({"status": "ok"})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/get-gssi")
@login_required
@role_required(["BFOR-TAV"])
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
