from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import psycopg2
import os

app = Flask(__name__)
CORS(app)

# 🔹 URL de connexion PostgreSQL (mettre la tienne ici ou en variable d'environnement)
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Ajout de la colonne grh
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
    conn.commit()
    c.close()
    conn.close()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/consultage")
def consultage():
    return render_template("Consultage.html")

@app.route("/renseignement")
def renseignement():
    return render_template("Renseignement ICP.html")

@app.route("/save-icp", methods=["POST"])
def save_icp():
    try:
        data = request.get_json()
        print("Données reçues dans /save-icp :", data)

        if not data:
            return jsonify({"status": "error", "message": "Pas de données reçues"}), 400
        
        if "agents" not in data or not isinstance(data["agents"], list):
            return jsonify({"status": "error", "message": "Format des agents incorrect"}), 400

        conn = get_db_connection()
        print("Connexion DB OK")
        c = conn.cursor()

        for agent in data["agents"]:
            print("Agent:", agent)
            c.execute("""
                INSERT INTO icp (date, eap, nom, pompes, tractions, killy, gainage, luc_leger, souplesse, grh)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE)
            """, (
                data.get("date"), data.get("eap"), agent.get("nom"),
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
                'id': row[0],
                'date': row[1],
                'eap': row[2],
                'nom': row[3],
                'pompes': row[4],
                'tractions': row[5],
                'killy': row[6],
                'gainage': row[7],
                'luc_leger': row[8],
                'souplesse': row[9],
                'grh': row[10]
            })
        return jsonify(results)

    except Exception as e:
        print(f"Erreur dans /get-icp : {e}")
        return jsonify([])  # Retourne un tableau vide pour éviter de planter le JS


# 🔹 Nouvelle route pour mettre à jour les cases cochées
@app.route("/update-grh", methods=["POST"])
def update_grh():
    try:
        data = request.get_json()
        ids = data.get("ids", [])

        if not ids:
            return jsonify({"success": False, "error": "Aucun ID reçu"}), 400

        conn = get_db_connection()
        c = conn.cursor()

        # Met à jour tous les enregistrements dont l'id est dans la liste
        c.execute("UPDATE icp SET grh = TRUE WHERE id = ANY(%s)", (ids,))
        
        conn.commit()
        c.close()
        conn.close()

        return jsonify({"success": True})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


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
 
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
