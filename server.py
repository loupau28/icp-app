from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import psycopg2
import os

app = Flask(__name__)
CORS(app)

# 🔹 URL de connexion PostgreSQL (mettre la tienne ici ou en variable d'environnement)
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:Eiffage.57E4@db.xqpqyksupvnqfvdybqdd.supabase.co:5432/postgres")

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
            souplesse INTEGER
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
                INSERT INTO icp (date, eap, nom, pompes, tractions, killy, gainage, luc_leger, souplesse)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        c.execute('SELECT date, eap, nom, pompes, tractions, killy, gainage, luc_leger, souplesse FROM icp')
        rows = c.fetchall()
        c.close()
        conn.close()

        results = []
        for row in rows:
            results.append({
                'date': row[0],
                'eap': row[1],
                'nom': row[2],
                'pompes': row[3],
                'tractions': row[4],
                'killy': row[5],
                'gainage': row[6],
                'luc_leger': row[7],
                'souplesse': row[8]
            })
        return jsonify(results)

    except Exception as e:
        print(f"Erreur dans /get-icp : {e}")
        return jsonify([])  # Retourne un tableau vide pour éviter de planter le JS

  # place cette fonction au même niveau d'indentation que les autres routes

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
    


