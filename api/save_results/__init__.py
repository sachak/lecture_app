# ============================================================================
# Azure Function : save_results
# Enregistre les réponses expérimentales dans la base SQL Azure
# Modèle Functions Python v2  (decorator @app.route)
# ============================================================================

import os
import json
import logging
import traceback
import pyodbc
import azure.functions as func

# ----------------------------------------------------------------------------
# 1. Création de l’application Functions
# ----------------------------------------------------------------------------
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# ----------------------------------------------------------------------------
# 2. Variables d’environnement
# ----------------------------------------------------------------------------
SQL_CONN   = os.getenv("SQL_CONN")        # chaîne ODBC complète (obligatoire)
API_SECRET = os.getenv("API_SECRET")      # x-api-secret attendu (facultatif)

# ----------------------------------------------------------------------------
# 3. Point d’entrée HTTP
# ----------------------------------------------------------------------------
@app.route(
    route="save_results",                 # URL : /api/save_results
    methods=["POST", "OPTIONS"],
    auth_level=func.AuthLevel.FUNCTION
)
def save_results(req: func.HttpRequest) -> func.HttpResponse:
    """
    Reçoit un tableau JSON d’objets :
        [{ "word": "...", "rt_ms": 123, "response": "...", "phase": "..." }, …]
    Insère chaque ligne dans dbo.resultats.
    """

    # --------------------------------------------------------------------- A.
    # Pré–vol CORS  (méthode OPTIONS)
    # -------------------------------------------------------------------------
    if req.method == "OPTIONS":
        return func.HttpResponse(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin":  "*",
                "Access-Control-Allow-Methods": "POST,OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type,x-api-secret",
            },
        )

    logging.info("POST /save_results reçu")

    # --------------------------------------------------------------------- B.
    # Vérification éventuelle du header x-api-secret
    # -------------------------------------------------------------------------
    if API_SECRET:
        if req.headers.get("x-api-secret") != API_SECRET:
            logging.warning("x-api-secret incorrect ou manquant")
            return func.HttpResponse(
                "Forbidden",
                status_code=403,
                headers={"Access-Control-Allow-Origin": "*"},
            )

    # --------------------------------------------------------------------- C.
    # Lecture + validation du corps JSON
    # -------------------------------------------------------------------------
    try:
        data = req.get_json()
        if not isinstance(data, list):
            raise ValueError("Le JSON racine doit être une liste")
    except Exception as exc:
        logging.error("JSON invalide : %s", exc, exc_info=True)
        return func.HttpResponse(
            f"Invalid JSON : {exc}",
            status_code=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    # --------------------------------------------------------------------- D.
    # Insertion en base
    # -------------------------------------------------------------------------
    try:
        with pyodbc.connect(SQL_CONN, timeout=10) as conn:
            with conn.cursor() as cur:
                for row in data:
                    cur.execute(
                        """
                        INSERT INTO dbo.resultats (word, rt_ms, response, phase)
                        VALUES (?, ?, ?, ?)
                        """,
                        row.get("word", ""),
                        int(row.get("rt_ms", 0)),
                        row.get("response", ""),
                        row.get("phase", ""),
                    )
            conn.commit()

        logging.info("Insertion terminée avec succès")
        return func.HttpResponse(
            "OK",
            status_code=200,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    # --------------------------------------------------------------------- E.
    # Gestion des erreurs SQL
    # -------------------------------------------------------------------------
    except Exception as exc:
        logging.exception("Erreur SQL")
        return func.HttpResponse(
            f"DB error : {exc}",
            status_code=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )
