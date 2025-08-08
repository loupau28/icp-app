from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

def init_db():
    conn = sqlite3.connect("icp.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS icp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    conn.close()

# Routes HTML
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/consultage")
def consultage():
    return render_template("Consultage.html")

@app.route("/renseignement")
def renseignement():
    return render_template("Renseignement ICP.html")

# API : Sauvegarde ICP
@app.route("/save-icp", methods=["POST"])
def save_icp():
    data = request.get_json()
    conn = sqlite3.connect("icp.db")
    c = conn.cursor()
    for agent in data["agents"]:
        c.execute("""
            INSERT INTO icp (date, eap, nom, pompes, tractions, killy, gainage, luc_leger, souplesse)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["date"], data["eap"], agent["nom"],
            agent["pompes"], agent["tractions"], agent["killy"],
            agent["gainage"], agent["luc_leger"], agent["souplesse"]
        ))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

# API : Consultation ICP
@app.route('/get-icp', methods=['GET'])
def get_icp():
    conn = sqlite3.connect('icp.db')
    cursor = conn.cursor()
    cursor.execute('SELECT date, eap, nom, pompes, tractions, killy, gainage, luc_leger, souplesse FROM icp')
    rows = cursor.fetchall()
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
