from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import psycopg2
import os

app = Flask(__name__)
CORS(app)

# 🔹 URL de connexion PostgreSQL (mettre la tienne ici ou en variable d'environnement)
DATABASE_URL = os.environ.get("DATABASE_URL", "postgres://postgres:Eiffage.57E4@db.xqpqyksupvnqfvdybqdd.supabase.co:5432/postgres")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS icp (
            id SERIAL PRIMARY KEY,
            date TEXT,
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
    data = request.get_json()
    conn = get_db_connection()
    c = conn.cursor()
    for agent in data["agents"]:
        c.execute("""
            INSERT INTO icp (date, eap, nom, pompes, tractions, killy, gainage, luc_leger, souplesse)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data["date"], data["eap"], agent["nom"],
            agent["pompes"], agent["tractions"], agent["killy"],
            agent["gainage"], agent["luc_leger"], agent["souplesse"]
        ))
    conn.commit()
    c.close()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/get-icp', methods=['GET'])
def get_icp():
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

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
