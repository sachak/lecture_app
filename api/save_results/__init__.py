# ============================================================================
# Azure Function : save_results  –  version “montre-moi TOUT”
#  • Affiche les erreurs d'import (pyodbc manquant, etc.)
#  • Paramètre ?debug=1  → force le statut HTTP à 200 pour voir le corps
#    même si l'erreur est interne
# ============================================================================
import os
import json
import logging
import traceback
import azure.functions as func

# ---------------------------------------------------------------------------
# 0) Tentative d'importation de pyodbc
# ---------------------------------------------------------------------------
try:
    import pyodbc
    PYODBC_IMPORT_ERROR = None
except Exception as e:
    # Le module n'existe pas ou autre souci → on mémorise l'erreur
    pyodbc = None
    PYODBC_IMPORT_ERROR = e

# ---------------------------------------------------------------------------
# 1) Objet FunctionApp
# ---------------------------------------------------------------------------
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# ---------------------------------------------------------------------------
# 2) Variables d'environnement
# ---------------------------------------------------------------------------
SQL_CONN   = os.getenv("SQL_CONN")          # Chaîne de connexion OBLIGATOIRE
API_SECRET = os.getenv("API_SECRET")        # Facultatif

# ---------------------------------------------------------------------------
# 3) Route HTTP
# ---------------------------------------------------------------------------
@app.route(
    route="save_results",
    methods=["POST", "OPTIONS"],
    auth_level=func.AuthLevel.FUNCTION
)
def save_results(req: func.HttpRequest) -> func.HttpResponse:
    # debug=1 → on renvoie toujours 200 pour forcer l'affichage du corps
    debug = req.params.get("debug", "0").lower() in ("1", "true")

    # -----------------------------------------------------------------------
    # A) OPTIONS = pré-vol CORS
    # -----------------------------------------------------------------------
    if req.method == "OPTIONS":
        return _cors(204, "")

    # -----------------------------------------------------------------------
    # B) Erreur d'import pyodbc ?
    # -----------------------------------------------------------------------
    if PYODBC_IMPORT_ERROR is not None:
        return _problem(
            500,
            f"Cannot import pyodbc : {PYODBC_IMPORT_ERROR}",
            debug,
            include_trace=True
        )

    # -----------------------------------------------------------------------
    # C) Secret éventuel
    # -----------------------------------------------------------------------
    if API_SECRET and req.headers.get("x-api-secret") != API_SECRET:
        return _problem(403, "Wrong or missing x-api-secret header", debug)

    # -----------------------------------------------------------------------
    # D) Chaîne de connexion présente ?
    # -----------------------------------------------------------------------
    if not SQL_CONN:
        return _problem(500, "Environment variable SQL_CONN is missing", debug)

    # -----------------------------------------------------------------------
    # E) Lecture / validation JSON
    # -----------------------------------------------------------------------
    try:
        data = req.get_json()
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list")
    except Exception as exc:
        return _problem(400, f"Invalid JSON : {exc}", debug, include_trace=True)

    # -----------------------------------------------------------------------
    # F) Insertion SQL
    # -----------------------------------------------------------------------
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

        return _cors(200, "OK")

    except Exception as exc:
        logging.exception("SQL error")
        return _problem(500, f"DB error : {exc}", debug, include_trace=True)

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
             include_trace: bool = False) -> func.HttpResponse:

    body = {"status": code, "error": message}
    if include_trace:
        body["traceback"] = traceback.format_exc()

    # Si debug=1 → on force le code HTTP à 200
    http_code = 200 if debug else code

    return func.HttpResponse(
        json.dumps(body, ensure_ascii=False, indent=2),
        status_code=http_code,
        mimetype="application/json",
        headers={"Access-Control-Allow-Origin": "*"}
    )
