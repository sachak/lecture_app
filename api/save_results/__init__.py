# ============================================================================
# Azure Function : save_results
# Enregistre les réponses expérimentales dans une base SQL Azure
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
# 2. Variables d’environnement
# ----------------------------------------------------------------------------
SQL_CONN   = os.getenv("SQL_CONN")        # Chaîne de connexion OBLIGATOIRE
API_SECRET = os.getenv("API_SECRET")      # Secret facultatif
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

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
    Corps attendu : liste JSON d’objets {word, rt_ms, response, phase}
    """

    # ------------------------------------------------------------------------
    # A. Pré-vol CORS (OPTIONS)
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

    logging.info("Requête POST reçue sur /save_results")

    # ------------------------------------------------------------------------
    # B. Vérification du secret (si activé)
    # ------------------------------------------------------------------------
    if API_SECRET:
        client_secret = req.headers.get("x-api-secret")
        if client_secret != API_SECRET:
            logging.warning("x-api-secret incorrect ou manquant")
            return _error(403, "Wrong or missing x-api-secret header")

    # ------------------------------------------------------------------------
    # C. Vérification de SQL_CONN
    # ------------------------------------------------------------------------
    if not SQL_CONN:
        return _fatal("La variable d’environnement SQL_CONN est manquante")

    # ------------------------------------------------------------------------
    # D. Lecture + validation du JSON
    # ------------------------------------------------------------------------
    try:
        data = req.get_json()
        if not isinstance(data, list):
            raise ValueError("Le JSON racine doit être une liste")
    except Exception as exc:
        logging.error("JSON invalide : %s", exc, exc_info=True)
        return _error(400, f"Invalid JSON : {exc}")

    # ------------------------------------------------------------------------
    # E. Insertion SQL
    # ------------------------------------------------------------------------
    try:
        with pyodbc.connect(SQL_CONN, timeout=5) as conn:
            with conn.cursor() as cursor:
                for row in data:
                    _check_row_schema(row)  # Validation stricte
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

        logging.info("Insertion terminée avec succès")
        return func.HttpResponse(
            "OK",
            status_code=200,
            headers={"Access-Control-Allow-Origin": "*"}
        )

    except Exception as exc:
        logging.exception("Erreur SQL")
        return _fatal(f"DB error : {exc}")


# =============================================================================
# Fonctions utilitaires
# =============================================================================
def _check_row_schema(row: dict) -> None:
    """
    Validation d’un élément de la liste `data`.
    Soulève ValueError si des clés obligatoires sont manquantes.
    """
    required = ["word", "rt_ms", "response", "phase"]
    missing  = [k for k in required if k not in row]
    if missing:
        raise ValueError(f"Missing keys in result object: {', '.join(missing)}")


def _error(status_code: int, message: str) -> func.HttpResponse:
    """
    Réponse d’erreur côté client (4xx).
    """
    return func.HttpResponse(
        json.dumps({"status": status_code, "error": message}),
        status_code=status_code,
        mimetype="application/json",
        headers={"Access-Control-Allow-Origin": "*"}
    )


def _fatal(message: str) -> func.HttpResponse:
    """
    Réponse 500 – affiche le stack-trace complet si DEBUG_MODE == true.
    """
    body = {"status": 500, "error": message}
    if DEBUG_MODE:
        body["traceback"] = traceback.format_exc()
    return func.HttpResponse(
        json.dumps(body, ensure_ascii=False, indent=2),
        status_code=500,
        mimetype="application/json",
        headers={"Access-Control-Allow-Origin": "*"}
    )
