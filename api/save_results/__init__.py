# ============================================================================
# Azure Function : save_results  –  version “affiche-moi l’erreur”
# ============================================================================
import os
import json
import logging
import traceback
import pyodbc
import azure.functions as func

# ----------------------------------------------------------------------------
# 1) Objet FunctionApp (Python v2)
# ----------------------------------------------------------------------------
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# ----------------------------------------------------------------------------
# 2) Variables d'environnement
# ----------------------------------------------------------------------------
SQL_CONN   = os.getenv("SQL_CONN")          # Chaîne de connexion OBLIGATOIRE
API_SECRET = os.getenv("API_SECRET")        # Facultatif

# ----------------------------------------------------------------------------
# 3) Route HTTP
# ----------------------------------------------------------------------------
@app.route(
    route="save_results",
    methods=["POST", "OPTIONS"],
    auth_level=func.AuthLevel.FUNCTION
)
def save_results(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/save_results
    • ?debug=1   → on renvoie TOUJOURS 200 pour forcer l'affichage du corps.
    • sinon      → 400 ou 500 selon la situation normale.
    Le corps contient systématiquement un JSON avec 'status', 'error',
    et, en cas d'exception, 'traceback'.
    """
    debug = req.params.get("debug", "0").lower() in ("1", "true")

    # ------------------------------------------------------------------------
    # A) Pré-vol CORS
    # ------------------------------------------------------------------------
    if req.method == "OPTIONS":
        return _cors(204, "")

    logging.info("POST /save_results reçu")

    # ------------------------------------------------------------------------
    # B) Vérification du secret (si défini)
    # ------------------------------------------------------------------------
    if API_SECRET and req.headers.get("x-api-secret") != API_SECRET:
        return _problem(403, "Wrong or missing x-api-secret header", debug)

    # ------------------------------------------------------------------------
    # C) Vérification de SQL_CONN
    # ------------------------------------------------------------------------
    if not SQL_CONN:
        return _problem(500, "Environment variable SQL_CONN is missing", debug)

    # ------------------------------------------------------------------------
    # D) Lecture + validation du JSON
    # ------------------------------------------------------------------------
    try:
        data = req.get_json()
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list")
    except Exception as exc:                            # JSON invalide → 400
        return _problem(400, f"Invalid JSON : {exc}", debug, True)

    # ------------------------------------------------------------------------
    # E) Insertion en base
    # ------------------------------------------------------------------------
    try:
        with pyodbc.connect(SQL_CONN, timeout=5) as conn:
            with conn.cursor() as cur:
                for row in data:
                    _validate(row)
                    cur.execute(
                        """
                        INSERT INTO resultats (word, rt_ms, response, phase)
                        VALUES (?, ?, ?, ?)
                        """,
                        row["word"],
                        int(row["rt_ms"]),
                        row["response"],
                        row["phase"]
                    )
            conn.commit()

        logging.info("Insertion terminée")
        return _cors(200, "OK")

    except Exception as exc:                            # Erreur SQL → 500
        logging.exception("SQL error")
        return _problem(500, f"DB error : {exc}", debug, True)

# =============================================================================
# Fonctions utilitaires
# =============================================================================
def _validate(row: dict):
    needed = ["word", "rt_ms", "response", "phase"]
    miss   = [k for k in needed if k not in row]
    if miss:
        raise ValueError("Missing keys : " + ", ".join(miss))

def _cors(code: int, body: str) -> func.HttpResponse:
    return func.HttpResponse(
        body,
        status_code=code,
        headers={
            "Access-Control-Allow-Origin":  "*",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,x-api-secret"
        }
    )

def _problem(code: int,
             message: str,
             debug: bool,
             add_trace: bool = False) -> func.HttpResponse:
    """
    Construit une réponse d'erreur.
    Si ?debug=1 → on force le code HTTP à 200 pour que le navigateur
    affiche le JSON. Sinon, on renvoie le code réel (4xx ou 5xx).
    """
    body = {"status": code, "error": message}
    if add_trace:
        body["traceback"] = traceback.format_exc()

    http_code = 200 if debug else code

    return func.HttpResponse(
        json.dumps(body, ensure_ascii=False, indent=2),
        status_code=http_code,
        mimetype="application/json",
        headers={"Access-Control-Allow-Origin": "*"}
    )
