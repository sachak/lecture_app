# ============================================================================
#  Azure Function  : save_results
#  Enregistre les réponses expérimentales dans la base SQL Azure
# ============================================================================

import os
import logging
import json
import pyodbc
import azure.functions as func

# ----------------------------------------------------------------------------
# 1. Création de l'application Functions (modèle Python v2)
# ----------------------------------------------------------------------------
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# ----------------------------------------------------------------------------
# 2. Variables d'environnement
# ----------------------------------------------------------------------------
SQL_CONN   = os.getenv("SQL_CONN")        # obligatoire
API_SECRET = os.getenv("API_SECRET")      # facultatif

# ----------------------------------------------------------------------------
# 3. Route HTTP
# ----------------------------------------------------------------------------
@app.route(
    route="save_results",                 # URL : /api/save_results
    methods=["POST", "OPTIONS"],          # ← POST + OPTIONS
    auth_level=func.AuthLevel.FUNCTION
)
def save_results(req: func.HttpRequest) -> func.HttpResponse:
    # ------------------------------------------------------------------------
    # A. Requête OPTIONS = pré-vol CORS  -------------------------------------
    # ------------------------------------------------------------------------
    if req.method == "OPTIONS":
        return func.HttpResponse(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin":  "*",
                "Access-Control-Allow-Methods": "POST,OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type,x-api-secret"
            }
        )

    # ------------------------------------------------------------------------
    # B. Vérification éventuelle du header x-api-secret
    # ------------------------------------------------------------------------
    logging.info("Réception d'une requête POST /save_results")
    if API_SECRET:
        client_secret = req.headers.get("x-api-secret")
        if client_secret != API_SECRET:
            logging.warning("Secret incorrect")
            return func.HttpResponse(
                "Forbidden",
                status_code=403,
                headers={"Access-Control-Allow-Origin": "*"}
            )

    # ------------------------------------------------------------------------
    # C. Lecture du JSON
    # ------------------------------------------------------------------------
    try:
        data = req.get_json()
        if not isinstance(data, list):
            raise ValueError("JSON must be a list of results")
    except Exception as e:
        logging.error(f"JSON invalide : {e}")
        return func.HttpResponse(
            f"Invalid JSON : {e}",
            status_code=400,
            headers={"Access-Control-Allow-Origin": "*"}
        )

    # ------------------------------------------------------------------------
    # D. Insertion SQL
    # ------------------------------------------------------------------------
    try:
        conn = pyodbc.connect(SQL_CONN, timeout=5)
        cursor = conn.cursor()

        for r in data:
            cursor.execute(
                """
                INSERT INTO resultats (word, rt_ms, response, phase)
                VALUES (?, ?, ?, ?)
                """,
                r.get("word", ""),
                int(r.get("rt_ms", 0)),
                r.get("response", ""),
                r.get("phase", "")
            )

        conn.commit()
        cursor.close()
        conn.close()
        logging.info("Insertion terminée avec succès")
        return func.HttpResponse(
            "OK",
            status_code=200,
            headers={"Access-Control-Allow-Origin": "*"}
        )

    except Exception as e:
        logging.exception("Erreur SQL")
        return func.HttpResponse(
            f"DB error : {e}",
            status_code=500,
            headers={"Access-Control-Allow-Origin": "*"}
        )
