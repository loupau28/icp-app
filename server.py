from flask import Flask, request, render_template, redirect, url_for
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
        username = request.args.get("user")
        if not username:
            # Redirige vers login avec next
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
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

# -------------------- ROUTES --------------------
# -------------------- ROUTES --------------------
@app.route("/")
def index():
    # Retour à l'index → oubli du login
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
    return render_template("Consultage.html")  # créer ce template

@app.route("/consultation/gssi")
@login_required
@role_required(["BFOR-TAV"])
def consultation_gssi_page():
    return render_template("ConsultageGSSI.html")  # créer ce template

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

# -------------------- LANCEMENT --------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
