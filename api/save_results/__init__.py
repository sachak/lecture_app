# ============================================================================
#  Azure Function  : save_results
#  Enregistre les réponses expérimentales dans la base SQL Azure
#  --------------------------------------------------------------------------
#  Variables d’application à définir dans Configuration de la Function App :
#     SQL_CONN   → chaîne de connexion ODBC complète vers la base SQL
#     API_SECRET → (optionnel) clé secrète supplémentaire pour le header
# ============================================================================

import os
import json
import logging
import pyodbc
import azure.functions as func

# Crée l’application Function App avec auth LEVEL = FUNCTION
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Récupère les variables d’environnement
SQL_CONN   = os.getenv("SQL_CONN")        # obligatoire
API_SECRET = os.getenv("API_SECRET")      # facultatif

# ---------------------------------------------------------------------------
@app.route(
    route="save_results",                 # URL : /api/save_results
    auth_level=func.AuthLevel.FUNCTION,   # nécessite ?code=...
    methods=["POST"]
)
def save_results(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Réception d'une requête POST /save_results")

    # 1. (Optionnel) Vérifie le header x-api-secret
    if API_SECRET:
        client_secret = req.headers.get("x-api-secret")
        if client_secret != API_SECRET:
            logging.warning("Secret incorrect")
            return func.HttpResponse("Forbidden", status_code=403)

    # 2. Parse le JSON (on attend une LISTE d’objets)
    try:
        data = req.get_json()
        if not isinstance(data, list):
            raise ValueError("JSON must be a list of results")
    except Exception as e:
        logging.error(f"JSON invalide : {e}")
        return func.HttpResponse(f"Invalid JSON : {e}", status_code=400)

    # 3. Ouvre la connexion SQL et insère chaque résultat
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
        return func.HttpResponse("OK", status_code=200)

    except Exception as e:
        logging.exception("Erreur SQL")
        return func.HttpResponse(f"DB error : {e}", status_code=500)
