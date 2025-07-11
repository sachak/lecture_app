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

# Variables d’environnement --------------------------------------------------
SQL_CONN   = os.getenv("SQL_CONN")        # chaîne ODBC obligatoire
API_SECRET = os.getenv("API_SECRET")      # header x-api-secret facultatif
# ---------------------------------------------------------------------------
# Variables d’environnement
# ---------------------------------------------------------------------------
SQL_CONN   = os.getenv("SQL_CONN")        # chaîne ODBC complète (obligatoire)
API_SECRET = os.getenv("API_SECRET")      # header x-api-secret (facultatif)

# ----------------------------------------------------------------------------
# Point d’entrée v1 : def main(req: func.HttpRequest)
# ----------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Point d’entrée HTTPTrigger
# ---------------------------------------------------------------------------
def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/save_results
    Corps attendu : liste JSON d’objets
      [{word, rt_ms, response, phase}, …]
    """

    # ── A. Pré-vol CORS (OPTIONS) ───────────────────────────────────────────
    # CORS pré-vol
    if req.method == "OPTIONS":
        return _cors(204, "")

    logging.info("POST /save_results reçu")

    # ── B. Vérification du secret ──────────────────────────────────────────
    # Secret éventuel
    if API_SECRET and req.headers.get("x-api-secret") != API_SECRET:
        return _cors(403, "Forbidden")

    # ── C. Lecture + validation du JSON ────────────────────────────────────
    # Lecture / validation JSON
    try:
        data = req.get_json()
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list")
    except Exception as exc:
        logging.error("JSON invalide : %s", exc, exc_info=True)
        logging.error("Invalid JSON", exc_info=True)
        return _cors(400, f"Invalid JSON : {exc}")

    # ── D. Insertion SQL ───────────────────────────────────────────────────
    # Insertion SQL
    try:
        with pyodbc.connect(SQL_CONN, timeout=10) as cnx, cnx.cursor() as cur:
            for row in data:
                cur.execute(
                    "INSERT INTO dbo.resultats (word, rt_ms, response, phase)"
                    "VALUES (?,?,?,?)",
                    row.get("word", ""),
                    """
                    INSERT INTO dbo.resultats
                      (word, rt_ms, response, phase, participant)
                    VALUES (?,?,?,?,?)
                    """,
                    row.get("word",        ""),
                    int(row.get("rt_ms", 0)),
                    row.get("response", ""),
                    row.get("phase", "")
                    row.get("response",    ""),
                    row.get("phase",       ""),
                    row.get("participant", "")
                )
            cnx.commit()
        return _cors(200, "OK")

    except Exception as exc:
        logging.exception("Erreur SQL")
        logging.exception("SQL error")
        body = {
            "status": 500,
            "error": f"DB error : {exc}",
            "traceback": traceback.format_exc()
            "status"   : 500,
            "error"    : f"DB error : {exc}",
            "traceback": traceback.format_exc()   # visible seulement dans les logs
        }
        # réponse 200 si ?debug=1 pour l’afficher dans le navigateur
        debug = req.params.get("debug") in ("1", "true")
        return func.HttpResponse(
            json.dumps(body, indent=2),
            status_code=200 if debug else 500,
            mimetype="application/json",
            headers={"Access-Control-Allow-Origin": "*"}
            status_code = 500,
            mimetype    = "application/json",
            headers     = {"Access-Control-Allow-Origin": "*"}
        )

# ── Fonctions utilitaires ───────────────────────────────────────────────────
# ---------------------------------------------------------------------------
# Helper CORS
# ---------------------------------------------------------------------------
def _cors(code: int, body: str) -> func.HttpResponse:
    return func.HttpResponse(
        body,
        status_code=code,
        headers={
            "Access-Control-Allow-Origin":  "*",
        status_code = code,
        headers = {
            "Access-Control-Allow-Origin" : "*",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,x-api-secret"
        }
