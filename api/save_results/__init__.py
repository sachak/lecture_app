import os
import json
import logging
import traceback
import pyodbc
import azure.functions as func

# Variables d’environnement --------------------------------------------------
SQL_CONN   = os.getenv("SQL_CONN")        # chaîne ODBC obligatoire
API_SECRET = os.getenv("API_SECRET")      # header x-api-secret facultatif

# ----------------------------------------------------------------------------
# Point d’entrée v1 : def main(req: func.HttpRequest)
# ----------------------------------------------------------------------------
def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/save_results
    Corps attendu : liste JSON d’objets
      [{word, rt_ms, response, phase}, …]
    """

    # ── A. Pré-vol CORS (OPTIONS) ───────────────────────────────────────────
    if req.method == "OPTIONS":
        return _cors(204, "")

    logging.info("POST /save_results reçu")

    # ── B. Vérification du secret ──────────────────────────────────────────
    if API_SECRET and req.headers.get("x-api-secret") != API_SECRET:
        return _cors(403, "Forbidden")

    # ── C. Lecture + validation du JSON ────────────────────────────────────
    try:
        data = req.get_json()
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list")
    except Exception as exc:
        logging.error("JSON invalide : %s", exc, exc_info=True)
        return _cors(400, f"Invalid JSON : {exc}")

    # ── D. Insertion SQL ───────────────────────────────────────────────────
    try:
        with pyodbc.connect(SQL_CONN, timeout=10) as cnx, cnx.cursor() as cur:
            for row in data:
                cur.execute(
                    "INSERT INTO dbo.resultats (word, rt_ms, response, phase)"
                    "VALUES (?,?,?,?)",
                    row.get("word", ""),
                    int(row.get("rt_ms", 0)),
                    row.get("response", ""),
                    row.get("phase", "")
                )
            cnx.commit()
        return _cors(200, "OK")

    except Exception as exc:
        logging.exception("Erreur SQL")
        body = {
            "status": 500,
            "error": f"DB error : {exc}",
            "traceback": traceback.format_exc()
        }
        # réponse 200 si ?debug=1 pour l’afficher dans le navigateur
        debug = req.params.get("debug") in ("1", "true")
        return func.HttpResponse(
            json.dumps(body, indent=2),
            status_code=200 if debug else 500,
            mimetype="application/json",
            headers={"Access-Control-Allow-Origin": "*"}
        )

# ── Fonctions utilitaires ───────────────────────────────────────────────────
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
