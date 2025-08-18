from flask import Flask, request, render_template, redirect, url_for, jsonify
from flask_cors import CORS
import psycopg2
import os

app = Flask(__name__)
CORS(app)

# -------------------- IDENTIFIANTS --------------------
USERS = {
    "renseignement": {"username": "EAP-TAV", "password": "EAP-TAV95"},
    "consultage": {"username": "BFOR-TAV", "password": "BFOR-TAV95"},
    "gssi": {"username": "SOG-TAV", "password": "SOG-TAV95"},
    "congssi": {"username": "SOG-TAV", "password": "SOG-TAV95"}
}

DATABASE_URL = os.environ.get("DATABASE_URL")  # Exemple : postgres://user:pass@host/db

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
    username = request.form.get("username")  # identifiant choisi
    password = request.form.get("password")

    if request.method == "POST":
        # Vérifie quel rôle correspond à l'identifiant choisi
        role = None
        for r, creds in USERS.items():
            if creds["username"] == username:
                role = r
                break

        if not role:
            error = "Identifiant invalide"
        elif password == USERS[role]["password"]:
            # Redirection selon le rôle
            if role == "renseignement":
                return render_template("Renseignement ICP.html")
            elif role == "consultage":
                return render_template("Consultage.html")
            elif role == "gssi":
                return render_template("Renseignement GSSI.html")
            elif role == "congssi":
                return render_template("ConsultageGSSI.html")
        else:
            error = "Mot de passe incorrect"

    return render_template("login.html", error=error, username=username)


# -------------------- ROUTES --------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/renseignement")
def renseignement_page():
    return redirect(url_for("login", role="renseignement"))

@app.route("/consultage")
def consultage_page():
    return redirect(url_for("login", role="consultage"))

@app.route("/gssi")
def gssi_page():
    return redirect(url_for("login", role="gssi"))

@app.route("/congssi")
def consultage_gssi_page():
    return redirect(url_for("login", role="congssi"))

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
            nom = (agent.get("nom") or "").strip().upper()  # <-- Majuscules ici
            pompes = agent.get("pompes", 0)
            tractions = agent.get("tractions", 0)
            killy = agent.get("killy", 0)
            gainage = agent.get("gainage", 0)
            luc_leger = agent.get("luc_leger", 0)
            souplesse = agent.get("souplesse", 0)

            c.execute("SELECT id FROM icp WHERE nom = %s", (nom,))
            result = c.fetchone()

            if result:
                c.execute("""
                    UPDATE icp
                    SET date=%s, eap=%s, pompes=%s, tractions=%s, killy=%s, gainage=%s, luc_leger=%s, souplesse=%s
                    WHERE nom=%s
                """, (data.get("date"), data.get("eap"), pompes, tractions, killy, gainage, luc_leger, souplesse, nom))
            else:
                c.execute("""
                    INSERT INTO icp (date, eap, nom, pompes, tractions, killy, gainage, luc_leger, souplesse)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (data.get("date"), data.get("eap"), nom, pompes, tractions, killy, gainage, luc_leger, souplesse))

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
            nom = (agent.get("nom") or "").strip().upper()  # <-- Forcer MAJUSCULES
            psc = bool(agent.get("psc"))
            crochet = bool(agent.get("crochet"))
            excavation = bool(agent.get("excavation"))

            c.execute("SELECT id FROM gssi WHERE nom = %s", (nom,))
            result = c.fetchone()

            if result:
                c.execute("""
                    UPDATE gssi
                    SET date=%s, eap=%s, psc=%s, crochet=%s, excavation=%s, grh=FALSE
                    WHERE nom=%s
                """, (data.get("date"), data.get("eap"), psc, crochet, excavation, nom))
            else:
                c.execute("""
                    INSERT INTO gssi (date, eap, nom, psc, crochet, excavation, grh)
                    VALUES (%s, %s, %s, %s, %s, %s, FALSE)
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

# -------------------- UPDATE GRH MUTUALISÉ --------------------
@app.route("/update-grh/<table>", methods=["POST"])
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
        print(f"Erreur update GRH {table}:", e)
        return jsonify({"error": str(e)}), 500

# -------------------- LANCEMENT --------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
