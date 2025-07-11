# ============================================================================
#  save_results  –  Function v1 (Static Web App / dossier api/save_results)
#  Insère les réponses dans dbo.resultats (word, rt_ms, response, phase, participant)
# ============================================================================

import os
import json
import logging
import traceback
import pyodbc
import azure.functions as func

# ---------------------------------------------------------------------------
# Variables d’environnement
# ---------------------------------------------------------------------------
SQL_CONN   = os.getenv("SQL_CONN")        # chaîne ODBC complète (obligatoire)
API_SECRET = os.getenv("API_SECRET")      # header x-api-secret (facultatif)

# ---------------------------------------------------------------------------
# Point d’entrée HTTPTrigger
# ---------------------------------------------------------------------------
def main(req: func.HttpRequest) -> func.HttpResponse:

    # CORS pré-vol
    if req.method == "OPTIONS":
        return _cors(204, "")

    # Secret éventuel
    if API_SECRET and req.headers.get("x-api-secret") != API_SECRET:
        return _cors(403, "Forbidden")

    # Lecture / validation JSON
    try:
        data = req.get_json()
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list")
    except Exception as exc:
        logging.error("Invalid JSON", exc_info=True)
        return _cors(400, f"Invalid JSON : {exc}")

    # Insertion SQL
    try:
        with pyodbc.connect(SQL_CONN, timeout=10) as cnx, cnx.cursor() as cur:
            for row in data:
                cur.execute(
                    """
                    INSERT INTO dbo.resultats
                      (word, rt_ms, response, phase, participant)
                    VALUES (?,?,?,?,?)
                    """,
                    row.get("word",        ""),
                    int(row.get("rt_ms", 0)),
                    row.get("response",    ""),
                    row.get("phase",       ""),
                    row.get("participant", "")
                )
            cnx.commit()
        return _cors(200, "OK")

    except Exception as exc:
        logging.exception("SQL error")
        body = {
            "status"   : 500,
            "error"    : f"DB error : {exc}",
            "traceback": traceback.format_exc()   # visible seulement dans les logs
        }
        return func.HttpResponse(
            json.dumps(body, indent=2),
            status_code = 500,
            mimetype    = "application/json",
            headers     = {"Access-Control-Allow-Origin": "*"}
        )

# ---------------------------------------------------------------------------
# Helper CORS
# ---------------------------------------------------------------------------
def _cors(code: int, body: str) -> func.HttpResponse:
    return func.HttpResponse(
        body,
        status_code = code,
        headers = {
            "Access-Control-Allow-Origin" : "*",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,x-api-secret"
        }
    )
