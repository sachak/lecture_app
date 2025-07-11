# ============================================================================
# Azure Function : save_results  (version "montre-moi-l'erreur")
# ============================================================================
import os
import json
import logging
import traceback
import pyodbc
import azure.functions as func

# ----------------------------------------------------------------------------
# 1. Application Functions (Python v2)
# ----------------------------------------------------------------------------
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# ----------------------------------------------------------------------------
# 2. Variables d’environnement obligatoires / facultatives
# ----------------------------------------------------------------------------
SQL_CONN   = os.getenv("SQL_CONN")          # Chaîne de connexion SQL OBLIGATOIRE
API_SECRET = os.getenv("API_SECRET")        # Secret facultatif

# ----------------------------------------------------------------------------
# 3. Route HTTP
# ----------------------------------------------------------------------------
@app.route(
    route="save_results",
    methods=["POST", "OPTIONS"],
    auth_level=func.AuthLevel.FUNCTION
)
def save_results(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/save_results
    Si l’URL comporte ?debug=1  →  la fonction renvoie 200 même en cas d’erreur
    et inclut la stack-trace complète dans le corps de la réponse.
    """
    # true si ?debug=1 ou ?debug=true
    debug_requested = req.params.get("debug", "0").lower() in ("1", "true")

    # ------------------------------------------------------------------------
    # A. Pré-vol CORS (OPTIONS)
    # ------------------------------------------------------------------------
    if req.method == "OPTIONS":
        return _cors_response(204)

    logging.info("Requête POST reçue sur /save_results")

    # ------------------------------------------------------------------------
    # B. Secret éventuel
    # ------------------------------------------------------------------------
    if API_SECRET and req.headers.get("x-api-secret") != API_SECRET:
        return _error(403, "Wrong or missing x-api-secret header", debug_requested)

    # ------------------------------------------------------------------------
    # C. Chaîne de connexion présente ?
    # ------------------------------------------------------------------------
    if not SQL_CONN:
        return _error(500, "Environment variable SQL_CONN is missing!",
                      debug_requested, include_trace=True)

    # ------------------------------------------------------------------------
    # D. JSON
    # ------------------------------------------------------------------------
    try:
        data = req.get_json()
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list")
    except Exception as exc:
        return _error(400, f"Invalid JSON : {exc}",
                      debug_requested, include_trace=True)

    # ------------------------------------------------------------------------
    # E. Insertion SQL
    # ------------------------------------------------------------------------
    try:
        with pyodbc.connect(SQL_CONN, timeout=5) as conn:
            with conn.cursor() as cursor:
                for row in data:
                    _validate_row(row)
                    cursor.execute(
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
        return _cors_response(200, body="OK")

    except Exception as exc:
        logging.exception("Erreur SQL")
        return _error(500, f"DB error : {exc}",
                      debug_requested, include_trace=True)

# =============================================================================
# Fonctions utilitaires
# =============================================================================
def _validate_row(row: dict):
    required = ["word", "rt_ms", "response", "phase"]
    missing  = [k for k in required if k not in row]
    if missing:
        raise ValueError("Missing keys in result object: " + ", ".join(missing))

def _cors_response(status_code: int, body: str | None = None) -> func.HttpResponse:
    return func.HttpResponse(
        body or "",
        status_code=status_code,
        headers={
            "Access-Control-Allow-Origin":  "*",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,x-api-secret"
        }
    )

def _error(status_code: int,
           message: str,
           debug_requested: bool,
           include_trace: bool = False) -> func.HttpResponse:
    """
    Construit la réponse d’erreur.
    • Si debug_requested = True  → status_code devient 200 pour forcer l’affichage.
    • include_trace = True       → on ajoute traceback.format_exc() dans le body.
    """
    body = {"status": status_code, "error": message}

    if include_trace:
        body["traceback"] = traceback.format_exc()

    # —————————————
    # Forcer 200 si le client a précisé ?debug=1
    # —————————————
    http_code = 200 if debug_requested else status_code

    return func.HttpResponse(
        json.dumps(body, ensure_ascii=False, indent=2),
        status_code=http_code,
        mimetype="application/json",
        headers={"Access-Control-Allow-Origin": "*"}
    )
