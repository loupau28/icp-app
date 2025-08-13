from flask import Flask, request, jsonify, render_template, redirect, url_for, Response
from flask_cors import CORS
import psycopg2
import os
from functools import wraps

app = Flask(__name__)
CORS(app)

# -------- Identifiants --------
USERNAME_RENSEIGNEMENT = "EAP-TAV"
PASSWORD_RENSEIGNEMENT = "EAP-TAV95"

USERNAME_CONSULTAGE = "BFOR-TAV"
PASSWORD_CONSULTAGE = "BFOR-TAV95"

USERNAME_SOG = "SOG-TAV"
PASSWORD_SOG = "SOG-TAV95"

DATABASE_URL = os.environ.get("DATABASE_URL")

# -------- DB connection --------
def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    # Table ICP
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
    
    # Table GSSI
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

# -------- Basic Auth helpers --------
def check_auth(username, password, role=None):
    """Vérifie le couple username/password selon le rôle"""
    if role == "renseignement":
        return username == USERNAME_RENSEIGNEMENT and password == PASSWORD_RENSEIGNEMENT
    elif role == "consultage":
        return username == USERNAME_CONSULTAGE and password == PASSWORD_CONSULTAGE
    elif role == "gssi":
        return username == USERNAME_SOG and password == PASSWORD_SOG
    return False

def authenticate():
    """Renvoie 401 si non authentifié"""
    return Response(
        'Authentification requise', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(role):
    """Décorateur pour protéger les routes selon le rôle"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = request.authorization
            if not auth or not check_auth(auth.username, auth.password, role):
                return authenticate()
            return f(*args, **kwargs)
        return decorated
    return decorator

# -------- Routes publiques --------
@app.route("/")
def home():
    return render_template("index.html")

# -------- Routes protégées --------
@app.route("/renseignement")
@requires_auth("renseignement")
def renseignement():
    return render_template("Renseignement ICP.html")

@app.route("/consultage")
@requires_auth("consultage")
def consultage():
    return render_template("Consultage.html")

@app.route("/renseignementgssi")
@requires_auth("gssi")
def renseignementgssi():
    return render_template("Renseignement GSSI.html")

# -------- ICP routes --------
@app.route("/save-icp", methods=["POST"])
@requires_auth("renseignement")
def save_icp():
    try:
        data = request.get_json()
        if not data or "agents" not in data or not isinstance(data["agents"], list):
            return jsonify({"status": "error", "message": "Format des agents incorrect"}), 400

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
                    data.get("date"), data.get("eap"), agent.get("pompes"), agent.get("tractions"),
                    agent.get("killy"), agent.get("gainage"), agent.get("luc_leger"), agent.get("souplesse"),
                    nom
                ))
            else:
                c.execute("""
                    INSERT INTO icp (date, eap, nom, pompes, tractions, killy, gainage, luc_leger, souplesse, grh)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE)
                """, (
                    data.get("date"), data.get("eap"), nom,
                    agent.get("pompes"), agent.get("tractions"), agent.get("killy"),
                    agent.get("gainage"), agent.get("luc_leger"), agent.get("souplesse")
                ))

        conn.commit()
        c.close()
        conn.close()
        return jsonify({"status": "ok"})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get-icp', methods=['GET'])
@requires_auth("consultage")
def get_icp():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT id, date, eap, nom, pompes, tractions, killy, gainage, luc_leger, souplesse, grh FROM icp')
        rows = c.fetchall()
        c.close()
        conn.close()

        results = []
        for row in rows:
            results.append({
                'id': row[0], 'date': row[1], 'eap': row[2], 'nom': row[3],
                'pompes': row[4], 'tractions': row[5], 'killy': row[6],
                'gainage': row[7], 'luc_leger': row[8], 'souplesse': row[9],
                'grh': row[10]
            })
        return jsonify(results)

    except Exception as e:
        print(f"Erreur dans /get-icp : {e}")
        return jsonify([])

@app.route("/update-grh", methods=["POST"])
@requires_auth("consultage")
def update_grh():
    try:
        data = request.get_json()
        ids = data.get("ids", [])
        if not ids:
            return jsonify({"success": False, "error": "Aucun ID reçu"}), 400
        try:
            ids = [int(i) for i in ids]
        except ValueError:
            return jsonify({"success": False, "error": "IDs invalides"}), 400

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE icp SET grh = TRUE WHERE id = ANY(%s)", (ids,))
        conn.commit()
        c.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

# -------- GSSI routes --------
@app.route("/save-gssi", methods=["POST"])
@requires_auth("gssi")
def save_gssi():
    try:
        data = request.get_json()
        if not data or "agents" not in data or not isinstance(data["agents"], list):
            return jsonify({"status": "error", "message": "Format des agents incorrect"}), 400

        conn = get_db_connection()
        c = conn.cursor()

        for agent in data["agents"]:
            nom = agent.get("nom")
            psc = True if agent.get("psc") in [True, "true", "on", "1"] else False
            crochet = True if agent.get("crochet") in [True, "true", "on", "1"] else False
            excavation = True if agent.get("excavation") in [True, "true", "on", "1"] else False

            c.execute("SELECT id FROM gssi WHERE nom = %s", (nom,))
            result = c.fetchone()

            if result:
                c.execute("""
                    UPDATE gssi SET date=%s, eap=%s, psc=%s, crochet=%s, excavation=%s, grh=FALSE
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

@app.route('/get-gssi', methods=['GET'])
@requires_auth("consultage")
def get_gssi():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT id, date, eap, nom, psc, crochet, excavation, grh FROM gssi')
        rows = c.fetchall()
        c.close()
        conn.close()

        results = []
        for row in rows:
            results.append({
                'id': row[0], 'date': row[1], 'eap': row[2], 'nom': row[3],
                'psc': row[4], 'crochet': row[5], 'excavation': row[6],
                'grh': row[7]
            })
        return jsonify(results)
    except Exception as e:
        print(f"Erreur dans /get-gssi : {e}")
        return jsonify([])

# -------- Test DB --------
@app.route("/test-db")
def test_db():
    try:
        conn = get_db_connection()
        conn.close()
        return "Connexion réussie à la base de données !"
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Erreur de connexion : {e}", 500

# -------- Run App --------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
